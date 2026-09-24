"""The analyze pipeline (one request, no state kept):

    1 read_text      text in (screenshots become text first, app/screenshot.py)
    2 check_urls     Web Risk lookups              } run in parallel with the Gemini judge call
    3 match_domains  punycode / look-alike / short } pure code, done first, fed to Gemini as trusted facts
    4 verdict        merge flags -> app/verdict.py -> reply filter

Tools run on EVERY link in code, not at the model's discretion, so an injected message cannot skip them.
Nothing here logs the message, the links or the reply; see _log_request().
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import unicodedata
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from app import offline_fixture
from app.config import Settings
from app.prompt import RESPONSE_SCHEMA, SCAM_TYPES, SYSTEM_PROMPT, user_prompt
from app.reply_filter import filter_reply
from app.tools import url_reputation as rep
from app.tools.domain_check import UrlInfo, check_text
from app.verdict import RED, decide

log = logging.getLogger("repsafe.analyze")
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="analyze")

# Code-side injection guard: a buyer who writes to "the checker" is a red flag whatever Gemini says.
INJECTION_RE = re.compile(
    r"(?i)ignore\s+(?:\w+\s+){0,3}(instructions|prompts?|rules)"  # BUG-003: "ignore your previous / all ..."
    r"|disregard .{0,30}(instructions|rules)|system prompt|you are now|as an ai"
    r"|(mark|classify|label|judge|rate) (this|it|me) as (safe|normal|legit|not (a )?scam)"
    r"|(note|message|instructions?) (for|to) (the )?(ai|assistant|checker|reviewer|bot|model)\b"
    r"|output no (red )?flags"
    r"|忽略.{0,8}(指示|指令|規則|提示)|(判定|判斷|標記|視)為.{0,3}(正常|安全|非詐騙)|系統提示"
    r"|(不要|別|不用)(理會|理|管).{0,6}(指示|指令|規則|提示)"
    r"|[【\[]\s*系統(訊息|通知|提示)\s*[】\]]|(回覆|判定|顯示|輸出)(為|成)?(無風險|沒有風險|零風險)"
)
# F7 / BUG-007: a quote must be long enough to point at a real sentence ("a" is in almost any message).
MIN_QUOTE_CHARS, MIN_QUOTE_CHARS_CJK = 4, 2
_CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯]")
_SENTENCE = re.compile(r"[^\n。！？!?]+[。！？!?]?")


# ---------------------------------------------------------------- global rate limit (cost ceiling)
class RateLimiter:
    def __init__(self, per_hour: int):
        self.per_hour, self._hits, self._lock = per_hour, deque(), threading.Lock()

    def allow(self, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            while self._hits and now - self._hits[0] > 3600:
                self._hits.popleft()
            if len(self._hits) >= self.per_hour:
                return False
            self._hits.append(now)
            return True


# ---------------------------------------------------------------- helpers
def _norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", s).split())


def injection_flags(text: str) -> list[dict]:
    out = []
    for m in _SENTENCE.finditer(text):
        sentence = m.group(0).strip()
        if sentence and INJECTION_RE.search(sentence):
            out.append(dict(quote=sentence, code="prompt_injection", tool="injection_guard",
                            reason="The message tries to give orders to the checking tool. Real buyers don't."))
    return out


def gemini_injection_flag(text: str) -> dict:
    """Gemini said injection_detected=true but the code guard found nothing (BUG-001). Typical injection effect:
    the model was talked out of listing flags but still set the boolean. Never amber on that: quote the first
    sentence of the message (it is in the message, so F7 holds) and say why."""
    first = next((m.group(0).strip() for m in _SENTENCE.finditer(text) if m.group(0).strip()), text.strip())
    return dict(quote=first[:200], code="prompt_injection", tool="gemini",
                reason="The checker found text in this message that tries to give it orders. Real buyers don't.")


def validate_judge(data: dict, text: str) -> tuple[dict, int]:
    """Shape check of the judge output + keep only quotes that really are in the message.
    Returns (clean output, dropped quote count). Raises ValueError when the output is unusable."""
    if not isinstance(data.get("scam_type"), str) or data["scam_type"] not in SCAM_TYPES:
        raise ValueError("scam_type")
    if not isinstance(data.get("red_flags"), list) or not isinstance(data.get("safe_reply"), str):
        raise ValueError("fields")
    if not isinstance(data.get("injection_detected"), bool):
        raise ValueError("injection_detected")
    haystack, kept, dropped = _norm(text), [], 0
    for f in data["red_flags"]:
        if not (isinstance(f, dict) and isinstance(f.get("quote"), str) and isinstance(f.get("reason"), str)):
            raise ValueError("red_flags item")
        q = _norm(f["quote"])
        min_len = MIN_QUOTE_CHARS_CJK if _CJK.search(q) else MIN_QUOTE_CHARS
        if len(q) >= min_len and q in haystack:
            kept.append(dict(quote=f["quote"].strip(), reason=f["reason"].strip(), code=data["scam_type"],
                             tool="gemini"))
        else:
            dropped += 1  # hallucinated or paraphrased quote: F7 says every flag must map to the message
    if data["scam_type"] != "none" and not kept:
        raise ValueError("scam_type without a verifiable red flag")
    return dict(scam_type=data["scam_type"], red_flags=kept, injection_detected=data["injection_detected"],
                safe_reply=data["safe_reply"]), dropped


def tool_lines(urls: list[UrlInfo]) -> list[str]:
    lines = []
    for i, u in enumerate(urls, 1):
        facts = "; ".join(f.reason for f in u.findings) or ("official marketplace domain" if u.official
                                                            else "no impersonation pattern found")
        lines.append(f"- link {i}: host={u.host} -> {facts}")
    return lines


def _gemini_judge(text: str, urls: list[UrlInfo], settings: Settings) -> dict:
    from google.genai import types

    from app.gemini import generate_json

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt(text, tool_lines(urls)))])]
    return generate_json(settings, contents, SYSTEM_PROMPT, RESPONSE_SCHEMA, purpose="judge")


# ---------------------------------------------------------------- pipeline
def analyze(text: str, settings: Settings, reputation: rep.UrlReputation, limiter: RateLimiter,
            judge_fn=None) -> dict:
    """judge_fn(text, urls) -> raw judge dict; defaults by AGENT_MODE. Tests inject failing ones."""
    t0 = time.monotonic()
    rid = uuid.uuid4().hex[:12]
    problems: list[str] = []
    flags: list[dict] = []
    steps = {"read_text": "done", "check_urls": "none", "match_domains": "none", "verdict": "pending"}
    judged, dropped = None, 0
    urls: list[UrlInfo] = []
    reps: list[rep.Reputation] = []
    try:
        # 3 match_domains first: pure code, instant, and Gemini gets it as trusted facts
        urls = check_text(text)
        if urls:
            steps["match_domains"] = "done"
        for u in urls:
            for f in u.findings:
                flags.append(dict(quote=u.raw, reason=f.reason, code=f.code, tool="domain_check"))
        flags.extend(injection_flags(text))

        if not limiter.allow():
            problems.append("rate_limited")
            steps["check_urls"] = "skipped" if urls else "none"
        else:
            if judge_fn is None:
                judge_fn = ((lambda t, u: offline_fixture.judge(t)) if settings.offline
                            else (lambda t, u: _gemini_judge(t, u, settings)))
            rep_future = None
            if urls:
                rep_future = _pool.submit(rep.check_many, reputation, [u.lookup_url for u in urls],
                                          settings.max_urls_checked, settings.webrisk_timeout_s)
            try:
                judged, dropped = validate_judge(judge_fn(text, urls), text)
            except ValueError:
                problems.append("gemini_bad_output")
            except Exception as e:  # noqa: BLE001 - JudgeError carries the code; anything else = error
                problems.append(getattr(e, "code", "gemini_error"))
            if rep_future is not None:
                reps = rep_future.result()
                statuses = {r.status for r in reps}
                if rep.ERROR in statuses:
                    problems.append("reputation_error")
                if rep.SKIPPED in statuses:
                    problems.append("reputation_skipped")
                steps["check_urls"] = "error" if statuses & {rep.ERROR, rep.SKIPPED} else "done"
                for u, r in zip(urls, reps):
                    if r.status == rep.MATCH:
                        flags.append(dict(quote=u.raw, code="listed_threat", tool="url_reputation",
                                          reason=f"Listed by Google Web Risk as {', '.join(r.threats)}."))
            if judged:
                flags.extend(judged["red_flags"])
                if judged["injection_detected"] and not any(f["code"] == "prompt_injection" for f in flags):
                    flags.append(gemini_injection_flag(text))
    except Exception as e:  # noqa: BLE001 - never 500 and never amber on a bug
        problems.append("internal_error")
        log.error(json.dumps({"event": "analyze_bug", "request_id": rid, "error": type(e).__name__}))

    # de-duplicate (same quote + same tool + same code)
    seen, merged = set(), []
    for f in flags:
        key = (f["quote"], f["tool"], f["code"])
        if key not in seen:
            seen.add(key)
            merged.append(f)

    verdict = decide(merged, problems)
    steps["verdict"] = "done"
    if judged:
        reply, reply_source = judged["safe_reply"], "gemini"
    else:
        reply, reply_source = offline_fixture.fallback_reply(text), "fallback"
    reply, removed = filter_reply(reply, text)
    if not reply:
        reply, removed2 = filter_reply(offline_fixture.fallback_reply(text), text)
        reply_source, removed = "fallback", removed + removed2

    scam_type = judged["scam_type"] if judged else None
    if scam_type in (None, "none") and verdict == RED:
        scam_type = merged[0]["code"]
    result = dict(
        request_id=rid,
        mode=settings.agent_mode,
        offline_fixture=settings.offline,
        verdict=verdict,
        problems=sorted(set(problems)),
        scam_type=scam_type,
        red_flags=merged,
        links=[dict(text=u.raw, host=u.host, host_ascii=u.host_ascii, official=u.official,
                    reputation=(reps[i].status if i < len(reps) else "not_checked"),
                    findings=[f.code for f in u.findings]) for i, u in enumerate(urls)],
        steps=[{"id": k, "status": v} for k, v in steps.items()],
        safe_reply=reply,
        safe_reply_source=reply_source,
        latency_ms=int((time.monotonic() - t0) * 1000),
    )
    _log_request(result, len(text), removed, dropped)
    return result


def _log_request(r: dict, n_chars: int, removed: int, dropped: int) -> None:
    """Metadata only. Adding a field here? It must not contain message text, links, hosts or the reply."""
    log.info(json.dumps({
        "event": "analyze", "request_id": r["request_id"], "mode": r["mode"], "verdict": r["verdict"],
        "problems": r["problems"], "scam_type": r["scam_type"], "n_chars": n_chars, "n_links": len(r["links"]),
        "flag_tools": sorted({f["tool"] for f in r["red_flags"]}), "n_flags": len(r["red_flags"]),
        "reply_source": r["safe_reply_source"], "reply_removed": removed, "quotes_dropped": dropped,
        "latency_ms": r["latency_ms"],
    }))

"""Safe-reply post-filter: the reply the seller copies must never carry a link or an account.

Runs on every reply (Gemini's and the fixed fallback), after the prompt already forbids them.
Removes: any link / bare domain / punycode host, emails, @handles, "ID: xxx" values, runs of 6+ digits
(bank accounts, phone numbers), and every link, host, number or handle that appeared in the buyer's message
(including chat-app handles written after "LINE" / "賴" / "Telegram" ... without an "ID:" prefix).
"""
from __future__ import annotations

import re

from app.tools.domain_check import _SCHEME_RE, extract_urls, check_url

REMOVED = "[removed]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_HANDLE = re.compile(r"(?<![\w@])@[A-Za-z0-9._-]{3,}")
_ID_VALUE = re.compile(r"(?i)\b((?:line\s*)?id|帳號|账号|帐号|account|acct)\s*[:：]\s*[^\s，。,]+")
# Chat-app handle without an "ID:" prefix (BUG-005): "加我賴 abc_123", "LINE：abc", "Telegram me at abc_1".
_CONTACT = re.compile(
    r"(?i)(?<![a-z])(line|whats\s?app|telegram|tg|wechat|weixin|kakao|signal|viber|zalo|skype|微信|賴|加我)(?![a-z])"
    r"((?:\s*(?:id|me|at|is|on|:|：|是|的|帳號|账号|號|号))*)\s*([a-z0-9][a-z0-9_.\-]{3,})"
)
_DIGITS = re.compile(r"(?<!\d)(?:\d[\s\-.]?){5,}\d(?!\d)")  # 6+ digits, spaces/dashes allowed between
_XN = re.compile(r"(?i)\bxn--[a-z0-9\-]+(?:\.[a-z0-9\-]+)*")
_SPACES = re.compile(r"[ \t]{2,}")


def _secrets_from(text: str) -> set[str]:
    """Links, hosts, emails, handles and long numbers the buyer wrote. Matched literally in the reply."""
    out: set[str] = set()
    for raw in extract_urls(text):
        info = check_url(raw)
        out.update({raw, info.host, info.host_ascii})
    for rx in (_EMAIL, _HANDLE, _DIGITS):
        out.update(m.group(0).strip() for m in rx.finditer(text))
    for m in _ID_VALUE.finditer(text):
        out.add(m.group(0).split(":", 1)[-1].split("：", 1)[-1].strip())
    for m in _CONTACT.finditer(text):
        app_name, filler, handle = m.group(1), m.group(2), m.group(3).rstrip(".-")
        # After an English "line" / "signal" a plain word ("later") is just English; keep only handle-looking
        # strings there. After a colon, "ID", or a CJK keyword, anything counts.
        if (not app_name.isascii() or re.search(r"(?i)id|[:：]", filler)
                or any(c.isdigit() or c in "_.-" for c in handle)):
            out.add(handle)
    return {s for s in out if len(s) >= 3}


def filter_reply(reply: str, original_text: str = "") -> tuple[str, int]:
    """Returns (clean reply, number of removals). Never raises."""
    count = 0

    def sub(rx: re.Pattern, s: str) -> str:
        nonlocal count
        s, n = rx.subn(REMOVED, s)
        count += n
        return s

    out = reply or ""
    for secret in sorted(_secrets_from(original_text), key=len, reverse=True):
        rx = re.compile(re.escape(secret), re.IGNORECASE)
        out = sub(rx, out)
    out = sub(_SCHEME_RE, out)
    out = sub(_EMAIL, out)
    for raw in extract_urls(out):
        if raw != REMOVED:
            out = sub(re.compile(re.escape(raw)), out)
    for rx in (_XN, _HANDLE, _ID_VALUE, _DIGITS):
        out = sub(rx, out)
    out = _SPACES.sub(" ", out).strip()
    return out, count

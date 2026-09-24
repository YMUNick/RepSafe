"""Vertex AI Gemini wrapper (google-genai SDK): one structured-output call, bounded time and retries.

Adapted from LineSleuth app/agent/gemini_agent.py (client setup, SDK retries off, timeout via a thread
future, retry only on 429 / 5xx / network). Differences: one call per request (no function-calling loop),
JSON schema output, and a 10 s budget, so a timeout is never retried.

Every failure raises JudgeError(code) with a problem code from app/verdict.py; the caller shows grey.
Log lines carry codes and token counts only, never message text or model output.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from app.config import Settings

log = logging.getLogger("repsafe.gemini")

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")
_client = None
RETRY_HTTP_CODES = (429, 500, 502, 503, 504)


class JudgeError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _get_client(settings: Settings):
    global _client
    if _client is None:
        from google import genai
        from google.genai import types

        if not settings.gcp_project:
            raise JudgeError("gemini_unavailable")
        _client = genai.Client(vertexai=True, project=settings.gcp_project, location=settings.gemini_location,
                               http_options=types.HttpOptions(timeout=int((settings.gemini_timeout_s + 2) * 1000),
                                                              retry_options=types.HttpRetryOptions(attempts=1)))
    return _client


def _classify(e: BaseException) -> tuple[str, bool]:
    """(problem code, retryable)."""
    if isinstance(e, (FutureTimeout, TimeoutError)):
        return "gemini_timeout", False
    try:
        from google.genai import errors

        if isinstance(e, errors.APIError) and e.code in RETRY_HTTP_CODES:
            return ("gemini_quota" if e.code == 429 else "gemini_error"), True
    except ImportError:  # pragma: no cover
        pass
    try:
        import httpx

        if isinstance(e, httpx.TimeoutException):
            return "gemini_timeout", False
        if isinstance(e, httpx.TransportError):
            return "gemini_error", True
    except ImportError:  # pragma: no cover
        pass
    return "gemini_error", False


def generate_json(settings: Settings, contents, system: str | None, schema: dict, purpose: str) -> dict:
    """One Gemini call returning parsed JSON that matches `schema` (shape checked by the caller)."""
    from google.genai import types

    client = _get_client(settings)
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=settings.gemini_temperature,
        response_mime_type="application/json",
        response_json_schema=schema,
    )
    deadline = time.monotonic() + settings.gemini_timeout_s
    attempt = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise JudgeError("gemini_timeout")
        future = _pool.submit(client.models.generate_content, model=settings.gemini_model,
                              contents=contents, config=config)
        try:
            resp = future.result(timeout=remaining)
            break
        except Exception as e:  # noqa: BLE001 - classified below
            code, retryable = _classify(e)
            if not retryable or attempt >= settings.gemini_max_retries:
                log.warning(json.dumps({"event": "gemini_failed", "purpose": purpose, "code": code,
                                        "error": type(e).__name__, "attempts": attempt + 1}))
                raise JudgeError(code) from None
            attempt += 1
            time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    m = getattr(resp, "usage_metadata", None)
    log.info(json.dumps({"event": "gemini_ok", "purpose": purpose, "model": settings.gemini_model,
                         "attempts": attempt + 1,
                         "input_tokens": getattr(m, "prompt_token_count", None),
                         "output_tokens": getattr(m, "candidates_token_count", None),
                         "thinking_tokens": getattr(m, "thoughts_token_count", None)}))
    try:
        data = json.loads(resp.text or "")
    except (ValueError, TypeError):
        raise JudgeError("gemini_bad_output") from None
    if not isinstance(data, dict):
        raise JudgeError("gemini_bad_output")
    return data

"""RepSafe FastAPI service: one Cloud Run service.

    uvicorn app.main:app --reload

Privacy rule: no handler logs request bodies, and FastAPI/uvicorn access logs only carry method + path.
"""
from __future__ import annotations

import logging
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.analyze import RateLimiter, analyze
from app.config import get_settings
from app.tools.url_reputation import make_reputation

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("repsafe.api")
INDEX_HTML = Path(__file__).parent / "static" / "index.html"

settings = get_settings()
reputation = make_reputation(settings)
limiter = RateLimiter(settings.global_rate_limit_per_hour)

def warm_up() -> dict:
    """BUG-008: build the Gemini and Web Risk clients (SDK imports, credentials) before the first request, so a
    cold start does not spend the Web Risk / Gemini time budget on setup. No model call, no lookup, no cost.
    Runs in a background daemon thread started by lifespan, so startup and GET / never wait for it. A failure
    is logged, never fatal: the request path builds the client again (under the same lock, so no race) and
    falls back to grey as before."""
    status = {}
    jobs = []
    if not settings.offline:
        from app.gemini import _get_client
        jobs.append(("gemini", lambda: _get_client(settings)))
    if hasattr(reputation, "_get_client"):
        jobs.append(("url_reputation", reputation._get_client))
    for name, job in jobs:
        t0 = time.monotonic()
        try:
            job()
            status[name] = "ready"
        except Exception as e:  # noqa: BLE001 - never block startup
            status[name] = f"error:{type(e).__name__}"
        log.info('{"event": "warm_up", "client": "%s", "status": "%s", "ms": %d}',
                 name, status[name], (time.monotonic() - t0) * 1000)
    return status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=_warm_up_safe, name="warm_up", daemon=True).start()
    yield


def _warm_up_safe() -> None:
    try:
        warm_up()
    except Exception as e:  # noqa: BLE001 - background thread, log only
        log.warning('{"event": "warm_up", "status": "error:%s"}', type(e).__name__)


app = FastAPI(title="RepSafe", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
if settings.offline:
    log.warning("AGENT_MODE=offline_fixture: keyword rules instead of Gemini. Never demo or evaluate with this.")


class AnalyzeIn(BaseModel):
    text: str


class ImageIn(BaseModel):
    image_base64: str
    mime_type: str


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Single-file front end (docs/design/ui-spec.md). No-cache so a redeploy shows up right away."""
    return FileResponse(INDEX_HTML, media_type="text/html",
                        headers={"Cache-Control": "no-cache", "Referrer-Policy": "no-referrer",
                                 "X-Content-Type-Options": "nosniff"})


@app.get("/health")
def health() -> dict:
    """Also the warm-up call before recording the demo (cold start is measured separately)."""
    return {"status": "ok", "mode": settings.agent_mode, "url_reputation": reputation.name}


@app.get("/api/config")
def config() -> dict:
    """What the front end needs to know: offline label, whether the upload button exists, limits."""
    return {"mode": settings.agent_mode, "offline_fixture": settings.offline,
            "screenshot_enabled": settings.screenshot_enabled, "max_input_chars": settings.max_input_chars,
            "max_image_mb": settings.max_image_mb}


@app.post("/api/analyze")
def analyze_text(body: AnalyzeIn) -> dict:
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Paste the buyer's message first.")
    if len(text) > settings.max_input_chars:
        raise HTTPException(400, f"Message is longer than {settings.max_input_chars} characters.")
    return analyze(text, settings, reputation, limiter)


if settings.screenshot_enabled:
    from app.screenshot import ScreenshotError, decode_image, extract_text

    @app.post("/api/extract-text")
    def extract(body: ImageIn) -> dict:
        """Screenshot -> text only. The seller checks the text, then calls /api/analyze."""
        from app.gemini import JudgeError

        try:
            data = decode_image(body.image_base64, body.mime_type, settings)
        except ScreenshotError as e:
            raise HTTPException(400, str(e)) from None
        if not limiter.allow():
            raise HTTPException(429, "Too many requests right now. Please paste the text instead.")
        try:
            return {"text": extract_text(data, body.mime_type, settings), "mode": settings.agent_mode}
        except JudgeError as e:
            raise HTTPException(503, f"Could not read the screenshot ({e.code}). Please paste the text.") from None

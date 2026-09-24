"""RepSafe FastAPI service: one Cloud Run service.

    uvicorn app.main:app --reload

Privacy rule: no handler logs request bodies, and FastAPI/uvicorn access logs only carry method + path.
"""
from __future__ import annotations

import logging
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.analyze import RateLimiter, analyze
from app.config import get_settings
from app.tools.url_reputation import make_reputation

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
log = logging.getLogger("repsafe.api")

settings = get_settings()
reputation = make_reputation(settings)
limiter = RateLimiter(settings.global_rate_limit_per_hour)

app = FastAPI(title="RepSafe", docs_url="/api/docs", openapi_url="/api/openapi.json")
if settings.offline:
    log.warning("AGENT_MODE=offline_fixture: keyword rules instead of Gemini. Never demo or evaluate with this.")


class AnalyzeIn(BaseModel):
    text: str


class ImageIn(BaseModel):
    image_base64: str
    mime_type: str


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

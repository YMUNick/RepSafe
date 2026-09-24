"""OPTIONAL screenshot -> text module. Off unless SCREENSHOT_ENABLED=true (docs/prd.md section 11: pending decision).

Only reads text. It never judges the image and never claims to detect forged payment screenshots.
The text goes back to the browser so the seller can check it (look-alike letters in links are easy to
misread) and then submits it to /api/analyze like pasted text. The image is not stored or logged.
Removing the feature = delete this file and its route in app/main.py; nothing else imports it.
"""
from __future__ import annotations

import base64
import binascii

from app.config import Settings
from app.prompt import OCR_PROMPT, OCR_SCHEMA

ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"}

OFFLINE_TEXT = ("Hi, I want to buy this. Your shop has not signed the payment guarantee, "
                "please verify here first: https://shopee-tw.verify-pay.example/login")


class ScreenshotError(ValueError):
    """Message is safe to show to the user (no content echoed)."""


def decode_image(image_base64: str, mime_type: str, settings: Settings) -> bytes:
    if mime_type not in ALLOWED_MIME:
        raise ScreenshotError(f"Unsupported image type. Use one of: {', '.join(sorted(ALLOWED_MIME))}.")
    if len(image_base64) > settings.max_image_mb * 1024 * 1024 * 4 / 3 + 16:
        raise ScreenshotError(f"Image is larger than {settings.max_image_mb:g} MB.")
    try:
        data = base64.b64decode(image_base64.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise ScreenshotError("Image data is not valid base64.") from None
    if not data:
        raise ScreenshotError("Empty image.")
    if len(data) > settings.max_image_mb * 1024 * 1024:
        raise ScreenshotError(f"Image is larger than {settings.max_image_mb:g} MB.")
    return data


def extract_text(data: bytes, mime_type: str, settings: Settings) -> str:
    """Raises app.gemini.JudgeError on Gemini failure."""
    if settings.offline:
        return OFFLINE_TEXT
    from google.genai import types

    from app.gemini import JudgeError, generate_json

    contents = [types.Content(role="user", parts=[types.Part.from_bytes(data=data, mime_type=mime_type),
                                                  types.Part.from_text(text=OCR_PROMPT)])]
    out = generate_json(settings, contents, None, OCR_SCHEMA, purpose="ocr")
    if not isinstance(out.get("text"), str):
        raise JudgeError("gemini_bad_output")
    return out["text"][: settings.max_input_chars]

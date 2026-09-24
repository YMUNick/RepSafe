"""Runtime settings, all from environment variables (see .env.example).

Same pattern as LineSleuth's app/config.py, trimmed to what RepSafe needs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # .env is optional; Cloud Run uses real env vars
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

AGENT_MODES = ("gemini", "offline_fixture")
URL_REPUTATION_BACKENDS = ("webrisk", "fixture")


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _bool(name: str, default: str) -> bool:
    return _env(name, default).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    agent_mode: str               # "gemini" (Vertex AI) or "offline_fixture" (no GCP, labelled in every response)
    url_reputation_backend: str   # "webrisk" (Google Cloud Web Risk API) or "fixture" (no GCP)
    gcp_project: str
    gemini_model: str
    gemini_location: str
    gemini_temperature: float
    gemini_timeout_s: float       # one Gemini call; past this the card goes grey
    gemini_max_retries: int       # retries on 429 / 5xx only (never on timeout: the 10 s budget is gone)
    webrisk_timeout_s: float      # one Web Risk lookup; past this that URL counts as "error"
    max_urls_checked: int         # URLs looked up per request; the rest are "skipped" (no amber possible)
    max_input_chars: int
    screenshot_enabled: bool      # screenshot -> text module (app/screenshot.py); on by default (boss 9/24); off = 404
    max_image_mb: float
    global_rate_limit_per_hour: int  # all clients together = the Gemini cost ceiling; over it -> grey card

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            agent_mode=_env("AGENT_MODE", "gemini"),
            url_reputation_backend=_env("URL_REPUTATION_BACKEND", "webrisk"),
            gcp_project=_env("GOOGLE_CLOUD_PROJECT", ""),
            gemini_model=_env("GEMINI_MODEL", "gemini-3-flash-preview"),
            gemini_location=_env("GOOGLE_CLOUD_LOCATION", "global"),
            gemini_temperature=float(_env("GEMINI_TEMPERATURE", "0")),
            gemini_timeout_s=float(_env("GEMINI_TIMEOUT_S", "9")),
            gemini_max_retries=int(_env("GEMINI_MAX_RETRIES", "1")),
            webrisk_timeout_s=float(_env("WEBRISK_TIMEOUT_S", "3")),
            max_urls_checked=int(_env("MAX_URLS_CHECKED", "5")),
            max_input_chars=int(_env("MAX_INPUT_CHARS", "5000")),
            screenshot_enabled=_bool("SCREENSHOT_ENABLED", "true"),
            max_image_mb=float(_env("MAX_IMAGE_MB", "10")),
            global_rate_limit_per_hour=int(_env("GLOBAL_RATE_LIMIT_PER_HOUR", "120")),
        )

    def validate(self) -> None:
        if self.agent_mode not in AGENT_MODES:
            raise ValueError(f"AGENT_MODE must be one of {AGENT_MODES}")
        if self.url_reputation_backend not in URL_REPUTATION_BACKENDS:
            raise ValueError(f"URL_REPUTATION_BACKEND must be one of {URL_REPUTATION_BACKENDS}")
        if not 0 <= self.gemini_max_retries <= 2:
            raise ValueError("GEMINI_MAX_RETRIES must be 0-2 (10 s latency budget)")
        if self.max_urls_checked < 1:
            raise ValueError("MAX_URLS_CHECKED must be >= 1")

    @property
    def offline(self) -> bool:
        return self.agent_mode == "offline_fixture"


def get_settings() -> Settings:
    s = Settings.from_env()
    s.validate()
    return s

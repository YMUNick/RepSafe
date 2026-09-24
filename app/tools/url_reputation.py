"""Tool 1: URL reputation lookup behind a swappable interface.

    status = "match"     the service lists the URL as a threat -> red flag
             "no_match"  not listed. NOT the same as safe (new phishing domains are not listed yet)
             "error"     failure / timeout / quota -> the card can never be amber (grey unless another red flag)
             "skipped"   over MAX_URLS_CHECKED -> treated like "error"

Swapping the API = add a class with .check(lookup_url) and one line in make_reputation().
The lookup sends the URL *string* to the API. Nothing here requests the URL itself.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Protocol

from app.config import Settings

log = logging.getLogger("repsafe.reputation")

MATCH, NO_MATCH, ERROR, SKIPPED = "match", "no_match", "error", "skipped"
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="reputation")


@dataclass
class Reputation:
    status: str
    threats: tuple[str, ...] = ()
    error: str | None = None   # exception class name only (never the URL, never the message text)


class UrlReputation(Protocol):
    name: str

    def check(self, lookup_url: str) -> Reputation: ...


class WebRiskReputation:
    """Google Cloud Web Risk API, uris.search (Lookup API). Auth = ADC / Cloud Run service account."""

    name = "web_risk"

    def __init__(self, timeout_s: float):
        self.timeout_s = timeout_s
        self._client = None
        self._lock = threading.Lock()  # background warm_up and request threads may build it at once

    def _get_client(self):
        if self._client is not None:
            return self._client
        with self._lock:
            if self._client is not None:
                return self._client
            from google.cloud import webrisk_v1

            self._types = [webrisk_v1.ThreatType.MALWARE, webrisk_v1.ThreatType.SOCIAL_ENGINEERING,
                           webrisk_v1.ThreatType.UNWANTED_SOFTWARE]
            self._client = webrisk_v1.WebRiskServiceClient()  # set last: _types must exist once _client does
        return self._client

    def check(self, lookup_url: str) -> Reputation:
        client = self._get_client()
        resp = client.search_uris(uri=lookup_url, threat_types=self._types, timeout=self.timeout_s)
        threat = getattr(resp, "threat", None)
        types = tuple(t.name for t in (threat.threat_types if threat else []))
        return Reputation(MATCH, types) if types else Reputation(NO_MATCH)


class FixtureReputation:
    """Offline stand-in (no GCP). Deterministic: hosts containing a marker below are 'listed'.
    Only for UI work and tests; every response is labelled offline_fixture."""

    name = "fixture"
    LISTED_MARKERS = ("phish", "malware", "testsafebrowsing.appspot.com")

    def check(self, lookup_url: str) -> Reputation:
        u = lookup_url.lower()
        if any(m in u for m in self.LISTED_MARKERS):
            return Reputation(MATCH, ("SOCIAL_ENGINEERING",))
        return Reputation(NO_MATCH)


def make_reputation(settings: Settings) -> UrlReputation:
    if settings.url_reputation_backend == "webrisk":
        return WebRiskReputation(settings.webrisk_timeout_s)
    return FixtureReputation()


def check_many(checker: UrlReputation, lookup_urls: list[str], max_urls: int, timeout_s: float) -> list[Reputation]:
    """Parallel lookups with one overall deadline. Any failure becomes status=error, never an exception."""
    results: list[Reputation] = [Reputation(SKIPPED) for _ in lookup_urls]
    futures = {i: _pool.submit(checker.check, u) for i, u in enumerate(lookup_urls[:max_urls])}
    if not futures:
        return results
    wait(futures.values(), timeout=timeout_s + 0.5)
    for i, f in futures.items():
        if not f.done():
            results[i] = Reputation(ERROR, error="Timeout")
            continue
        try:
            results[i] = f.result()
        except Exception as e:  # noqa: BLE001 - quota, auth, network: all mean "don't know"
            results[i] = Reputation(ERROR, error=type(e).__name__)
    errors = sorted({r.error for r in results if r.status == ERROR})
    if errors:
        log.warning('{"event": "reputation_error", "backend": "%s", "errors": "%s"}', checker.name, ",".join(errors))
    return results


FUNCTION_DECLARATION = {
    "name": "check_url_reputation",
    "description": "Look up a link in Google Cloud Web Risk. Sends the URL string only; never opens the link.",
    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
}

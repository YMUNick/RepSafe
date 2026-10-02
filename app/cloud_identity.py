"""Keyless Vercel → GCP identity. No service-account keys or user credentials.

Vercel injects the OIDC header at its gateway. Google STS validates its signature,
issuer, audience and the narrowly bound workload subject before issuing access.
The latest request token is shared only within this backend process: Google gRPC
may refresh credentials from its own thread, where request ContextVars are absent.
Never use this token as an end-user session or log/return it.
"""
from __future__ import annotations

import os
import re
import threading
from collections.abc import Mapping

from google.auth import identity_pool
from google.auth.exceptions import RefreshError

_lock = threading.Lock()
_request_token = ""
_AUDIENCE = re.compile(
    r"//iam\.googleapis\.com/projects/[0-9]+/locations/global/"
    r"workloadIdentityPools/[a-z0-9-]+/providers/[a-z0-9-]+"
)
_ACCOUNT = re.compile(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com")


def capture_vercel_oidc_token(headers: Mapping[str, str]) -> None:
    """Capture a gateway candidate; Google remains the verifier, not this app."""
    if os.environ.get("VERCEL") != "1":
        return
    token = headers.get("x-vercel-oidc-token", "")
    if token and len(token) <= 32768 and token.count(".") == 2:
        global _request_token
        with _lock:
            _request_token = token


class _VercelSupplier(identity_pool.SubjectTokenSupplier):
    def get_subject_token(self, context, request) -> str:
        with _lock:
            token = _request_token
        if not token:
            raise RefreshError("Vercel OIDC request token unavailable")
        return token


class VercelOIDCMiddleware:
    """Capture the platform token before downstream synchronous thread dispatch."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            from starlette.datastructures import Headers
            capture_vercel_oidc_token(Headers(scope=scope))
        await self.app(scope, receive, send)


def cloud_credentials():
    """Return federated credentials on Vercel; None lets local/Cloud Run use ADC.

    Credentials construction performs no network requests. Missing or malformed
    Vercel configuration is an error, never a fallback to another identity.
    """
    if os.environ.get("VERCEL") != "1":
        return None
    audience = os.environ.get("GCP_WORKLOAD_IDENTITY_AUDIENCE", "")
    account = os.environ.get("GCP_SERVICE_ACCOUNT_EMAIL", "")
    if not _AUDIENCE.fullmatch(audience) or not _ACCOUNT.fullmatch(account):
        raise ValueError("Vercel keyless GCP configuration is missing or invalid")
    return identity_pool.Credentials(
        audience=audience,
        subject_token_type="urn:ietf:params:oauth:token-type:jwt",
        token_url="https://sts.googleapis.com/v1/token",
        service_account_impersonation_url=(
            "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
            f"{account}:generateAccessToken"
        ),
        subject_token_supplier=_VercelSupplier(),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )

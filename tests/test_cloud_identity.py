"""Keyless cloud auth: wrong/missing setup must never fall back to user ADC on Vercel."""
import importlib

import pytest
from google.auth.exceptions import RefreshError


@pytest.fixture
def identity(monkeypatch):
    for name in ("VERCEL", "VERCEL_OIDC_TOKEN", "GCP_WORKLOAD_IDENTITY_AUDIENCE",
                 "GCP_SERVICE_ACCOUNT_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    return importlib.reload(importlib.import_module("app.cloud_identity"))


def configure(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("GCP_WORKLOAD_IDENTITY_AUDIENCE",
                       "//iam.googleapis.com/projects/123/locations/global/workloadIdentityPools/demo/providers/vercel")
    monkeypatch.setenv("GCP_SERVICE_ACCOUNT_EMAIL", "demo@repsafe-2026.iam.gserviceaccount.com")


def test_non_vercel_preserves_adc(identity):
    assert identity.cloud_credentials() is None


def test_vercel_missing_config_fails_closed(identity, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(ValueError, match="keyless"):
        identity.cloud_credentials()


def test_supplier_uses_rotating_request_token(identity, monkeypatch):
    configure(monkeypatch)
    credentials = identity.cloud_credentials()
    with pytest.raises(RefreshError, match="OIDC"):
        credentials.retrieve_subject_token(None)
    identity.capture_vercel_oidc_token({"x-vercel-oidc-token": "signed.first.token"})
    assert credentials.retrieve_subject_token(None) == "signed.first.token"
    identity.capture_vercel_oidc_token({"x-vercel-oidc-token": "signed.next.token"})
    assert credentials.retrieve_subject_token(None) == "signed.next.token"
    # A request lacking a gateway token must not erase the latest valid candidate.
    identity.capture_vercel_oidc_token({})
    assert credentials.retrieve_subject_token(None) == "signed.next.token"


def test_header_ignored_outside_vercel(identity, monkeypatch):
    identity.capture_vercel_oidc_token({"x-vercel-oidc-token": "not.from.gateway"})
    configure(monkeypatch)
    with pytest.raises(RefreshError):
        identity.cloud_credentials().retrieve_subject_token(None)


def test_middleware_supplies_gateway_token_to_sync_route(identity, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    configure(monkeypatch)
    app = FastAPI()
    app.add_middleware(identity.VercelOIDCMiddleware)
    credentials = identity.cloud_credentials()
    @app.get('/probe')
    def probe():
        # Assertion stays inside this test-only endpoint. Never expose tokens.
        assert credentials.retrieve_subject_token(None) == 'gateway.signed.token'
        return {'ok': True}
    with TestClient(app) as client:
        assert client.get('/probe', headers={'x-vercel-oidc-token': 'gateway.signed.token'}).json() == {'ok': True}


@pytest.mark.parametrize("audience", ["https://evil.example/token", "//iam.googleapis.com/projects/123/../../evil"])
def test_audience_cannot_inject_an_external_exchange_endpoint(identity, monkeypatch, audience):
    configure(monkeypatch)
    monkeypatch.setenv("GCP_WORKLOAD_IDENTITY_AUDIENCE", audience)
    with pytest.raises(ValueError):
        identity.cloud_credentials()


def test_service_account_must_be_a_google_account(identity, monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("GCP_SERVICE_ACCOUNT_EMAIL", "https://evil.example/account")
    with pytest.raises(ValueError):
        identity.cloud_credentials()


def test_exchange_only_targets_google_and_readwrite_cloud_scope(identity, monkeypatch):
    configure(monkeypatch)
    credentials = identity.cloud_credentials()
    info = credentials.info
    assert info["token_url"] == "https://sts.googleapis.com/v1/token"
    assert info["service_account_impersonation_url"] == (
        "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
        "demo@repsafe-2026.iam.gserviceaccount.com:generateAccessToken"
    )
    assert credentials.scopes == ["https://www.googleapis.com/auth/cloud-platform"]

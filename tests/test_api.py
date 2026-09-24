"""API in OFFLINE FIXTURE mode (no GCP). Checks plumbing, labelling and the no-content-in-logs rule."""
import base64
import dataclasses
import logging

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.screenshot import ScreenshotError, decode_image

SCAM = "您好，您的賣場未簽署金流保障，請點 https://shopee-tw.com/verify 驗證，客服 LINE ID: scam888"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "mode": "offline_fixture", "url_reputation": "fixture"}


def test_config_labels_offline_and_screenshot_off(client):
    cfg = client.get("/api/config").json()
    assert cfg["offline_fixture"] is True and cfg["screenshot_enabled"] is False


def test_scam_is_red_with_steps(client):
    r = client.post("/api/analyze", json={"text": SCAM}).json()
    assert r["verdict"] == "red" and r["offline_fixture"] is True
    assert [s["id"] for s in r["steps"]] == ["read_text", "check_urls", "match_domains", "verdict"]
    assert "shopee-tw" not in r["safe_reply"] and "scam888" not in r["safe_reply"]


def test_normal_is_amber(client):
    r = client.post("/api/analyze", json={"text": "Hi, is this still available? Can I collect on Saturday?"}).json()
    assert r["verdict"] == "amber"


def test_empty_and_too_long_rejected(client):
    assert client.post("/api/analyze", json={"text": "   "}).status_code == 400
    assert client.post("/api/analyze", json={"text": "a" * 5001}).status_code == 400


def test_screenshot_route_absent_when_disabled(client):
    assert client.post("/api/extract-text", json={"image_base64": "", "mime_type": "image/png"}).status_code == 404


def test_logs_never_contain_message(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.post("/api/analyze", json={"text": SCAM})
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert '"event": "analyze"' in logged
    for secret in ("shopee-tw", "scam888", "金流", "verify"):
        assert secret not in logged


# ---------------------------------------------------------------- screenshot module (unit level)
S = dataclasses.replace(get_settings(), max_image_mb=0.001)  # ~1 KB limit for the test


def test_image_type_and_size_checked():
    ok = base64.b64encode(b"x" * 500).decode()
    assert decode_image(ok, "image/heic", S) == b"x" * 500
    with pytest.raises(ScreenshotError):
        decode_image(ok, "image/gif", S)
    with pytest.raises(ScreenshotError):
        decode_image(base64.b64encode(b"x" * 5000).decode(), "image/png", S)
    with pytest.raises(ScreenshotError):
        decode_image("not base64!!", "image/png", S)

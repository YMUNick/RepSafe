"""Browser QA on an existing offline server; never downloads a browser or calls Gemini."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.finshield_smoke import write_evidence


def validate_origin(value, allow_live=False):
    parsed = urlsplit(value)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or
            parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("invalid_origin")
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if not local and (not allow_live or parsed.scheme != "https"):
        raise ValueError("remote_origin_requires_allow_live_https")
    return value.rstrip("/")


def run_browser(origin, channel=None):
    from playwright.sync_api import sync_playwright, expect
    checks = {}
    case_ids = []
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, **({"channel": channel} if channel else {}))
        try:
            contexts = [browser.new_context(reduced_motion="reduce") for _ in range(2)]
            pages = [context.new_page() for context in contexts]
            # Never follow URLs contained in evidence or load third-party assets.
            def same_origin(route):
                parsed = urlsplit(route.request.url)
                if f"{parsed.scheme}://{parsed.netloc}" == origin:
                    route.continue_()
                else:
                    route.abort()
            for context in contexts:
                context.route("**/*", same_origin)
            for page in pages:
                page.set_default_timeout(15000)
                page.on("pageerror", lambda _: errors.append("browser_script_error"))
                page.goto(origin + "/finshield", wait_until="networkidle")
                with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/finshield/cases")) as response:
                    page.locator("#open-case").click()
                case = response.value.json()
                if case.get("mode") != "offline_fixture":
                    raise ValueError("offline_model_mode_required_for_ui_probe")
                case_ids.append(case["case_id"])
                expect(page.locator("#check-payment")).to_be_enabled()
                expect(page.locator("#mode-note")).to_contain_text("Offline")
            checks["different_session_cases"] = case_ids[0] != case_ids[1]
            cross = contexts[1].request.get(origin + "/api/finshield/cases/" + case_ids[0])
            checks["cross_session_denied"] = cross.status == 404 and case_ids[0] not in cross.text()
            page = pages[0]
            page.locator("#check-payment").click()
            expect(page.locator("#payment-code")).to_have_text("HOLD_PENDING_REVIEW")
            expect(page.locator("#investigation-code")).to_have_text("READY", timeout=50000)
            checks["separate_payment_investigation_states"] = True
            expect(page.locator("#history-total")).to_have_text("SGD 2,700.00")
            expect(page.locator("#current-amount")).to_have_text("SGD 500.00")
            checks["history_excludes_current"] = True
            page.locator(".citation:not([disabled])").first.click()
            expect(page.locator("#source-inspector blockquote")).to_be_visible()
            checks["citation_source_navigation"] = bool(page.locator("#source-inspector blockquote").inner_text())
            page.locator("#ask-vip").click()
            expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
            expect(page.locator("#payment-code")).to_have_text("HOLD_PENDING_REVIEW")
            checks["vip_keeps_hold"] = True
            expect(page.locator("#review-form")).to_be_hidden()
            checks["visitor_has_no_review_form"] = True

            # Inject only into an intercepted browser response. The database is untouched.
            payload = '<img src=x onerror="window.qaInjected=true">'
            def hostile_response(route):
                response = route.fetch()
                data = response.json()
                data["bundle"]["sources"][0]["fields"]["conversation"] = payload
                route.fulfill(response=response, json=data)
            page.route("**/api/finshield/cases/" + case_ids[0], hostile_response)
            page.locator("#refresh-case").click()
            expect(page.locator("#conversation")).to_have_text(payload)
            checks["source_text_not_html"] = (page.locator("#conversation img").count() == 0 and
                                               page.evaluate("window.qaInjected !== true"))
            page.unroute("**/api/finshield/cases/" + case_ids[0], hostile_response)

            page.locator("#template-normal").click()
            page.locator("#open-case").click()
            expect(page.locator("#check-payment")).to_be_enabled()
            page.locator("#check-payment").click()
            expect(page.locator("#payment-code")).to_have_text("SIMULATED_PASSED")
            expect(page.locator("#investigation-code")).to_have_text("READY", timeout=50000)
            expect(page.locator("#counter-evidence")).to_contain_text("Invoice")
            checks["normal_case_and_invoice_counter_evidence"] = True

            health = contexts[0].request.get(origin + "/health").json()
            checks["health_exact_fields"] = set(health) == {"status", "mode", "url_reputation"}
            if health.get("mode") != "offline_fixture":
                raise ValueError("offline_chat_mode_required_for_ui_probe")
            page.goto(origin + "/", wait_until="networkidle")
            page.locator("#msg").fill("Is the used desk available for collection on Saturday?")
            page.locator("#check").click()
            expect(page.locator("#results")).to_contain_text("Safe reply", timeout=20000)
            checks["legacy_text_safe_reply"] = True
            # OCR is intentionally a browser fixture, not proof of OCR model quality.
            if page.locator("#tab-shot").is_visible():
                page.route("**/api/extract-text", lambda r: r.fulfill(json={"text": "Synthetic screenshot text for manual confirmation."}))
                page.locator("#tab-shot").click()
                png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=")
                page.locator("#shot").set_input_files({"name": "qa-synthetic.png", "mimeType": "image/png", "buffer": png})
                expect(page.locator("#shot-preview")).to_be_visible()
                expect(page.locator("#msg-notice")).to_be_visible()
                expect(page.locator("#msg")).to_have_value("Synthetic screenshot text for manual confirmation.")
                checks["legacy_screenshot_preview_confirmation_fixture"] = True
            else:
                checks["legacy_screenshot_preview_confirmation_fixture"] = None
            page.route("**/api/analyze", lambda r: r.fulfill(status=503, json={"detail": "QA service unavailable"}))
            page.locator("#msg").fill("A separate synthetic message for the failure path.")
            page.locator("#check").click()
            expect(page.locator("#results .card")).to_be_visible()
            checks["legacy_failure_card"] = True
        finally:
            browser.close()
    complete = bool(checks) and all(v is True for v in checks.values()) and not errors
    return {"stage": "UI", "status": "pass" if complete else "incomplete", "mode": "offline_fixture",
            "checks": checks, "case_ids": case_ids, "errors": errors, "g1_pass": False,
            "screenshot_ocr_mode": "browser_fixture", "model_calls": 0,
            "cost_usd": None, "cost_status": "unverified"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-live", action="store_true", help="Allow HTTPS remote UI; model mode must still be offline.")
    parser.add_argument("--channel", help="Use an already installed channel, e.g. msedge; never installs browsers.")
    args = parser.parse_args(argv)
    try:
        origin = validate_origin(args.base_url, args.allow_live)
        result = run_browser(origin, args.channel)
    except ImportError:
        result = {"stage": "UI", "status": "blocked", "error": "playwright_dependency_missing", "g1_pass": False}
    except Exception as exc:
        result = {"stage": "UI", "status": "blocked" if type(exc) is ValueError else "fail",
                  "error": str(exc) if type(exc) is ValueError else type(exc).__name__, "g1_pass": False}
    write_evidence(args.out, result)
    print(json.dumps(result))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

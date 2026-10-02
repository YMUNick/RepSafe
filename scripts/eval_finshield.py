"""Independent synthetic financial cases; offline policy accuracy is not AI quality."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.finshield_smoke import provenance_errors, write_evidence

DISPLAY_IDS = {"risk-fee", "normal-invoice"}
PROMPT_EXAMPLES = {
    "Pay a verification fee before receiving your sale proceeds.",
    "Please pay invoice INV-N-1 for the service already delivered.",
}
CATEGORIES = {"high_risk", "normal", "counter_evidence", "missing_kyc",
              "missing_history", "shared_device", "injection", "tool_failure"}


def validate_suite(cases: list[dict]) -> None:
    if not isinstance(cases, list) or any(not isinstance(c, dict) for c in cases):
        raise ValueError("invalid_suite")
    if any(c.get("template_id") in DISPLAY_IDS for c in cases):
        raise ValueError("display_template")
    ids = [c.get("template_id") for c in cases]
    case_ids = [(c.get("bundle") or {}).get("case_id") for c in cases]
    if len(cases) < 8 or len(set(ids)) != len(cases) or len(set(case_ids)) != len(cases) or not all(ids + case_ids):
        raise ValueError("independent_case_count")
    conversations = [" ".join(c.get("conversation", "").split()).casefold() for c in cases]
    examples = {text.casefold() for text in PROMPT_EXAMPLES}
    if any(text in examples for text in conversations):
        raise ValueError("prompt_example")
    if not all(conversations) or len(set(conversations)) != len(cases):
        raise ValueError("independent_case_text")
    if not CATEGORIES <= {c.get("category") for c in cases}:
        raise ValueError("scenario_coverage")
    required = {"bundle", "expected_payment_status", "expected_metrics", "required_fact_keys",
                "required_facts", "forbidden_claims", "required_counter_evidence"}
    for case in cases:
        if not required <= case.keys():
            raise ValueError("case_schema_incomplete")
        if case["expected_payment_status"] not in {"HOLD_PENDING_REVIEW", "SIMULATED_PASSED", "CHECK_FAILED"}:
            raise ValueError("invalid_expected_state")
        if set(case["required_fact_keys"]) != set(case["required_facts"]):
            raise ValueError("fact_oracle_incomplete")
        if case["bundle"].get("template_id") in DISPLAY_IDS:
            raise ValueError("display_template")


def compare_report(case, public_case):
    """Mechanical fact/provenance checks are separate from human semantic review."""
    errors = provenance_errors(public_case)
    report = (public_case.get("result") or {}).get("report") or {}
    claims = [c for section in ("findings", "counter_evidence", "policy_basis") for c in report.get(section, [])]
    facts = {c["fact_key"]: c["fact_value"] for c in claims}
    for key, expected in case["required_facts"].items():
        if key not in facts or type(facts[key]) is not type(expected) or facts[key] != expected:
            errors.append("required_fact_mismatch:" + key)
    text = " ".join(c["text"] for c in claims).casefold()
    for forbidden in case["forbidden_claims"]:
        if forbidden.casefold() in text:
            errors.append("forbidden_claim")
    counter = " ".join(c["text"] for c in report.get("counter_evidence", [])).casefold()
    for required in case["required_counter_evidence"]:
        if required.casefold() not in counter:
            errors.append("counter_evidence_manual_check_required")
    return {"mechanical_errors": sorted(set(errors)), "human_semantic_verdict": "not_run"}


def exercise_case(case, bundle):
    """Exercise the real service/investigator with only storage/model fixtures."""
    from app.finshield.models import CaseRecord, Session, Scope, ServiceError, ReviewerGrant, ReviewCommand
    from app.finshield.service import CaseService
    from app.finshield.store import session_key
    from app.finshield.investigator import run_investigation, make_offline_step
    from tests.finshield_fakes import MemoryStore
    store = MemoryStore()
    now = datetime(2026, 10, 2, 4, tzinfo=timezone.utc)
    clock = [now]
    service = CaseService(store, clock=lambda: clock[0])
    sid = "eval-" + bundle.case_id
    scope = Scope(sid, bundle.case_id, "reviewer-a", True)
    grant = ReviewerGrant(actor_id=scope.actor_id, case_id=bundle.case_id, expires_at=now + timedelta(minutes=15))
    session = Session(session_id=sid, token_hash="eval-not-a-token", csrf_hash="eval-not-a-csrf",
                      expires_at=now + timedelta(hours=24), case_ids=(bundle.case_id,), review_grants={bundle.case_id: grant})
    sk, ck = session_key(sid), "case-" + bundle.case_id
    initial = CaseRecord(case_id=bundle.case_id, session_id=sid, bundle=bundle)
    store.atomic((sk, ck), lambda _: {sk: session.model_dump(mode="json"), ck: initial.model_dump(mode="json")})
    checked = service.check(scope, "eval-payment-001")
    replay = service.check(scope, "eval-payment-001")
    new_key = service.check(scope, "eval-payment-002")
    idempotency = replay == checked and new_key.events == checked.events and new_key.version == checked.version
    authorization = False
    try:
        forged = Scope(sid, bundle.case_id, "forged-reviewer", True)
        service.review(forged, ReviewCommand(action="dismiss", reason="Forged reviewer must fail.",
                       expected_version=checked.version), "eval-forged-001")
    except ServiceError as exc:
        authorization = exc.status_code == 403
    cross_case = False
    try:
        service.get(Scope(sid, "outside-this-session", scope.actor_id, True))
    except ServiceError as exc:
        cross_case = exc.status_code == 404
    run = None
    if checked.payment_status != "CHECK_FAILED":
        lease = service.claim_run(scope, "eval-investigate-001")
        context = patch("app.finshield.investigator.dispatch", side_effect=TimeoutError()) if case.get("fault") == "tool_timeout" else nullcontext()
        with context:
            run = run_investigation(scope, bundle, make_offline_step(bundle), lambda: None)
        finished = service.finish_run(scope, lease.run_id, run)
        if finished.payment_status != checked.payment_status:
            raise ValueError("investigation_changed_payment")
    current = service.get(scope)
    public = current.model_dump(mode="json", exclude={"session_id", "operations"})
    report_checks = compare_report(case, public) if run and run.report else {
        "mechanical_errors": [], "human_semantic_verdict": "not_run"}
    # An unavailable tool is expected to leave an incomplete report, not fabricate facts.
    mechanical_errors = report_checks["mechanical_errors"] if run and run.status == "READY" else provenance_errors(public)
    status = run.status if run else "not_run"
    return {"investigation_status": status,
            "investigation_match": status == case["expected_investigation_status"],
            "provenance_status": "pass" if not mechanical_errors and run and run.report else "not_run" if not run or not run.report else "fail",
            "mechanical_errors": mechanical_errors,
            "authorization_status": "pass" if authorization and cross_case else "fail",
            "idempotency_status": "pass" if idempotency else "fail",
            "trace": [s.model_dump(mode="json") for s in run.trace] if run else [],
            "audit": [e.model_dump(mode="json") for e in current.events],
            "report": run.report.model_dump(mode="json") if run and run.report else None,
            "reason_codes": list(run.reason_codes) if run else [],
            "scripted_steps": len(run.trace) if run else 0,
            "restart_status": "not_run"}


def evaluate_suite(cases, revision):
    validate_suite(cases)
    if not revision or not revision.strip():
        raise ValueError("revision_required")
    from app.finshield.models import Bundle
    from app.finshield.policy import check_payment
    rows = []
    started = time.monotonic()
    for case in cases:
        t0 = time.monotonic()
        bundle = Bundle.model_validate(case["bundle"])
        result = check_payment(bundle)
        metrics = None if result.metrics is None else {
            "count": result.metrics.count, "total_minor": result.metrics.total_minor}
        actual_facts = {} if metrics is None else {
            "history_count": metrics["count"], "history_total_minor": metrics["total_minor"]}
        exercised = exercise_case(case, bundle)
        rows.append({"case_id": bundle.case_id, "category": case["category"],
            "expected": {"payment_status": case["expected_payment_status"], "metrics": case["expected_metrics"]},
            "actual": result.model_dump(mode="json"),
            "payment_match": result.payment_status == case["expected_payment_status"],
            "facts_match": metrics == case["expected_metrics"] and all(
                actual_facts.get(k) == v for k, v in case["required_facts"].items()),
            "fault_scenario": case.get("fault"), "human_semantic_verdict": "not_run",
            "counter_evidence_status": "human_review_required", **exercised,
            "elapsed_ms": int((time.monotonic() - t0) * 1000), "model_calls": 0,
            "token_usage": None, "cost_usd": None, "cost_status": "unverified"})
    return {"stage": "G2", "status": "offline_verified" if all(
        r["payment_match"] and r["facts_match"] and r["investigation_match"] and not r["mechanical_errors"]
        and r["authorization_status"] == "pass" and r["idempotency_status"] == "pass" for r in rows) else "fail",
        "scope": "policy_service_scripted_investigation", "mode": "offline_fixture", "code_revision": revision,
        "suite_version": "fs-g2-v1", "dataset_version": "fs-demo-v1", "policy_version": "1", "case_count": len(rows),
        "cases": rows, "model_quality_verified": False, "g2_pass": False,
        "elapsed_ms": int((time.monotonic() - started) * 1000), "model_calls": 0,
        "token_usage": None, "cost_usd": None, "cost_status": "unverified",
        "manual_time_savings": "unverified"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline",), default="offline")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args(argv)
    try:
        suite = json.loads(args.suite.read_text(encoding="utf-8"))
        result = evaluate_suite(suite["cases"], args.revision)
    except (ValueError, KeyError, ImportError):
        print(json.dumps({"status": "blocked", "error": "suite_or_backend_invalid"}))
        return 2
    write_evidence(args.out, result)
    print(json.dumps({"status": result["status"], "case_count": result["case_count"], "g2_pass": False}))
    return 1 if result["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())

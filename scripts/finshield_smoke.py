"""FIN-SHIELD evidence gates. Offline checks never certify G1 or model quality."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AC_IDS = tuple(f"AC-{i:02d}" for i in range(1, 12))
CITATION_FIELDS = ("case_id", "source_id", "record_id", "field", "quote",
                   "dataset_version", "policy_version", "call_index")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()


def citation_key(value):
    return tuple(value.get(k) for k in CITATION_FIELDS)


def verify_derived(evidence, bundle):
    """Recompute the ledger claim independently of production policy helpers."""
    try:
        end = datetime.fromisoformat(bundle["as_of"].replace("Z", "+00:00"))
        start = end - timedelta(minutes=20)
        unique = {}
        for row in bundle["history"]:
            tid = row["transaction_id"]
            if tid in unique and unique[tid] != row:
                return False
            unique[tid] = row
        rows = [r for r in unique.values() if r["transaction_id"] != bundle["current"]["transaction_id"]
                and r["recipient_account_id"] == bundle["current"]["recipient_account_id"]
                and r["status"] == "SETTLED" and start <= datetime.fromisoformat(r["at"].replace("Z", "+00:00")) < end
                and datetime.fromisoformat(r["recorded_at"].replace("Z", "+00:00")) <= end]
        expected = {"history_count": len(rows), "history_total_minor": sum(r["amount_minor"] for r in rows)}
        key = evidence["fact_key"]
        return (key in expected and evidence["field"] == key and type(evidence["fact_value"]) is int
                and evidence["fact_value"] == expected[key] and evidence["quote"] == str(expected[key])
                and evidence["record_id"] == "recent_20m"
                and evidence["source_id"] == bundle["case_id"] + ":derived:recent_20m"
                and evidence["dataset_version"] == bundle["dataset_version"]
                and evidence["policy_version"] == bundle["policy"]["policy_version"]
                and sorted(evidence["derived_from"]) == sorted(r["transaction_id"] for r in rows))
    except (KeyError, TypeError, ValueError):
        return False


def adaptive_lookup(trace):
    """Require a revealed query and its actual evidence from an earlier read."""
    previous = []
    for step in trace:
        action = step.get("action", {})
        query = action.get("query")
        refs = {citation_key(c) for c in action.get("based_on", [])}
        if step.get("mode") == "gemini" and query and refs and step.get("tool_result"):
            for result in previous:
                read = {citation_key(e) for e in result.get("evidence", [])}
                if query in result.get("next_queries", []) and refs <= read:
                    return True
        if step.get("tool_result"):
            previous.append(step["tool_result"])
    return False


def provenance_errors(case):
    """Independently bind every reported fact to returned, scoped evidence."""
    errors = []
    result = case.get("result") or {}
    bundle = case.get("bundle", {})
    source_map = {s["source_id"]: s for s in bundle.get("sources", [])}
    evidence = {}
    for step in result.get("trace", []):
        for e in (step.get("tool_result") or {}).get("evidence", []):
            evidence[citation_key(e)] = e
    for section in ("findings", "counter_evidence", "policy_basis"):
        for claim in (result.get("report") or {}).get(section, []):
            if not claim.get("citations"):
                errors.append("citation_missing")
            for ref in claim.get("citations", []):
                e = evidence.get(citation_key(ref))
                if not e or e.get("case_id") != case.get("case_id"):
                    errors.append("citation_unread_or_wrong_case")
                    continue
                if (e.get("fact_key") != claim.get("fact_key") or
                        type(e.get("fact_value")) is not type(claim.get("fact_value")) or
                        e.get("fact_value") != claim.get("fact_value")):
                    errors.append("citation_fact_mismatch")
                source = source_map.get(ref.get("source_id"))
                if not source and ref.get("record_id") == "recent_20m":
                    if not verify_derived(e, bundle):
                        errors.append("derived_history_mismatch")
                    continue
                if not source or source.get("record_id") != ref.get("record_id"):
                    errors.append("citation_source_missing")
                    continue
                if any(source.get(k) != ref.get(k) for k in ("case_id", "dataset_version", "policy_version")):
                    errors.append("citation_version_mismatch")
                field = ref.get("field")
                fields = source.get("fields", {})
                if field in fields:
                    value = fields[field]
                    quote = str(value).lower() if isinstance(value, bool) else str(value)
                    if ref.get("quote") != quote:
                        errors.append("citation_quote_mismatch")
                elif not e.get("derived_from"):
                    errors.append("citation_field_missing")
    return sorted(set(errors))


def validate_record(record: dict) -> list[str]:
    errors = []
    calls = record.get("model_calls")
    if record.get("mode") != "gemini" or type(calls) is not int or calls < 1:
        errors.append("real_model_required")
    if not record.get("adaptive_lookup_observed") or not adaptive_lookup(record.get("trace", [])):
        errors.append("adaptive_lookup_required")
    restart = record.get("restart_evidence") or {}
    if (not record.get("restart_verified") or restart.get("status") != "pass" or
            restart.get("backend") != "firestore" or
            not restart.get("write_process_id") or not restart.get("read_process_id") or
            restart.get("write_process_id") == restart.get("read_process_id")):
        errors.append("restart_evidence_required")
    results = record.get("ac_results", {})
    if any(results.get(ac) != "pass" for ac in AC_IDS):
        errors.append("acceptance_incomplete")
    details = record.get("ac_details", {})
    if any(not isinstance(details.get(ac), dict) or
           any(k not in details[ac] for k in ("expected", "actual", "evidence")) or
           not details[ac].get("evidence") for ac in AC_IDS):
        errors.append("acceptance_evidence_required")
    human = record.get("human_oracle") or {}
    if not human.get("reviewer") or human.get("verdict") != "pass":
        errors.append("human_oracle_required")
    if not record.get("code_revision") or not record.get("dataset_version") or not record.get("policy_version"):
        errors.append("version_evidence_required")
    if type(calls) is int and calls > 12:
        errors.append("model_call_cap_exceeded")
    return errors


def check_live_authorization(allow_live, max_model_calls, env):
    """Must run before imports which might initialize cloud clients."""
    if allow_live is not True or type(max_model_calls) is not int or not 1 <= max_model_calls <= 12:
        raise ValueError("live_authorization_required")
    required = ("GOOGLE_CLOUD_PROJECT", "FINSHIELD_FIRESTORE_DATABASE", "FINSHIELD_BUDGET_ID",
                "FINSHIELD_MODEL_CALL_CAP", "GEMINI_MODEL")
    if any(not env.get(k, "").strip() for k in required):
        raise ValueError("live_configuration_incomplete")
    try:
        cap = int(env["FINSHIELD_MODEL_CALL_CAP"])
    except (TypeError, ValueError):
        raise ValueError("live_call_cap_invalid") from None
    if not 1 <= cap <= max_model_calls:
        raise ValueError("live_call_cap_invalid")
    if env.get("FINSHIELD_LIVE_CALLS_ENABLED", "").lower() != "true":
        raise ValueError("live_calls_disabled")
    if env.get("FINSHIELD_MODEL_MODE") != "gemini":
        raise ValueError("real_model_required")


def new_record(revision, mode="offline_fixture"):
    if not revision or not revision.strip():
        raise ValueError("revision_required")
    return dict(stage="G1", status="incomplete", mode=mode,
                adaptive_lookup_observed=False, restart_verified=False,
                code_revision=revision, dataset_version="fs-demo-v1", policy_version="1",
                case_id=[], expected={}, actual={}, ac_results={ac: "not_run" for ac in AC_IDS},
                ac_details={}, trace=[], audit=[], elapsed_ms=0, model_calls=0,
                token_usage={"input_tokens": None, "output_tokens": None, "thinking_tokens": None},
                cost_usd=None, cost_status="unverified", human_oracle={"verdict": "not_run"})


def run_offline(revision):
    from app.finshield.dataset import load_bundle
    from app.finshield.policy import check_payment
    from scripts.eval_finshield import exercise_case
    start = time.monotonic()
    record = new_record(revision)
    for template, expected, ac in (("risk-fee", "HOLD_PENDING_REVIEW", "AC-01"),
                                  ("normal-invoice", "SIMULATED_PASSED", "AC-02")):
        bundle = load_bundle(template, f"qa-smoke-{template}")
        actual = check_payment(bundle)
        record["case_id"].append(bundle.case_id)
        record["expected"][template] = expected
        record["actual"][template] = actual.model_dump(mode="json")
        case_oracle = {"expected_investigation_status": "READY", "required_facts": {
            "history_count": 3, "history_total_minor": 270000}, "forbidden_claims": [
            "confirmed criminal", "guaranteed safe", "VIP overrides policy"], "required_counter_evidence": []}
        exercised = exercise_case(case_oracle, bundle)
        record["actual"][template]["offline_workflow"] = exercised
        record["trace"].extend(exercised["trace"])
        record["audit"].extend(exercised["audit"])
        matched = (actual.payment_status == expected and actual.metrics.count == 3 and
                   actual.metrics.total_minor == 270000 and set(actual.evaluated_rule_ids) == {"H1", "H2"})
        # Partial policy checks do not prove UI, model, or counter-evidence coverage.
        record["ac_results"][ac] = "not_run" if matched else "fail"
        record["ac_details"][ac] = {"expected": expected, "actual": actual.payment_status,
            "evidence": f"actual.{template}", "policy_check": "pass" if matched else "fail",
            "workflow_check": "pass" if exercised["investigation_match"] and not exercised["mechanical_errors"]
                and exercised["authorization_status"] == "pass" and exercised["idempotency_status"] == "pass" else "fail",
            "remaining": "HTTP/UI, live model, restart and human semantic acceptance require separate evidence"}
    record["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    record["validation_errors"] = validate_record(record)
    record["status"] = "offline_verified" if all(
        d["policy_check"] == "pass" and d["workflow_check"] == "pass" for d in record["ac_details"].values()) else "fail"
    return record


def write_evidence(path, record):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--max-model-calls", type=int, default=0)
    parser.add_argument("--base-url")
    args = parser.parse_args(argv)
    try:
        if not args.revision.strip():
            raise ValueError("revision_required")
        if args.mode == "live":
            check_live_authorization(args.allow_live, args.max_model_calls, os.environ)
            record = run_live(args)
        else:
            record = run_offline(args.revision)
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc) if type(exc) is ValueError
                          else "backend_or_transport_unavailable"}))
        return 2
    write_evidence(args.out, record)
    print(json.dumps({"status": record["status"], "mode": record["mode"], "g1_pass": not validate_record(record)}))
    return 1 if record["status"] == "fail" else 0 if args.mode == "offline" else 2


def run_live(args):
    """Call only the two packaged templates; no review grants or deployments."""
    from urllib.parse import urlsplit
    import httpx
    origin = args.base_url or os.environ.get("FINSHIELD_ORIGIN", "")
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("https_base_url_required")
    record = new_record(args.revision, "gemini")
    started = time.monotonic()
    with httpx.Client(base_url=origin, timeout=50, follow_redirects=False) as client:
        response = client.post("/api/finshield/sessions", json={}, headers={"Origin": origin})
        response.raise_for_status()
        headers = {"Origin": origin, "X-CSRF-Token": response.json()["csrf_token"]}
        for template in ("risk-fee", "normal-invoice"):
            h = {**headers, "Idempotency-Key": f"qa-{os.getpid()}-{time.time_ns()}"}
            response = client.post("/api/finshield/cases", json={"template_id": template}, headers=h)
            response.raise_for_status()
            case_id = response.json()["case_id"]
            record["case_id"].append(case_id)
            for endpoint in ("payment", "investigation"):
                h["Idempotency-Key"] = f"qa-{endpoint}-{time.time_ns()}"
                response = client.post(f"/api/finshield/cases/{case_id}/{endpoint}", json={}, headers=h)
                response.raise_for_status()
            response = client.get(f"/api/finshield/cases/{case_id}")
            response.raise_for_status()
            case = response.json()
            record["actual"][template] = case
            record["audit"].extend(case.get("events", []))
            trace = (case.get("result") or {}).get("trace", [])
            record["trace"].extend(trace)
            calls = case.get("model_calls")
            record["model_calls"] = record["model_calls"] + calls if type(calls) is int and type(record["model_calls"]) is int else None
            record["ac_details"][template] = {"provenance_errors": provenance_errors(case)}
    record["adaptive_lookup_observed"] = adaptive_lookup(record["trace"])
    record["model_call_count_status"] = "server_counter" if type(record["model_calls"]) is int else "unverified"
    for key in record["token_usage"]:
        values = [step.get(key) for step in record["trace"]]
        record["token_usage"][key] = sum(values) if values and all(type(v) is int for v in values) else None
    record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    record["validation_errors"] = validate_record(record)
    # G1 also needs separately captured adversarial, restart, UI and human evidence.
    return record


if __name__ == "__main__":
    raise SystemExit(main())

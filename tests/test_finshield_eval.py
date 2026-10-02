"""Independent case oracles are frozen input, never production-derived."""
import copy
import json
from pathlib import Path

import pytest

from scripts.eval_finshield import validate_suite, evaluate_suite

SUITE = Path(__file__).resolve().parents[1] / "eval/finshield/g2-v1.json"


def test_display_templates_are_not_independent_evaluation():
    with pytest.raises(ValueError, match="display_template"):
        validate_suite([{"template_id": "risk-fee"}])


def test_independent_suite_has_eight_distinct_scenarios():
    cases = json.loads(SUITE.read_text(encoding="utf-8"))["cases"]
    validate_suite(cases)
    assert len(cases) == 8
    assert {c["category"] for c in cases} == {
        "high_risk", "normal", "counter_evidence", "missing_kyc",
        "missing_history", "shared_device", "injection", "tool_failure",
    }


def test_duplicate_case_or_prompt_copy_is_rejected():
    cases = json.loads(SUITE.read_text(encoding="utf-8"))["cases"]
    duplicate = copy.deepcopy(cases)
    duplicate[-1] = copy.deepcopy(duplicate[0])
    with pytest.raises(ValueError, match="independent_case"):
        validate_suite(duplicate)
    copied = copy.deepcopy(cases)
    copied[0]["conversation"] = "Pay a verification fee before receiving your sale proceeds."
    with pytest.raises(ValueError, match="prompt_example"):
        validate_suite(copied)


def test_offline_suite_exercises_real_policy_against_frozen_oracles():
    cases = json.loads(SUITE.read_text(encoding="utf-8"))["cases"]
    result = evaluate_suite(cases, revision="qa-working-tree")
    assert result["status"] == "offline_verified"
    assert result["model_quality_verified"] is False
    assert result["cost_usd"] is None
    assert result["case_count"] == 8
    assert all(row["payment_match"] for row in result["cases"])
    assert all(row["facts_match"] for row in result["cases"])
    assert all(row["investigation_match"] for row in result["cases"])
    assert all(row["authorization_status"] == "pass" for row in result["cases"])
    assert all(row["idempotency_status"] == "pass" for row in result["cases"])
    assert all(row["human_semantic_verdict"] == "not_run" for row in result["cases"])
    assert result["cases"][3]["investigation_status"] == "INCOMPLETE"
    assert result["cases"][7]["investigation_status"] == "INCOMPLETE"


def test_wrong_expected_outcome_fails_comparison():
    cases = json.loads(SUITE.read_text(encoding="utf-8"))["cases"]
    cases[0]["expected_payment_status"] = "SIMULATED_PASSED"
    result = evaluate_suite(cases, revision="qa-working-tree")
    assert result["status"] == "fail"
    assert result["cases"][0]["payment_match"] is False

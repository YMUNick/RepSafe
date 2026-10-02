import pytest

from app.finshield.dataset import load_bundle
from app.finshield.models import Action, Citation, ModelReply, Report, Scope, ServiceError, ToolQuery
from app.finshield.investigator import run_investigation, make_offline_step
from tests.test_finshield_state import held


def reply(action):
    return ModelReply(action=action, model='scripted', mode='offline_fixture')


def test_adaptive_lookup_uses_previous_result():
    observed = []
    def step(observations, seconds):
        observed.append(observations)
        if not observations:
            return reply(Action(kind='call_tool', query=ToolQuery(tool='transactions', record_id='current')))
        if len(observations) == 1:
            previous = observations[0]
            q = next(q for q in previous.next_queries if q.tool == 'profile_kyc')
            ref = Citation.model_validate(previous.evidence[0].model_dump(include=set(Citation.model_fields)))
            return reply(Action(kind='call_tool', query=q, based_on=(ref,)))
        return reply(Action(kind='finish', report=Report(findings=(), counter_evidence=(), policy_basis=(), missing_information=('Policy evidence has not been retrieved.',), suggested_next_steps=('Request the missing records',))))
    b = load_bundle('risk-fee', 'case-a')
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, step, lambda: None)
    assert len(observed) == 3
    assert observed[2][1].query.tool == 'profile_kyc'
    assert result.status == 'INCOMPLETE'
    assert len(result.trace) == 3


@pytest.mark.parametrize('template', ['risk-fee', 'normal-invoice'])
def test_offline_workflow_evidence_and_honest_mode(template):
    b = load_bundle(template, 'case-a')
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, make_offline_step(b), lambda: None)
    assert result.status == 'READY'
    assert len(result.trace) == 5
    assert all(step.mode == 'offline_fixture' for step in result.trace)
    assert result.report.policy_basis and result.report.counter_evidence
    facts = {c.fact_key: c.fact_value for c in result.report.findings}
    assert facts['history_count'] == 3
    assert facts['history_total_minor'] == 270000


@pytest.mark.parametrize('failure', ['timeout', 'budget', 'forbidden', 'bad_output'])
def test_failure_never_changes_payment(failure):
    service, scope, case = held()
    lease = service.claim_run(scope, 'run-0001')
    def step(observations, seconds):
        if failure == 'timeout':
            raise TimeoutError()
        if failure == 'forbidden':
            return reply(Action(kind='call_tool', query=ToolQuery(tool='profile_kyc', record_id='another-case')))
        return {'invalid': 'model output'}
    def budget():
        if failure == 'budget':
            raise ServiceError('model_budget_exhausted', 409)
    result = run_investigation(scope, case.bundle, step, budget)
    assert result.status == 'INCOMPLETE'
    current = service.finish_run(scope, lease.run_id, result)
    assert current.payment_status == case.payment_status
    assert current.events == case.events


def test_missing_profile_never_becomes_ready():
    b = load_bundle('normal-invoice', 'case-a')
    b = b.model_copy(update={'sources': tuple(s for s in b.sources if not s.record_id.endswith('-profile'))})
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, make_offline_step(b), lambda: None)
    assert result.status == 'INCOMPLETE'


def test_late_result_and_tool_cap():
    b = load_bundle('risk-fee', 'case-a')
    now = [0.0]
    def late(observations, seconds):
        now[0] = 46.0
        return reply(Action(kind='call_tool', query=ToolQuery(tool='transactions', record_id='current')))
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, late, lambda: None, clock=lambda: now[0])
    assert result.status == 'INCOMPLETE' and not result.trace


def test_invalid_claim_is_not_exposed_in_trace():
    b = load_bundle('risk-fee', 'case-a')
    base = make_offline_step(b)
    def step(observations, seconds):
        result = base(observations, seconds)
        if result.action.kind == 'finish':
            report = result.action.report
            forged = report.findings[0].model_copy(update={'fact_value': 999, 'text':'untrusted-invalid-output'})
            return result.model_copy(update={'action': result.action.model_copy(update={'report': report.model_copy(update={'findings':(forged,)})})})
        return result
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, step, lambda: None)
    assert result.status == 'INCOMPLETE' and result.report is None
    assert 'untrusted-invalid-output' not in result.model_dump_json()


def test_fifth_tool_is_rejected_before_execution():
    b = load_bundle('risk-fee', 'case-a')
    base = make_offline_step(b)
    calls = []
    def step(observations, seconds):
        if len(observations) == 4:
            previous = observations[-1]
            return reply(Action(kind='call_tool', query=previous.next_queries[0], based_on=(Citation.model_validate(previous.evidence[0].model_dump(include=set(Citation.model_fields))),)))
        return base(observations, seconds)
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, step, lambda:calls.append(1))
    assert result.reason_codes == ('tool_call_limit',)
    assert len(calls) == 5 and len(result.trace) == 4


def test_oversized_source_stops_with_no_raw_source_in_trace():
    b = load_bundle('risk-fee', 'case-a')
    b = b.model_copy(update={'sources':tuple(s.model_copy(update={'fields':{'conversation':'too-long-' * 1000}}) if s.record_id == 'current' else s for s in b.sources)})
    result = run_investigation(Scope('s', b.case_id, 'visitor', False), b, make_offline_step(b), lambda:None)
    assert result.reason_codes == ('tool_output_limit',) and result.trace == ()

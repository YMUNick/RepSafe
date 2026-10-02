from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta

import pytest

from app.finshield.models import Scope, ReviewCommand, ServiceError, Session, ReviewerGrant, RunResult
from app.finshield.service import CaseService
from app.finshield.store import session_key
from tests.finshield_fakes import MemoryStore

NOW = datetime(2026, 10, 2, 4, tzinfo=timezone.utc)


def held(store=None):
    store = store or MemoryStore()
    key = session_key('session-a')
    session = Session(session_id='session-a', token_hash='token', csrf_hash='csrf', expires_at=NOW + timedelta(hours=1))
    store.atomic((key,), lambda docs: {key: session.model_dump(mode='json')})
    service = CaseService(store, clock=lambda: NOW)
    case = service.create('session-a', 'risk-fee', 'create-001')
    def grant(docs):
        session = Session.model_validate(docs[key])
        assert case.case_id in session.case_ids
        grant = ReviewerGrant(actor_id='reviewer-a', case_id=case.case_id, expires_at=NOW + timedelta(minutes=15))
        return {key: session.model_copy(update={'review_grants': {case.case_id: grant}}).model_dump(mode='json')}
    store.atomic((key,), grant)
    scope = Scope('session-a', case.case_id, 'reviewer-a', True)
    return service, scope, service.check(scope, 'payment-001')


def test_review_replay_and_conflict():
    service, scope, case = held()
    cmd = ReviewCommand(action='approve', reason='Reviewed the synthetic invoice.', expected_version=case.version)
    first = service.review(scope, cmd, 'decision-001')
    assert first.payment_status == 'SIMULATED_PASSED'
    assert service.review(scope, cmd, 'decision-001') == first
    with pytest.raises(ServiceError, match='idempotency_conflict'):
        service.review(scope, cmd.model_copy(update={'action': 'cancel'}), 'decision-001')
    assert len(service.get(scope).events) == len(case.events) + 1
    assert first.operations == {}


def test_concurrent_decisions():
    service, scope, case = held()
    def attempt(action):
        try:
            return service.review(scope, ReviewCommand(action=action, reason='Manual decision.', expected_version=case.version), 'decision-' + action).payment_status
        except ServiceError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['approve', 'cancel']))
    assert results.count(409) == 1
    assert len(service.get(scope).events) == len(case.events) + 1


@pytest.mark.parametrize('action,expected', [('cancel','SIMULATED_CANCELLED'), ('dismiss','HOLD_PENDING_REVIEW'), ('keep_hold','HOLD_PENDING_REVIEW'), ('escalate','HOLD_PENDING_REVIEW')])
def test_review_targets(action, expected):
    service, scope, case = held()
    result = service.review(scope, ReviewCommand(action=action, reason='Manually reviewed.', expected_version=case.version), 'decision-001')
    assert result.payment_status == expected


def test_persisted_grant_required_even_with_forged_scope():
    service, scope, case = held()
    key = session_key(scope.session_id)
    doc = service.store.read(key)
    doc['review_grants'] = {}
    service.store.atomic((key,), lambda docs: {key: doc})
    with pytest.raises(ServiceError) as e:
        service.review(scope, ReviewCommand(action='approve', reason='Manual review.', expected_version=case.version), 'decision-001')
    assert e.value.status_code == 403
    assert service.get(scope).payment_status == 'HOLD_PENDING_REVIEW'


def test_run_recovery_late_finish_and_review_merge():
    service, scope, case = held()
    lease = service.claim_run(scope, 'run-0001')
    assert service.claim_run(scope, 'run-0001').acquired is False
    current = service.get(scope)
    service.review(scope, ReviewCommand(action='cancel', reason='Manual review.', expected_version=current.version), 'decision-001')
    finished = service.finish_run(scope, lease.run_id, RunResult(status='INCOMPLETE', reason_codes=('timeout',)))
    assert finished.payment_status == 'SIMULATED_CANCELLED'
    service, scope, _ = held()
    lease = service.claim_run(scope, 'run-0001')
    service.clock = lambda: NOW + timedelta(seconds=61)
    assert service.get(scope).result.reason_codes == ('interrupted',)
    with pytest.raises(ServiceError):
        service.finish_run(scope, lease.run_id, RunResult(status='READY'))
    assert service.get(scope).payment_status == 'HOLD_PENDING_REVIEW'


def test_payment_new_key_is_side_effect_free_and_quota_is_shared():
    service, scope, case = held()
    assert service.check(scope, 'payment-002').events == case.events
    service.reserve_model_call(scope, 'approved-budget', 1)
    with pytest.raises(ServiceError, match='model_budget_exhausted'):
        service.reserve_model_call(scope, 'approved-budget', 1)
    assert service.get(scope).payment_status == 'HOLD_PENDING_REVIEW'


def test_create_key_cannot_change_template():
    service, scope, _ = held()
    with pytest.raises(ServiceError, match='idempotency_conflict'):
        service.create(scope.session_id, 'normal-invoice', 'create-001')


def test_quota_cannot_be_bypassed_by_a_different_session():
    from app.finshield.auth import SessionAuth
    service, scope, _ = held()
    service.reserve_model_call(scope, 'approved-global-budget', 1)
    auth = SessionAuth(service.store, {}, clock=lambda:NOW)
    token, _, session = auth.new_session()
    case = service.create(session.session_id, 'risk-fee', 'create-002')
    with pytest.raises(ServiceError, match='model_budget_exhausted'):
        service.reserve_model_call(auth.resolve(token, case.case_id), 'approved-global-budget', 1)


def test_storage_failure_does_not_mutate_state():
    service, scope, case = held()
    def unavailable(keys, reduce):
        raise ServiceError('storage_unavailable', 503)
    service.store.atomic = unavailable
    with pytest.raises(ServiceError, match='storage_unavailable'):
        service.review(scope, ReviewCommand(action='approve', reason='Manual review.', expected_version=case.version), 'decision-001')
    assert service.store.read('case-' + case.case_id)['payment_status'] == 'HOLD_PENDING_REVIEW'

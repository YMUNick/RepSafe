from datetime import timedelta

import pytest

from app.finshield.auth import SessionAuth, token_hash
from app.finshield.dataset import load_bundle
from app.finshield.models import Scope, ToolQuery, ServiceError
from app.finshield.service import CaseService
from app.finshield.tools import dispatch
from tests.finshield_fakes import MemoryStore
from tests.test_finshield_state import NOW


def test_scope_and_auth_boundary():
    b = load_bundle('risk-fee', 'case-a')
    with pytest.raises(ServiceError):
        dispatch(Scope('s', 'case-b', 'visitor', False), b, ToolQuery(tool='transactions', record_id='current'), 1)
    with pytest.raises(ServiceError):
        dispatch(Scope('s', 'case-a', 'visitor', False), b, ToolQuery(tool='policy_case_history', record_id='normal-precedent'), 1)


def test_session_tokens_case_grants_and_expiration():
    store = MemoryStore()
    auth = SessionAuth(store, {'reviewer-a': token_hash('x' * 43)}, clock=lambda: NOW)
    service = CaseService(store, clock=lambda: NOW)
    token, csrf, session = auth.new_session()
    case = service.create(session.session_id, 'risk-fee', 'create-001')
    assert not auth.resolve(token, case.case_id).can_review
    assert session.token_hash != token and session.csrf_hash != csrf
    with pytest.raises(ServiceError):
        auth.resolve(session.session_id + '.wrong', case.case_id)
    with pytest.raises(ServiceError):
        auth.grant(token, case.case_id, 'reviewer-a', 'wrong')
    auth.grant(token, case.case_id, 'reviewer-a', 'x' * 43)
    assert auth.resolve(token, case.case_id).can_review
    second = service.create(session.session_id, 'normal-invoice', 'create-002')
    assert not auth.resolve(token, second.case_id).can_review
    other, _, _ = auth.new_session()
    with pytest.raises(ServiceError) as e:
        auth.resolve(other, case.case_id)
    assert e.value.status_code == 404
    auth.clock = lambda: NOW + timedelta(minutes=16)
    assert not auth.resolve(token, case.case_id).can_review


def test_login_attempt_limit_is_durable():
    store = MemoryStore()
    auth = SessionAuth(store, {'reviewer-a': token_hash('x' * 43)}, clock=lambda: NOW)
    token, _, session = auth.new_session()
    case = CaseService(store, clock=lambda: NOW).create(session.session_id, 'risk-fee', 'create-001')
    for _ in range(5):
        with pytest.raises(ServiceError):
            auth.grant(token, case.case_id, 'reviewer-a', 'wrong')
    with pytest.raises(ServiceError, match='review_login_locked'):
        SessionAuth(store, {'reviewer-a': token_hash('x' * 43)}, clock=lambda: NOW).grant(token, case.case_id, 'reviewer-a', 'x' * 43)


def test_sources_recorded_after_as_of_are_not_returned():
    b = load_bundle('risk-fee', 'case-a')
    b = b.model_copy(update={'sources': tuple(s.model_copy(update={'recorded_at': b.as_of + timedelta(seconds=1)}) for s in b.sources)})
    result = dispatch(Scope('s', b.case_id, 'visitor', False), b, ToolQuery(tool='transactions', record_id='current'), 1)
    assert result.evidence == () and result.missing_information


def test_public_sessions_have_durable_global_creation_cap():
    store = MemoryStore()
    auth = SessionAuth(store, {}, clock=lambda: NOW, session_cap=2)
    auth.new_session()
    auth.new_session()
    with pytest.raises(ServiceError, match='session_capacity_reached'):
        SessionAuth(store, {}, clock=lambda: NOW, session_cap=2).new_session()
    assert len([key for key in store.docs if key.startswith('session-')]) == 2


def test_missing_complete_history_cannot_return_derived_facts():
    b = load_bundle('risk-fee', 'case-a').model_copy(update={'history_complete':False})
    result = dispatch(Scope('s', b.case_id, 'visitor', False), b, ToolQuery(tool='transactions', record_id='recent_20m'), 1)
    assert not result.evidence and result.missing_information


@pytest.mark.parametrize('invalid_policy', ['missing', 'future', 'version'])
def test_unavailable_policy_cannot_be_cited(invalid_policy):
    b = load_bundle('risk-fee', 'case-a')
    policy = None if invalid_policy == 'missing' else b.policy.model_copy(update={
        'effective_at': b.as_of + timedelta(seconds=1)} if invalid_policy == 'future' else {'policy_version':'2'})
    b = b.model_copy(update={'policy': policy})
    result = dispatch(Scope('s', b.case_id, 'visitor', False), b, ToolQuery(tool='policy_case_history', record_id='DEMO-PAYMENT'), 1)
    assert result.evidence == () and result.missing_information


def test_uppercase_reviewer_hash_authenticates_same_secret():
    store = MemoryStore()
    auth = SessionAuth(store, {'reviewer-a':token_hash('x' * 43).upper()}, clock=lambda:NOW)
    token, _, session = auth.new_session()
    case = CaseService(store, clock=lambda:NOW).create(session.session_id, 'risk-fee', 'create-001')
    auth.grant(token, case.case_id, 'reviewer-a', 'x' * 43)
    assert auth.resolve(token, case.case_id).can_review

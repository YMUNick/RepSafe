from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.finshield.auth import SessionAuth, token_hash
from app.finshield.investigator import make_offline_step, answer_offline_vip
from app.finshield.routes import build_router
from app.finshield.service import CaseService
from app.finshield.settings import FinShieldSettings
from app.finshield.store import FirestoreStore
from tests.finshield_fakes import MemoryStore
from tests.test_finshield_state import NOW


def client_for(store=None, config=None):
    store = store if store is not None else MemoryStore()
    service = CaseService(store, clock=lambda: NOW)
    auth = SessionAuth(store, {'reviewer-a': token_hash('x' * 43)}, clock=lambda: NOW)
    config = config or FinShieldSettings(enabled=True, allowed_origin='https://testserver')
    app = FastAPI()
    app.include_router(build_router(service, auth, make_offline_step, answer_offline_vip, config))
    return TestClient(app, base_url='https://testserver'), service, auth


def bootstrap(client):
    result = client.post('/api/finshield/sessions', json={}, headers={'Origin': 'https://testserver'})
    assert result.status_code == 200
    assert 'HttpOnly' in result.headers['set-cookie'] and 'Secure' in result.headers['set-cookie']
    client.headers.update({'Origin': 'https://testserver', 'X-CSRF-Token': result.json()['csrf_token'], 'Idempotency-Key': 'create-001'})
    return client.post('/api/finshield/cases', json={'template_id': 'risk-fee'}).json()


def test_module_off_keeps_existing_home():
    from app.main import app
    with TestClient(app) as client:
        assert client.get('/finshield').status_code == 404
        assert client.post('/api/finshield/cases', json={'template_id':'risk-fee'}).status_code == 404
        assert client.get('/health').json() == {'status':'ok', 'mode':'offline_fixture', 'url_reputation':'fixture'}
        assert 'id="shot-preview"' in client.get('/').text
        assert client.get('/api/config').json()['finshield_enabled'] is False


def test_public_audit_redacts_session_actor_without_changing_private_audit():
    import json
    client, service, auth = client_for()
    case = bootstrap(client)
    cookie = client.cookies.get('fs_session')
    session_id = cookie.split('.')[0]
    path = '/api/finshield/cases/' + case['case_id']
    payment = client.post(path + '/payment', json={}, headers={'Idempotency-Key': 'redaction-payment'})
    assert payment.status_code == 200
    for response in (payment, client.get(path), client.get(path + '/report')):
        assert session_id not in json.dumps(response.json())
        assert response.json()['events'][0]['actor_id'] == 'visitor'
    private = service.get(auth.resolve(cookie, case['case_id']))
    assert private.events[0].actor_id == 'visitor:' + session_id


def test_cookie_csrf_review_and_investigation_flow():
    client, _, _ = client_for()
    case = bootstrap(client)
    path = '/api/finshield/cases/' + case['case_id']
    assert not case['permissions']['can_review'] and case['mode'] == 'offline_fixture'
    assert not {'session_id','operations','token_hash'} & set(case)
    case = client.post(path + '/payment', json={}, headers={'Idempotency-Key':'payment-001'}).json()
    assert case['payment_status'] == 'HOLD_PENDING_REVIEW'
    command = {'action':'approve', 'reason':'Manual review.', 'expected_version':case['version'], 'evidence_refs':[]}
    assert client.post(path + '/review', json=command).status_code == 403
    result = client.post(path + '/investigation', json={}, headers={'Idempotency-Key':'investigate-001'})
    assert result.status_code == 200 and result.json()['status'] == 'READY'
    case = client.get(path).json()
    assert case['payment_status'] == 'HOLD_PENDING_REVIEW' and case['result']['report']['policy_basis']
    answer = client.post(path + '/vip', json={}, headers={'Idempotency-Key':'vip-00001'})
    assert answer.status_code == 200 and 'Offline fixture' in answer.json()['answer']
    assert client.get(path).json()['payment_status'] == 'HOLD_PENDING_REVIEW'
    login = client.post('/api/finshield/review-login', json={'case_id':case['case_id'], 'reviewer_id':'reviewer-a', 'secret':'x' * 43})
    assert login.status_code == 204
    case = client.get(path).json()
    command['expected_version'] = case['version']
    first = client.post(path + '/review', json=command, headers={'Idempotency-Key':'review-001'})
    assert first.status_code == 200 and first.json()['payment_status'] == 'SIMULATED_PASSED'
    assert client.post(path + '/review', json=command, headers={'Idempotency-Key':'review-001'}).json() == first.json()
    assert client.get(path + '/report').status_code == 200


@pytest.mark.parametrize('header,value', [('Origin','https://evil.example'), ('X-CSRF-Token','wrong')])
def test_write_boundaries(header, value):
    client, _, _ = client_for()
    case = bootstrap(client)
    response = client.post('/api/finshield/cases/' + case['case_id'] + '/payment', json={}, headers={header:value})
    assert response.status_code == 403


def test_cross_session_and_fake_actor_are_rejected_without_echo():
    store = MemoryStore()
    client, _, _ = client_for(store)
    case = bootstrap(client)
    other, _, _ = client_for(store)
    bootstrap(other)
    path = '/api/finshield/cases/' + case['case_id']
    assert other.get(path).status_code == 404
    result = client.post('/api/finshield/review-login', json={'case_id':case['case_id'], 'reviewer_id':'reviewer-a', 'secret':'sensitive-secret', 'actor':'forged'})
    assert result.status_code == 422
    assert 'sensitive-secret' not in result.text and result.json() == {'error':{'code':'invalid_request'}}


def test_missing_storage_is_503_not_import_failure():
    client, _, _ = client_for(FirestoreStore())
    response = client.post('/api/finshield/sessions', json={}, headers={'Origin':'https://testserver'})
    assert response.status_code == 503 and response.json() == {'error':{'code':'storage_unavailable'}}


def test_live_disabled_does_not_invoke_injected_model():
    client, _, _ = client_for(config=FinShieldSettings(enabled=True, allowed_origin='https://testserver', model_mode='gemini'))
    case = bootstrap(client)
    path = '/api/finshield/cases/' + case['case_id']
    client.post(path + '/payment', json={})
    response = client.post(path + '/investigation', json={})
    assert response.json()['status'] == 'INCOMPLETE'
    assert response.json()['trace'] == []
    assert client.get(path).json()['payment_status'] == 'HOLD_PENDING_REVIEW'


def test_https_cookie_stays_secure_with_loopback_flag_enabled():
    client, _, _ = client_for(config=FinShieldSettings(enabled=True, allowed_origin='https://testserver', allow_loopback_http=True))
    bootstrap(client)

"""Recovery contracts exercised through real routes and atomic in-memory storage."""
from copy import deepcopy
from base64 import b64encode
from datetime import timedelta
import json
import random
import zlib

import pytest

from app.finshield.auth import token_hash
from app.finshield.investigator import make_offline_step, run_investigation
from app.finshield.models import Citation, ReviewCommand, ServiceError
from app.finshield.service import CaseService
from app.finshield.store import session_key
from tests.test_finshield_api import bootstrap, client_for
from tests.test_finshield_state import NOW, held


@pytest.mark.parametrize('body', [{}, {'resume_only': True}, {'resume_only': False}])
def test_valid_session_resumes_without_cookie_rotation_or_storage_writes(body):
    client, service, auth = client_for()
    first = bootstrap(client)
    second = client.post('/api/finshield/cases', json={'template_id': 'normal-invoice'},
                         headers={'Idempotency-Key': 'create-second'}).json()
    cookie, csrf = client.cookies.get('fs_session'), client.headers['X-CSRF-Token']
    auth.grant(cookie, first['case_id'], 'reviewer-a', 'x' * 43)
    auth.session_cap = 1  # Resume must still work once allocation is exhausted.
    before = deepcopy(service.store.docs)
    response = client.post('/api/finshield/sessions', json=body)
    assert response.status_code == 200
    assert 'set-cookie' not in response.headers
    assert client.cookies.get('fs_session') == cookie
    assert response.json() == {
        'csrf_token': csrf, 'reviewer_available': True,
        'cases': [{'case_id': first['case_id'], 'template_id': 'risk-fee'},
                  {'case_id': second['case_id'], 'template_id': 'normal-invoice'}],
    }
    assert service.store.docs == before
    assert cookie.split('.')[0] not in response.text


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'forged', 'expired'])
def test_resume_only_rejects_invalid_cookie_without_allocating(kind):
    client, service, auth = client_for()
    if kind != 'missing':
        bootstrap(client)
        cookie = client.cookies.get('fs_session')
        client.cookies.clear()
        client.cookies.set('fs_session', 'bad' if kind == 'malformed' else
                           cookie.split('.')[0] + '.' + 'z' * 43 if kind == 'forged' else cookie)
        if kind == 'expired':
            auth.clock = lambda: NOW + timedelta(hours=24)
    before = deepcopy(service.store.docs)
    response = client.post('/api/finshield/sessions', json={'resume_only': True},
                           headers={'Origin': 'https://testserver'})
    assert response.status_code == 401
    assert response.json() == {'error': {'code': 'unauthorized'}}
    assert 'set-cookie' not in response.headers
    assert service.store.docs == before


def test_expired_session_can_be_replaced_by_explicit_creation():
    client, service, auth = client_for()
    bootstrap(client)
    original = client.cookies.get('fs_session')
    auth.clock = lambda: NOW + timedelta(hours=24)
    response = client.post('/api/finshield/sessions', json={'resume_only': False})
    assert response.status_code == 200
    assert response.json()['cases'] == []
    assert client.cookies.get('fs_session') != original
    assert service.store.read('quota-session-creation')['used'] == 2


def test_cross_tab_resume_derives_stable_csrf_and_keeps_legacy_tabs_valid():
    client, service, auth = client_for()
    case = bootstrap(client)
    cookie = client.cookies.get('fs_session')
    sk = session_key(auth.session(cookie).session_id)
    legacy = service.store.read(sk)
    legacy['csrf_hash'] = token_hash('legacy-tab-csrf')
    service.store.atomic((sk,), lambda docs: {sk: legacy})
    other, _, _ = client_for(service.store)
    other.cookies.set('fs_session', cookie)
    response = other.post('/api/finshield/sessions', json={'resume_only': True},
                          headers={'Origin': 'https://testserver'})
    assert response.status_code == 200
    csrf = response.json()['csrf_token']
    assert csrf == client.headers['X-CSRF-Token']
    assert csrf not in (cookie, token_hash(cookie), 'legacy-tab-csrf')
    path = '/api/finshield/cases/' + case['case_id'] + '/payment'
    for tab, value, key in ((other, csrf, 'payment-new-tab'),
                            (client, 'legacy-tab-csrf', 'payment-old-tab')):
        assert tab.post(path, json={}, headers={'Origin': 'https://testserver',
                        'X-CSRF-Token': value, 'Idempotency-Key': key}).status_code == 200
    assert service.store.read(sk) == legacy


@pytest.mark.parametrize('value', ['true', 1, None])
def test_resume_only_requires_a_boolean(value):
    client, service, _ = client_for()
    response = client.post('/api/finshield/sessions', json={'resume_only': value},
                           headers={'Origin': 'https://testserver'})
    assert response.status_code == 422
    assert service.store.docs == {}


@pytest.mark.parametrize('configured', [False, True])
def test_unconfigured_reviewer_does_not_consume_attempts_even_when_other_reviewer_exists(configured):
    client, service, auth = client_for()
    if not configured:
        auth.reviewer_hashes = {}
    case = bootstrap(client)
    assert case['permissions'] == {'can_review': False, 'reviewer_available': configured}
    body = {'case_id': case['case_id'], 'reviewer_id': 'reviewer-b', 'secret': 'arbitrary'}
    before = deepcopy(service.store.docs)
    for _ in range(7):
        response = client.post('/api/finshield/review-login', json=body)
        assert response.status_code == 503
        assert response.json() == {'error': {'code': 'reviewer_unavailable'}}
    assert service.store.docs == before
    if configured:
        body.update(reviewer_id='reviewer-a', secret='x' * 43)
        assert client.post('/api/finshield/review-login', json=body).status_code == 204
    path = '/api/finshield/cases/' + case['case_id']
    responses = [client.get(path), client.get(path + '/report'),
                 client.post(path + '/payment', json={}, headers={'Idempotency-Key': 'payment-permissions'})]
    if configured:
        responses.append(client.post(path + '/review', json={'action': 'keep_hold', 'reason': 'Reviewed.',
                         'expected_version': responses[-1].json()['version']},
                         headers={'Idempotency-Key': 'review-permissions'}))
    for response in responses:
        assert response.status_code == 200
        assert response.json()['permissions'] == {'can_review': configured, 'reviewer_available': configured}


def test_unavailable_reviewer_still_checks_origin_csrf_and_case_scope_first():
    client, service, auth = client_for()
    case = bootstrap(client)
    auth.reviewer_hashes = {}
    body = {'case_id': case['case_id'], 'reviewer_id': 'reviewer-a', 'secret': 'arbitrary'}
    before = deepcopy(service.store.docs)
    for headers, expected in (({'Origin': 'https://evil.example'}, 'origin_forbidden'),
                              ({'X-CSRF-Token': 'bad'}, 'csrf_forbidden')):
        response = client.post('/api/finshield/review-login', json=body, headers=headers)
        assert response.status_code == 403 and response.json()['error']['code'] == expected
    response = client.post('/api/finshield/review-login', json={**body, 'case_id': 'not-owned'})
    assert response.status_code == 404
    assert service.store.docs == before


def investigate_held_case(service, scope):
    lease = service.claim_run(scope, 'investigate-recovery')
    result = run_investigation(scope, lease.current.bundle, make_offline_step(lease.current.bundle), lambda: None)
    assert result.status == 'READY'
    return service.finish_run(scope, lease.run_id, result)


def test_repeated_reviews_keep_full_historical_responses_across_restart_and_approval():
    service, scope, original = held()
    case = investigate_held_case(service, scope)
    history = []
    for index in range(12):
        command = ReviewCommand(action='keep_hold', reason='Manual follow-up ' + str(index), expected_version=case.version)
        key = 'keep-hold-' + str(index)
        case = service.review(scope, command, key)
        history.append((command, key, case.model_dump(mode='json')))
    before = service.store.read('case-' + scope.case_id)
    restarted = CaseService(service.store, clock=lambda: NOW)
    for command, key, expected in history:
        assert restarted.review(scope, command, key).model_dump(mode='json') == expected
    assert restarted.check(scope, 'payment-001') == original
    command = ReviewCommand(action='approve', reason='Manual approval.', expected_version=case.version)
    approved = restarted.review(scope, command, 'final-approve')
    for previous, key, expected in history:
        assert restarted.review(scope, previous, key).model_dump(mode='json') == expected
    current = restarted.get(scope)
    assert current.payment_status == 'SIMULATED_PASSED'
    assert current.investigation_status == 'READY'
    assert current.result == case.result
    assert current.events[:-1] == case.events
    assert restarted.review(scope, command, 'final-approve') == approved
    after = service.store.read('case-' + scope.case_id)
    assert len(json.dumps(after).encode()) <= 256 * 1024
    assert len(after['operations']) == len(before['operations']) + 1
    for key, operation in before['operations'].items():
        assert after['operations'][key]['request_hash'] == operation['request_hash']


def test_legacy_full_snapshots_are_migrated_losslessly_before_the_size_cap():
    service, scope, original = held()
    case = investigate_held_case(service, scope)
    history = []
    for index in range(5):
        command = ReviewCommand(action='keep_hold', reason='Legacy review ' + str(index), expected_version=case.version)
        key = 'legacy-hold-' + str(index)
        case = service.review(scope, command, key)
        history.append((command, key, case.model_dump(mode='json')))
    ck = 'case-' + scope.case_id
    legacy = service.store.read(ck)
    # Persist the actual old schema: full response objects, including a payment
    # response from before investigation. No production encoding helper is used.
    legacy['operations']['payment:payment-001']['response'] = original.model_dump(mode='json')
    for command, key, expected in history:
        legacy['operations']['review:' + key]['response'] = expected
    service.store.atomic((ck,), lambda docs: {ck: legacy})
    legacy_size = len(json.dumps(legacy).encode())
    restarted = CaseService(service.store, clock=lambda: NOW)
    assert restarted.get(scope) == case
    migrated = service.store.read(ck)
    assert len(json.dumps(migrated).encode()) < legacy_size // 2
    assert migrated['events'] == legacy['events']
    for key, operation in legacy['operations'].items():
        assert migrated['operations'][key]['request_hash'] == operation['request_hash']
    for command, key, expected in history:
        assert restarted.review(scope, command, key).model_dump(mode='json') == expected
    assert restarted.check(scope, 'payment-001') == original
    final = restarted.review(scope, ReviewCommand(action='cancel', reason='Manual resolution.',
                             expected_version=case.version), 'legacy-cancel')
    assert final.payment_status == 'SIMULATED_CANCELLED'
    for command, key, expected in history:
        assert restarted.review(scope, command, key).model_dump(mode='json') == expected


@pytest.mark.parametrize('action', ['approve', 'cancel'])
@pytest.mark.parametrize('operation', ['review', 'payment'])
def test_operation_capacity_reserves_a_terminal_decision_including_after_noop_payments(action, operation):
    service, scope, case = held()
    for index in range(40):
        before = deepcopy(service.store.docs)
        try:
            if operation == 'review':
                case = service.review(scope, ReviewCommand(action='keep_hold', reason='Still awaiting review.',
                                      expected_version=case.version), 'bounded-review-' + str(index))
            else:
                case = service.check(scope, 'noop-payment-' + str(index))
        except ServiceError as exc:
            assert exc.code == 'case_capacity_reached'
            assert service.store.docs == before
            break
    else:
        pytest.fail('Unbounded operations')
    assert index >= 12
    assert service.get(scope).payment_status == 'HOLD_PENDING_REVIEW'
    final = service.review(scope, ReviewCommand(action=action, reason='Terminal review.',
                           expected_version=case.version), 'reserved-final')
    assert final.payment_status == ('SIMULATED_PASSED' if action == 'approve' else 'SIMULATED_CANCELLED')
    doc = service.store.read('case-' + scope.case_id)
    assert len(doc['operations']) <= 32 and len(doc['events']) <= 64
    assert len(json.dumps(doc).encode()) <= 256 * 1024
    with pytest.raises(ServiceError, match='case_capacity_reached'):
        service.check(scope, 'past-hard-operation-cap')


def test_event_capacity_reserves_a_terminal_event_without_dropping_legacy_audit():
    service, scope, case = held()
    ck = 'case-' + scope.case_id
    doc = service.store.read(ck)
    doc['events'] = [{**doc['events'][0], 'event_id': 'legacy-event-' + str(i)} for i in range(63)]
    doc['version'] = 63
    service.store.atomic((ck,), lambda docs: {ck: doc})
    before = deepcopy(service.store.docs)
    with pytest.raises(ServiceError, match='case_capacity_reached'):
        service.review(scope, ReviewCommand(action='keep_hold', reason='No more audit capacity.',
                       expected_version=63), 'over-event-reserve')
    assert service.store.docs == before
    final = service.review(scope, ReviewCommand(action='cancel', reason='Resolve held payment.',
                           expected_version=63), 'final-event-slot')
    assert len(final.events) == 64
    assert final.model_dump(mode='json')['events'][:-1] == doc['events']
    with pytest.raises(ServiceError, match='case_capacity_reached'):
        service.review(scope, ReviewCommand(action='dismiss', reason='Over hard audit cap.',
                       expected_version=final.version), 'over-hard-event-cap')


def test_byte_capacity_reserves_maximum_reason_and_evidence_for_terminal_review():
    service, scope, case = held()
    case = investigate_held_case(service, scope)
    evidence = [item for step in case.result.trace if step.tool_result for item in step.tool_result.evidence]
    largest = max(evidence, key=lambda item: len(item.model_dump_json()))
    refs = tuple(Citation.model_validate(largest.model_dump(include=set(Citation.model_fields))) for _ in range(12))
    rng = random.Random(20261004)
    for index in range(40):
        reason = ''.join(chr(rng.randrange(0x10000, 0x10FFFF)) for _ in range(500))
        before = deepcopy(service.store.docs)
        try:
            case = service.review(scope, ReviewCommand(action='keep_hold', reason=reason, evidence_refs=refs,
                                  expected_version=case.version), 'large-review-' + str(index))
        except ServiceError as exc:
            assert exc.code == 'case_capacity_reached'
            assert service.store.docs == before
            break
    else:
        pytest.fail('Unbounded case document')
    final = service.review(scope, ReviewCommand(action='cancel', reason=reason, evidence_refs=refs,
                           expected_version=case.version), 'large-final-review')
    assert final.payment_status == 'SIMULATED_CANCELLED'
    assert final.events[-1].evidence_refs == refs and final.events[-1].reason == reason
    assert len(json.dumps(service.store.read('case-' + scope.case_id)).encode()) <= 256 * 1024


def test_legacy_cookie_and_two_payment_snapshots_survive_api_migration():
    client, service, auth = client_for()
    first = bootstrap(client)
    second = client.post('/api/finshield/cases', json={'template_id': 'normal-invoice'},
                         headers={'Idempotency-Key': 'create-second'}).json()
    cookie = client.cookies.get('fs_session')
    sk = session_key(auth.session(cookie).session_id)
    session = service.store.read(sk)
    session['csrf_hash'] = token_hash('old-open-tab-token')
    service.store.atomic((sk,), lambda docs: {sk: session})
    client.headers['X-CSRF-Token'] = 'old-open-tab-token'
    history = []
    for case in (first, second):
        path = '/api/finshield/cases/' + case['case_id']
        response = client.post(path + '/payment', json={}, headers={'Idempotency-Key': 'old-payment-key'})
        assert response.status_code == 200
        ck = 'case-' + case['case_id']
        doc = service.store.read(ck)
        legacy_response = {**doc, 'operations': {}}
        doc['operations']['payment:old-payment-key']['response'] = legacy_response
        service.store.atomic((ck,), lambda docs: {ck: doc})
        history.append((path, response.json()))
    resumed, _, _ = client_for(service.store)
    resumed.cookies.set('fs_session', cookie)
    resume = resumed.post('/api/finshield/sessions', json={'resume_only': True},
                          headers={'Origin': 'https://testserver'})
    assert resume.status_code == 200 and len(resume.json()['cases']) == 2
    for path, expected in history:
        # Exercise legacy replay before a GET performs the atomic migration.
        headers = {'Origin': 'https://testserver', 'X-CSRF-Token': 'old-open-tab-token',
                   'Idempotency-Key': 'old-payment-key'}
        assert resumed.post(path + '/payment', json={}, headers=headers).json() == expected
        assert resumed.get(path).status_code == 200
        replayed = resumed.post(path + '/payment', json={}, headers=headers)
        assert replayed.status_code == 200 and replayed.json() == expected
    assert service.store.read(sk) == session


@pytest.mark.parametrize('damage', ['overflow', 'truncated', 'trailing', 'base64', 'schema', 'unknown-format'])
def test_invalid_compressed_replay_fails_closed_with_bounded_decode(damage):
    service, scope, case = held()
    ck = 'case-' + scope.case_id
    doc = service.store.read(ck)
    response = deepcopy(doc['operations']['payment:payment-001']['response'])
    if damage == 'overflow':
        data = zlib.compress(b' ' * (256 * 1024 + 1))
    elif damage == 'schema':
        data = zlib.compress(b'{"not_a_case": true}')
    elif damage in ('truncated', 'trailing'):
        data = zlib.compress(json.dumps(case.model_dump(mode='json')).encode())
        data = data[:-1] if damage == 'truncated' else data + b'extra'
    else:
        data = b'not-a-zlib-stream'
    response['data'] = '%%invalid%%' if damage == 'base64' else b64encode(data).decode('ascii')
    if damage == 'unknown-format':
        response['format'] = 'unknown-v2'
    doc['operations']['payment:payment-001']['response'] = response
    service.store.atomic((ck,), lambda docs: {ck: doc})
    before = deepcopy(service.store.docs)
    with pytest.raises(ServiceError, match='storage_unavailable') as caught:
        service.check(scope, 'payment-001')
    assert caught.value.status_code == 503
    assert service.store.docs == before


def test_hard_case_byte_limit_remains_enforced_after_compaction():
    service, scope, _ = held()
    ck = 'case-' + scope.case_id
    doc = service.store.read(ck)
    doc['vip_answer'] = 'x' * (256 * 1024)
    service.store.atomic((ck,), lambda docs: {ck: doc})
    before = deepcopy(service.store.docs)
    with pytest.raises(ServiceError, match='case_capacity_reached'):
        service.get(scope)
    assert service.store.docs == before

"""Opt-in local persistence contract. A skip is not durability evidence."""
import os
from uuid import uuid4

import pytest

from app.finshield.models import ReviewCommand, ServiceError
from app.finshield.service import CaseService
from app.finshield.store import FirestoreStore
from tests.test_finshield_state import NOW, held


@pytest.fixture
def emulator():
    host = os.environ.get('FIRESTORE_EMULATOR_HOST', '')
    if not host:
        pytest.skip('Local Firestore emulator is not configured; durability remains unverified.')
    if host.rsplit(':', 1)[0] not in ('127.0.0.1', 'localhost', '[::1]'):
        pytest.fail('Emulator tests accept loopback only.')
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    client = firestore.Client(project='repsafe-finshield-test', credentials=AnonymousCredentials())
    collection = 'finshield_test_' + uuid4().hex
    return FirestoreStore(client, collection), client, collection


def test_emulator_atomic_review_replay_and_new_client(emulator):
    store, client, collection = emulator
    service, scope, case = held(store)
    command = ReviewCommand(action='approve', reason='Manual emulator verification.', expected_version=case.version)
    first = service.review(scope, command, 'decision-001')
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    replacement = firestore.Client(project='repsafe-finshield-test', credentials=AnonymousCredentials())
    second = CaseService(FirestoreStore(replacement, collection), clock=lambda: NOW)
    assert second.review(scope, command, 'decision-001') == first
    assert second.get(scope).payment_status == 'SIMULATED_PASSED'


def test_emulator_reducer_failure_writes_nothing(emulator):
    store, _, _ = emulator
    key = 'quota-rollback'
    store.atomic((key,), lambda docs: {key: {'used': 1}})
    def fail(docs):
        docs[key]['used'] = 999
        raise ServiceError('deliberate_rollback', 409)
    with pytest.raises(ServiceError, match='deliberate_rollback'):
        store.atomic((key,), fail)
    assert store.read(key) == {'used': 1}


def test_transaction_begin_commit_and_rollback_have_explicit_rpc_bounds():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    from google.cloud.firestore_v1.types import BeginTransactionResponse, CommitResponse, BatchGetDocumentsResponse
    calls = []
    class API:
        def begin_transaction(self, **kwargs):
            calls.append(('begin', kwargs))
            return BeginTransactionResponse(transaction=b'test-transaction')
        def commit(self, **kwargs):
            calls.append(('commit', kwargs))
            return CommitResponse()
        def rollback(self, **kwargs):
            calls.append(('rollback', kwargs))
        def batch_get_documents(self, **kwargs):
            calls.append(('read', kwargs))
            yield BatchGetDocumentsResponse(missing=kwargs['request']['documents'][0])
    client = firestore.Client(project='repsafe-finshield-test', credentials=AnonymousCredentials())
    client._firestore_api_internal = API()
    store = FirestoreStore(client, 'bounded_test')
    assert store.atomic(('quota-test',), lambda docs: {'quota-test': {'used':1}}) == {'quota-test': {'used':1}}
    def fail(docs):
        raise ServiceError('deliberate_rollback', 409)
    with pytest.raises(ServiceError, match='deliberate_rollback'):
        store.atomic((), fail)
    assert [name for name, _ in calls] == ['begin', 'read', 'commit', 'begin', 'rollback']
    for name, kwargs in calls:
        assert kwargs['retry'] is None
        assert 0 < kwargs['timeout'] <= 3

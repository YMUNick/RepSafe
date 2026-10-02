"""Server-side persistence. No in-memory fallback exists in this module."""
import re
import time
from hashlib import sha256
from typing import Callable, Protocol

from .models import JsonDoc, ServiceError


def session_key(session_id: str) -> str:
    return 'session-' + sha256(session_id.encode('utf-8')).hexdigest()


class Store(Protocol):
    def read(self, key: str) -> JsonDoc | None: ...
    def atomic(self, keys: tuple[str, ...], reduce: Callable) -> dict[str, JsonDoc]: ...


class _TransactionBudget:
    def __init__(self):
        self.deadline = time.monotonic() + 9

    def timeout(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ServiceError('storage_unavailable', 503)
        return min(3, remaining)


class _BoundedTransactionClient:
    """Per-transaction adapter; never mutates the shared SDK client.

    The public transactional runner invokes internal begin/commit/rollback RPCs
    without timeout arguments (verified with google-cloud-firestore 2.34).
    This narrow adapter bounds those RPCs while retaining the SDK's transaction
    conflict handling. An SDK upgrade must keep the boundary test passing.
    """
    def __init__(self, client, budget):
        self._wrapped_client, self._budget = client, budget

    def __getattr__(self, name):
        return getattr(self._wrapped_client, name)

    @property
    def _firestore_api(self):
        return _BoundedTransactionRPC(self._wrapped_client._firestore_api, self._budget)


class _BoundedTransactionRPC:
    def __init__(self, api, budget):
        self._api, self._budget = api, budget

    def __getattr__(self, name):
        method = getattr(self._api, name)
        if name not in ('begin_transaction', 'commit', 'rollback'):
            return method
        def bounded(*args, **kwargs):
            kwargs.update(retry=None, timeout=self._budget.timeout())
            return method(*args, **kwargs)
        return bounded


class FirestoreStore:
    """Client or lazy client_factory may be injected by deployment authentication."""
    def __init__(self, client=None, collection='finshield', *, client_factory=None):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', collection):
            raise ValueError('invalid_collection')
        self.client, self.collection, self.client_factory = client, collection, client_factory

    def _client(self):
        if self.client is None:
            if self.client_factory is None:
                raise ServiceError('storage_unavailable', 503)
            self.client = self.client_factory()
        return self.client

    def _ref(self, key):
        if not re.fullmatch(r'(session|case|quota)-[a-zA-Z0-9-]{1,128}', key):
            raise ServiceError('invalid_storage_key', 500)
        return self._client().collection(self.collection).document(key)

    def read(self, key):
        try:
            snap = self._ref(key).get(timeout=3, retry=None)
            return snap.to_dict() if snap.exists else None
        except ServiceError:
            raise
        except Exception:
            raise ServiceError('storage_unavailable', 503) from None

    def atomic(self, keys, reduce):
        try:
            from google.cloud import firestore
            from google.cloud.firestore_v1.transaction import Transaction
            budget = _TransactionBudget()
            refs = {key: self._ref(key) for key in keys}
            @firestore.transactional
            def apply(transaction):
                documents = {}
                for key, ref in refs.items():
                    snap = ref.get(transaction=transaction, timeout=budget.timeout(), retry=None)
                    documents[key] = snap.to_dict() if snap.exists else None
                writes = reduce(documents)
                if not set(writes) <= set(keys):
                    raise ServiceError('invalid_storage_write', 500)
                for key, document in writes.items():
                    transaction.set(refs[key], document)
                return writes
            return apply(Transaction(_BoundedTransactionClient(self._client(), budget), max_attempts=3))
        except ServiceError:
            raise
        except Exception:
            raise ServiceError('storage_unavailable', 503) from None

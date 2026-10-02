import re
import secrets
from datetime import timedelta
from hashlib import sha256
from hmac import compare_digest
from uuid import uuid4

from .models import ReviewerGrant, Scope, ServiceError, Session
from .service import require_session, utcnow
from .store import session_key


def token_hash(token):
    return sha256(token.encode('utf-8')).hexdigest()


class SessionAuth:
    def __init__(self, store, reviewer_hashes, clock=utcnow, session_cap=100):
        self.store, self.clock = store, clock
        self.session_cap = session_cap
        self.reviewer_hashes = {key: value.lower() for key, value in reviewer_hashes.items()
                                if key in ('reviewer-a', 'reviewer-b') and re.fullmatch(r'[a-fA-F0-9]{64}', value)}

    def new_session(self):
        session_id = str(uuid4())
        token, csrf = session_id + '.' + secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        session = Session(session_id=session_id, token_hash=token_hash(token), csrf_hash=token_hash(csrf),
                          expires_at=self.clock() + timedelta(hours=24))
        key = session_key(session_id)
        quota_key = 'quota-session-creation'
        def reduce(docs):
            quota = docs[quota_key] or {'used': 0, 'cap': self.session_cap}
            if self.session_cap <= 0 or quota['used'] >= min(self.session_cap, quota['cap']):
                raise ServiceError('session_capacity_reached', 429)
            return {key: session.model_dump(mode='json'), quota_key: {**quota, 'used': quota['used'] + 1}}
        self.store.atomic((key, quota_key), reduce)
        return token, csrf, session

    def session(self, token):
        if not token or not re.fullmatch(r'[0-9a-f-]{36}\.[A-Za-z0-9_-]{43}', token):
            raise ServiceError('unauthorized', 401)
        session = require_session(self.store.read(session_key(token.split('.')[0])), self.clock())
        if not compare_digest(session.token_hash, token_hash(token)):
            raise ServiceError('unauthorized', 401)
        return session

    def check_csrf(self, token, csrf):
        session = self.session(token)
        if not csrf or not compare_digest(session.csrf_hash, token_hash(csrf)):
            raise ServiceError('csrf_forbidden', 403)
        return session

    def resolve(self, token, case_id):
        session = self.session(token)
        if case_id not in session.case_ids:
            raise ServiceError('case_not_found', 404)
        grant = session.review_grants.get(case_id)
        valid = grant is not None and grant.case_id == case_id and grant.expires_at > self.clock()
        return Scope(session.session_id, case_id, grant.actor_id if valid else 'visitor:' + session.session_id, valid)

    def grant(self, token, case_id, reviewer_id, secret):
        session = self.session(token)
        sk, now = session_key(session.session_id), self.clock()
        digest = token_hash(secret)
        valid_secret = compare_digest(self.reviewer_hashes.get(reviewer_id, '0' * 64), digest)
        def reduce(docs):
            current = require_session(docs[sk], now)
            if not compare_digest(current.token_hash, token_hash(token)):
                raise ServiceError('unauthorized', 401)
            if case_id not in current.case_ids:
                raise ServiceError('case_not_found', 404)
            if current.failed_logins >= 5:
                raise ServiceError('review_login_locked', 429)
            if not valid_secret:
                current = current.model_copy(update={'failed_logins': current.failed_logins + 1})
            else:
                grant = ReviewerGrant(actor_id=reviewer_id, case_id=case_id, expires_at=now + timedelta(minutes=15))
                current = current.model_copy(update={'review_grants': {**current.review_grants, case_id: grant}})
            return {sk: current.model_dump(mode='json')}
        self.store.atomic((sk,), reduce)
        if not valid_secret:
            raise ServiceError('review_forbidden', 403)

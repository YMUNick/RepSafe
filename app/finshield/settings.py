import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from .models import ServiceError


def _bool(name, default='false'):
    return os.environ.get(name, default).strip().lower() in ('true', '1', 'yes', 'on')


@dataclass(frozen=True)
class FinShieldSettings:
    enabled: bool = False
    live_calls_enabled: bool = False
    model_call_cap: int = 0
    budget_id: str = ''
    allowed_origin: str = ''
    allow_loopback_http: bool = False
    model_mode: str = 'offline_fixture'
    firestore_project: str = ''
    firestore_database: str = '(default)'
    firestore_collection: str = 'finshield'
    emulator_host: str = ''
    session_cap: int = 100
    reviewer_a_hash: str = ''
    reviewer_b_hash: str = ''

    @classmethod
    def from_env(cls):
        return cls(enabled=_bool('FINSHIELD_ENABLED'), live_calls_enabled=_bool('FINSHIELD_LIVE_CALLS_ENABLED'),
                   model_call_cap=int(os.environ.get('FINSHIELD_MODEL_CALL_CAP', '0')),
                   budget_id=os.environ.get('FINSHIELD_BUDGET_ID', ''),
                   allowed_origin=os.environ.get('FINSHIELD_ALLOWED_ORIGIN', ''),
                   allow_loopback_http=_bool('FINSHIELD_ALLOW_LOOPBACK_HTTP'),
                   model_mode=os.environ.get('FINSHIELD_MODEL_MODE', 'offline_fixture'),
                   firestore_project=os.environ.get('FINSHIELD_FIRESTORE_PROJECT', ''),
                   firestore_database=os.environ.get('FINSHIELD_FIRESTORE_DATABASE', '(default)'),
                   firestore_collection=os.environ.get('FINSHIELD_FIRESTORE_COLLECTION', 'finshield'),
                   emulator_host=os.environ.get('FIRESTORE_EMULATOR_HOST', ''),
                   session_cap=int(os.environ.get('FINSHIELD_SESSION_CAP', '100')),
                   reviewer_a_hash=os.environ.get('FINSHIELD_REVIEWER_A_HASH', ''),
                   reviewer_b_hash=os.environ.get('FINSHIELD_REVIEWER_B_HASH', ''))

    def validate(self):
        origin = urlsplit(self.allowed_origin)
        if not origin.hostname or origin.path or origin.query or origin.fragment or origin.username or origin.password:
            raise ServiceError('configuration_unavailable', 503)
        loopback = origin.hostname in ('localhost', '127.0.0.1', '::1')
        emulator = self.emulator_host.rsplit(':', 1)[0] in ('localhost', '127.0.0.1', '[::1]')
        if origin.scheme != 'https' and not (origin.scheme == 'http' and loopback and emulator and self.allow_loopback_http):
            raise ServiceError('configuration_unavailable', 503)
        if self.model_mode not in ('offline_fixture', 'gemini') or self.model_call_cap < 0 or self.session_cap < 0:
            raise ServiceError('configuration_unavailable', 503)

    @property
    def reviewer_hashes(self):
        return {'reviewer-a': self.reviewer_a_hash, 'reviewer-b': self.reviewer_b_hash}

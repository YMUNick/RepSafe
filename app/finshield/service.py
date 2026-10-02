import json
import re
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid4, uuid5

from .dataset import load_bundle
from .models import AuditEvent, CaseRecord, Operation, ReviewCommand, RunLease, RunResult, Scope, ServiceError, Session
from .policy import check_payment
from .store import session_key


def utcnow():
    return datetime.now(timezone.utc)


def request_hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def snapshot(case):
    return case.model_copy(update={'operations': {}})


def validate_key(key):
    if not re.fullmatch(r'[A-Za-z0-9-]{8,64}', key):
        raise ServiceError('invalid_idempotency_key', 422)


def require_session(doc, now):
    if doc is None:
        raise ServiceError('unauthorized', 401)
    session = Session.model_validate(doc)
    if session.expires_at <= now:
        raise ServiceError('unauthorized', 401)
    return session


def require_case(doc, session, scope):
    if doc is None or scope.case_id not in session.case_ids:
        raise ServiceError('case_not_found', 404)
    case = CaseRecord.model_validate(doc)
    if case.session_id != session.session_id or scope.session_id != session.session_id:
        raise ServiceError('case_not_found', 404)
    return case


def require_review(session, scope, now):
    grant = session.review_grants.get(scope.case_id)
    if not scope.can_review or grant is None or grant.expires_at <= now or grant.actor_id != scope.actor_id or grant.case_id != scope.case_id:
        raise ServiceError('review_forbidden', 403)


def review_target(status, action):
    if action == 'dismiss':
        return status
    if status != 'HOLD_PENDING_REVIEW':
        raise ServiceError('invalid_transition', 409)
    return {'approve': 'SIMULATED_PASSED', 'cancel': 'SIMULATED_CANCELLED', 'keep_hold': status, 'escalate': status}[action]


class CaseService:
    def __init__(self, store, clock=utcnow):
        self.store, self.clock = store, clock

    def _pack(self, case):
        doc = case.model_dump(mode='json')
        if len(case.operations) > 32 or len(case.events) > 64 or len(json.dumps(doc).encode()) > 256 * 1024:
            raise ServiceError('case_capacity_reached', 409)
        return doc

    def _recover(self, case, now):
        if case.investigation_status == 'RUNNING' and case.lease_until <= now:
            return case.model_copy(update={'investigation_status': 'INCOMPLETE',
                                          'result': RunResult(status='INCOMPLETE', reason_codes=('interrupted',)),
                                          'version': case.version + 1})
        return case

    def create(self, session_id, template_id, key):
        validate_key(key)
        if template_id not in ('risk-fee', 'normal-invoice'):
            raise ServiceError('unknown_template', 422)
        case_id = str(uuid5(NAMESPACE_URL, session_id + ':' + template_id))
        sk, ck = session_key(session_id), 'case-' + case_id
        now = self.clock()
        opkey = 'create:' + key
        digest = request_hash({'route': 'create', 'actor': session_id, 'template_id': template_id, 'case': case_id})
        bundle = load_bundle(template_id, case_id)
        def reduce(docs):
            session = require_session(docs[sk], now)
            previous = session.operations.get(opkey)
            if previous:
                if previous.request_hash != digest:
                    raise ServiceError('idempotency_conflict', 409)
                return {sk: docs[sk], ck: docs[ck]}
            case = CaseRecord.model_validate(docs[ck]) if docs[ck] else CaseRecord(case_id=case_id, session_id=session_id, bundle=bundle)
            operations = {**session.operations, opkey: Operation(request_hash=digest, response=snapshot(case).model_dump(mode='json'))}
            if len(operations) > 32:
                raise ServiceError('case_capacity_reached', 409)
            session = session.model_copy(update={'case_ids': tuple(dict.fromkeys((*session.case_ids, case_id))), 'operations': operations})
            return {sk: session.model_dump(mode='json'), ck: self._pack(case)}
        writes = self.store.atomic((sk, ck), reduce)
        return CaseRecord.model_validate(writes[sk]['operations'][opkey]['response'])

    def _change(self, scope, transform, *, route=None, key=None, body=None, review=False):
        if key is not None:
            validate_key(key)
        now, sk, ck = self.clock(), session_key(scope.session_id), 'case-' + scope.case_id
        opkey = route + ':' + key if key else None
        digest = request_hash({'actor': scope.actor_id, 'case': scope.case_id, 'route': route, 'body': body})
        def reduce(docs):
            session = require_session(docs[sk], now)
            case = require_case(docs[ck], session, scope)
            if review:
                require_review(session, scope, now)
            if opkey and opkey in case.operations:
                if case.operations[opkey].request_hash != digest:
                    raise ServiceError('idempotency_conflict', 409)
                return {ck: docs[ck]}
            case = transform(self._recover(case, now), now)
            if opkey:
                operation = Operation(request_hash=digest, response=snapshot(case).model_dump(mode='json'))
                case = case.model_copy(update={'operations': {**case.operations, opkey: operation}})
            return {ck: self._pack(case)}
        writes = self.store.atomic((sk, ck), reduce)
        case = CaseRecord.model_validate(writes[ck])
        return CaseRecord.model_validate(case.operations[opkey].response) if opkey else snapshot(case)

    def get(self, scope):
        return self._change(scope, lambda case, now: case)

    def recover_expired(self, scope):
        return self.get(scope)

    def _event(self, case, scope, action, reason, after, now, evidence_refs=()):
        rule = case.rule_result
        return AuditEvent(event_id=str(uuid5(NAMESPACE_URL, case.case_id + ':' + str(case.version + 1))),
                          actor_id=scope.actor_id, case_id=case.case_id, transaction_id=case.bundle.current.transaction_id,
                          action=action, reason=reason, policy_id=rule.policy_id if rule else '',
                          policy_version=rule.policy_version if rule else '', dataset_version=case.bundle.dataset_version,
                          at=now, before=case.payment_status, after=after, evidence_refs=evidence_refs)

    def check(self, scope, key):
        def transform(case, now):
            if case.payment_status != 'PENDING_CHECK':
                return case
            result = check_payment(case.bundle)
            event = self._event(case.model_copy(update={'rule_result': result}), scope, 'payment_check',
                                'Synthetic server policy evaluation.', result.payment_status, now)
            return case.model_copy(update={'rule_result': result, 'payment_status': result.payment_status,
                                          'version': case.version + 1, 'events': (*case.events, event)})
        return self._change(scope, transform, route='payment', key=key, body={})

    def review(self, scope, command, key):
        command = ReviewCommand.model_validate(command.model_dump())
        def transform(case, now):
            if case.version != command.expected_version:
                raise ServiceError('version_conflict', 409)
            if command.evidence_refs:
                from .citations import validate_citation
                evidence = tuple(e for step in (case.result.trace if case.result else ()) if step.tool_result for e in step.tool_result.evidence)
                for citation in command.evidence_refs:
                    validate_citation(citation, evidence, scope)
            target = review_target(case.payment_status, command.action)
            event = self._event(case, scope, command.action, command.reason, target, now, command.evidence_refs)
            return case.model_copy(update={'payment_status': target, 'version': case.version + 1, 'events': (*case.events, event)})
        return self._change(scope, transform, route='review', key=key, body=command.model_dump(mode='json'), review=True)

    def claim_run(self, scope, key):
        run_id = str(uuid4())
        def transform(case, now):
            if case.payment_status == 'PENDING_CHECK':
                raise ServiceError('payment_check_required', 409)
            if case.investigation_status != 'NOT_STARTED':
                raise ServiceError('investigation_already_started', 409)
            return case.model_copy(update={'run_id': run_id, 'lease_until': now + timedelta(seconds=60),
                                          'investigation_status': 'RUNNING', 'version': case.version + 1})
        case = self._change(scope, transform, route='investigation', key=key, body={})
        return RunLease(case_id=case.case_id, run_id=case.run_id, lease_until=case.lease_until, acquired=case.run_id == run_id, current=case)

    def finish_run(self, scope, run_id, result):
        result = RunResult.model_validate(result.model_dump())
        def transform(case, now):
            if case.run_id != run_id or case.investigation_status != 'RUNNING' or case.lease_until <= now:
                raise ServiceError('stale_run', 409)
            return case.model_copy(update={'result': result, 'investigation_status': result.status, 'version': case.version + 1})
        return self._change(scope, transform)

    def reserve_model_call(self, scope, budget_id, cap):
        if cap <= 0 or not re.fullmatch(r'[A-Za-z0-9-]{1,64}', budget_id):
            raise ServiceError('model_budget_exhausted', 409)
        sk, ck, qk = session_key(scope.session_id), 'case-' + scope.case_id, 'quota-' + budget_id
        now = self.clock()
        def reduce(docs):
            session = require_session(docs[sk], now)
            case = require_case(docs[ck], session, scope)
            quota = docs[qk] or {'used': 0, 'cap': cap}
            if quota['cap'] != cap or quota['used'] >= min(cap, quota['cap']) or case.model_calls >= 6:
                raise ServiceError('model_budget_exhausted', 409)
            return {qk: {**quota, 'used': quota['used'] + 1}, ck: self._pack(case.model_copy(update={'model_calls': case.model_calls + 1}))}
        self.store.atomic((sk, ck, qk), reduce)

    def claim_vip(self, scope, key):
        validate_key(key)
        sk, ck, now = session_key(scope.session_id), 'case-' + scope.case_id, self.clock()
        marker = str(uuid4())
        def reduce(docs):
            session = require_session(docs[sk], now)
            case = require_case(docs[ck], session, scope)
            if case.vip_used:
                return {ck: docs[ck]}
            if case.investigation_status not in ('READY', 'INCOMPLETE'):
                raise ServiceError('investigation_required', 409)
            operation = Operation(request_hash=request_hash({'case': scope.case_id, 'actor': scope.actor_id, 'route': 'vip'}), response={'claim': marker})
            updated = case.model_copy(update={'vip_used': True, 'vip_answer': 'Unavailable. Manual review is required.',
                                             'operations': {**case.operations, 'vip:' + key: operation}})
            return {ck: self._pack(updated)}
        case = CaseRecord.model_validate(self.store.atomic((sk, ck), reduce)[ck])
        operation = case.operations.get('vip:' + key)
        return operation is not None and operation.response.get('claim') == marker

    def save_vip(self, scope, answer):
        def transform(case, now):
            if not case.vip_used:
                raise ServiceError('vip_not_claimed', 409)
            return case.model_copy(update={'vip_answer': answer[:1000]})
        return self._change(scope, transform)

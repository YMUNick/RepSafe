from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import replace
from typing import Callable

from pydantic import ValidationError

from app.gemini import JudgeError, generate_json
from .citations import validate_citation, validate_report
from .models import Action, Bundle, Citation, Claim, Evidence, ModelReply, Report, RunResult, Scope, ServiceError, ToolQuery, ToolResult, TraceStep
from .policy import check_payment
from .prompts import SYSTEM, VIP_SYSTEM
from .tools import dispatch

ModelStep = Callable[[tuple[ToolResult, ...], float], ModelReply]
ModelStepFactory = Callable[[Bundle], ModelStep]
VipAnswerer = Callable[[Scope, Report, tuple[Evidence, ...], Callable[[], None]], str]
_workers = ThreadPoolExecutor(max_workers=8, thread_name_prefix='finshield-read')
ENTRIES = (ToolQuery(tool='transactions', record_id='current'), ToolQuery(tool='policy_case_history', record_id='DEMO-PAYMENT'))


def _bounded(function, seconds, *args):
    future = _workers.submit(function, *args)
    try:
        return future.result(timeout=max(0, seconds))
    except FutureTimeout:
        future.cancel()
        raise ServiceError('deadline_exceeded', 409) from None


def _json(value):
    encoded = json.dumps(value, separators=(',', ':'), ensure_ascii=False)
    if len(encoded.encode('utf-8')) > 32768:
        raise ServiceError('model_input_limit', 422)
    return encoded


def _citation(evidence):
    return Citation.model_validate(evidence.model_dump(include=set(Citation.model_fields)))


def run_investigation(scope, bundle, model_step, before_call, clock=time.monotonic):
    start = clock()
    observations, trace, returned = [], [], []
    def incomplete(code, report=None):
        return RunResult(status='INCOMPLETE', report=report, reason_codes=(code,), trace=tuple(trace), elapsed_ms=max(0, int((clock() - start) * 1000)))
    try:
        for index in range(1, 6):
            remaining = 45 - (clock() - start)
            if remaining <= 0:
                return incomplete('deadline_exceeded')
            _json([o.model_dump(mode='json') for o in observations])
            before_call()
            remaining = 45 - (clock() - start)
            if remaining <= 0:
                return incomplete('deadline_exceeded')
            call_start = clock()
            reply = _bounded(model_step, min(9, remaining), tuple(observations), min(9, remaining))
            reply = ModelReply.model_validate(reply.model_dump() if isinstance(reply, ModelReply) else reply)
            if clock() - start >= 45 or clock() - call_start > 9:
                return incomplete('deadline_exceeded')
            if len(reply.model_dump_json().encode()) > 32768:
                return incomplete('model_output_limit')
            action = reply.action
            allowed = set(ENTRIES)
            for observation in observations:
                allowed.update(observation.next_queries)
            for citation in action.based_on:
                validate_citation(citation, tuple(returned), scope)
            tool_result = None
            if action.kind == 'call_tool':
                if len(observations) >= 4:
                    return incomplete('tool_call_limit')
                if action.query not in allowed or any(o.query == action.query for o in observations):
                    return incomplete('query_forbidden')
                if observations:
                    if not action.based_on:
                        return incomplete('dependency_required')
                    if action.query not in ENTRIES:
                        revealing = [o for o in observations if action.query in o.next_queries]
                        if not any(c in tuple(_citation(e) for e in o.evidence) for o in revealing for c in action.based_on):
                            return incomplete('dependency_required')
                tool_start = clock()
                tool_result = _bounded(dispatch, min(1, 45 - (clock() - start)), scope, bundle, action.query, index)
                if clock() - tool_start > 1 or clock() - start >= 45:
                    return incomplete('tool_deadline_exceeded')
                observations.append(tool_result)
                returned.extend(tool_result.evidence)
            if action.kind == 'finish':
                validate_report(action.report, tuple(returned), scope)
            trace.append(TraceStep(index=index, action=action, tool_result=tool_result, model=reply.model, mode=reply.mode,
                                   elapsed_ms=max(0, int((clock() - call_start) * 1000)), input_tokens=reply.input_tokens,
                                   output_tokens=reply.output_tokens, thinking_tokens=reply.thinking_tokens))
            if action.kind == 'finish':
                report = validate_report(action.report, tuple(returned), scope)
                missing = list(report.missing_information)
                missing.extend(item for observation in observations for item in observation.missing_information)
                kinds = {o.query.tool for o in observations if o.evidence}
                if kinds != {'transactions', 'profile_kyc', 'known_relationships', 'policy_case_history'}:
                    missing.append('Required transaction, profile, relationship or policy evidence has not been retrieved.')
                if not report.policy_basis or not any(c.fact_key == 'policy' for c in report.policy_basis):
                    missing.append('A cited demo policy basis is required.')
                facts = {c.fact_key for c in report.findings}
                if not {'history_count', 'history_total_minor'} <= facts:
                    missing.append('Exact history count and total findings are required.')
                if bundle.current.invoice_verified and not {'profile', 'relationship'} <= {c.fact_key for c in report.counter_evidence}:
                    missing.append('Verified invoice and shared-terminal counter-evidence are required.')
                missing = tuple(dict.fromkeys(missing))[:8]
                report = report.model_copy(update={'missing_information': missing})
                if missing:
                    return incomplete('missing_required_context', report)
                return RunResult(status='READY', report=report, trace=tuple(trace), elapsed_ms=max(0, int((clock() - start) * 1000)))
        return incomplete('model_call_limit')
    except (ServiceError, JudgeError) as exc:
        return incomplete(exc.code)
    except (TimeoutError, FutureTimeout):
        return incomplete('deadline_exceeded')
    except (ValidationError, ValueError, TypeError):
        return incomplete('invalid_model_output')
    except Exception:
        # Never expose source text or model output in an error or service log.
        return incomplete('investigation_unavailable')


def make_model_step(settings, bundle):
    current_source = next((s for s in bundle.sources if s.record_id == 'current' and s.at <= bundle.as_of and s.recorded_at <= bundle.as_of), None)
    initial = {'label': 'Synthetic data; simulated payment', 'case_id': bundle.case_id,
               'current': bundle.current.model_dump(mode='json'),
               'conversation': current_source.fields.get('conversation') if current_source else None,
               'rule_result': check_payment(bundle).model_dump(mode='json'),
               'entry_queries': [q.model_dump() for q in ENTRIES]}
    def step(observations, seconds):
        contents = _json({'initial': initial, 'observations': [o.model_dump(mode='json') for o in observations]})
        usage = {}
        bounded = replace(settings, gemini_max_retries=0, gemini_timeout_s=min(9, seconds))
        action = generate_json(bounded, contents, SYSTEM, Action.model_json_schema(), 'finshield_investigation',
                               max_output_tokens=2048, usage_sink=usage.update)
        return ModelReply(action=Action.model_validate(action), model=settings.gemini_model, mode='gemini', **usage)
    return step


def make_offline_step(bundle):
    """Deterministic demonstration, explicitly NOT evidence of real agentic AI."""
    def step(observations, seconds):
        if not observations:
            action = Action(kind='call_tool', query=ENTRIES[0])
        elif len(observations) < 4 and observations[-1].evidence and not observations[-1].missing_information:
            target = ('profile_kyc', 'known_relationships', 'policy_case_history')[len(observations) - 1]
            query = next((q for q in observations[-1].next_queries if q.tool == target), None)
            if query is not None:
                action = Action(kind='call_tool', query=query, based_on=(_citation(observations[-1].evidence[0]),))
            else:
                action = _offline_finish(observations)
        else:
            action = _offline_finish(observations)
        return ModelReply(action=action, model='deterministic-demo-v1', mode='offline_fixture')
    return step


def _offline_finish(observations):
    evidence = {e.fact_key: e for o in observations for e in o.evidence}
    def claim(key):
        e = evidence[key]
        label = {'history_count': 'Unique settled history count', 'history_total_minor': 'Settled history total (SGD minor units)'}.get(key, key.capitalize())
        return Claim(text=(label + ': ' + e.quote)[:400], fact_key=key, fact_value=e.fact_value, citations=(_citation(e),))
    report = Report(findings=tuple(claim(k) for k in ('history_count', 'history_total_minor', 'amount_minor') if k in evidence),
                    counter_evidence=tuple(claim(k) for k in ('profile', 'relationship') if k in evidence),
                    policy_basis=tuple(claim(k) for k in ('policy',) if k in evidence),
                    missing_information=tuple(item for o in observations for item in o.missing_information)[:8],
                    suggested_next_steps=('Review the cited evidence', 'Use the separate review form'))
    return Action(kind='finish', report=report)


def answer_vip(scope, report, evidence, settings, before_call):
    validate_report(report, evidence, scope)
    contents = _json({'question': 'Does VIP status allow this payment to be approved?', 'report': report.model_dump(mode='json'),
                      'policy_evidence': [e.model_dump(mode='json') for e in evidence if e.fact_key == 'policy']})
    if not any(e.fact_key == 'policy' for e in evidence):
        raise ServiceError('vip_unavailable', 409)
    before_call()
    result = generate_json(replace(settings, gemini_timeout_s=9, gemini_max_retries=0), contents, VIP_SYSTEM,
                           Report.model_json_schema(), 'finshield_vip', max_output_tokens=2048)
    answer = validate_report(Report.model_validate(result), evidence, scope)
    if len(answer.policy_basis) != 1 or answer.policy_basis[0].fact_key != 'policy':
        raise ServiceError('vip_unavailable', 409)
    return answer.policy_basis[0].text


def answer_offline_vip(scope, report, evidence, before_call):
    validate_report(report, evidence, scope)
    if not any(e.fact_key == 'policy' for e in evidence):
        raise ServiceError('vip_unavailable', 409)
    return 'Offline fixture: No. VIP status is not an exception. Only an authorized reviewer can approve or cancel a held simulated payment.'

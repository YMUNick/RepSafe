import json

from .models import DemoPolicy, Evidence, ServiceError, ToolQuery, ToolResult
from .dataset import validate_bundle
from .policy import calculate_metrics


def canonical(value):
    return json.dumps(value) if type(value) is bool else str(value)


def dispatch(scope, bundle, query, call_index):
    if scope.case_id != bundle.case_id:
        raise ServiceError('case_not_found', 404)
    query = ToolQuery.model_validate(query.model_dump())
    prefix = 'risk' if bundle.template_id == 'risk-fee' else 'normal'
    allowed = {
        'transactions': {'current', 'recent_20m'},
        'profile_kyc': {bundle.case_id + ':' + prefix + '-profile'},
        'known_relationships': {bundle.case_id + ':' + prefix + '-rel'},
        'policy_case_history': {'DEMO-PAYMENT', *bundle.allowed_precedent_ids},
    }
    if query.record_id not in allowed[query.tool]:
        raise ServiceError('query_forbidden', 403)
    if query.tool == 'policy_case_history':
        try:
            if bundle.policy is None:
                raise ValueError('missing_policy')
            policy = DemoPolicy.model_validate(bundle.policy.model_dump())
            if policy.effective_at > bundle.as_of:
                raise ValueError('future_policy')
        except ValueError:
            return ToolResult(query=query, evidence=(), missing_information=('The required policy is missing, unsupported or not yet effective.',))
    sources = [s for s in bundle.sources if s.record_id == query.record_id and s.case_id == scope.case_id
               and s.dataset_version == bundle.dataset_version and s.policy_version == '1'
               and s.at <= bundle.as_of and s.recorded_at <= bundle.as_of]
    evidence, next_queries, missing = [], [], []
    for source in sources:
        for field, value in source.fields.items():
            evidence.append(Evidence(case_id=source.case_id, source_id=source.source_id, record_id=source.record_id,
                                     field=field, quote=canonical(value), dataset_version=source.dataset_version,
                                     policy_version=source.policy_version, call_index=call_index,
                                     fact_key=field, fact_value=value))
        next_queries.extend(q for q in source.next_queries if q.record_id in allowed[q.tool])
    if query.tool == 'transactions' and (sources or query.record_id == 'recent_20m'):
        try:
            validate_bundle(bundle)
            metrics = calculate_metrics(bundle)
            for field, value in [('history_count', metrics.count), ('history_total_minor', metrics.total_minor)]:
                evidence.append(Evidence(case_id=bundle.case_id, source_id=bundle.case_id + ':derived:recent_20m',
                                         record_id='recent_20m', field=field, quote=canonical(value), dataset_version=bundle.dataset_version,
                                         policy_version=bundle.policy.policy_version, call_index=call_index,
                                         fact_key=field, fact_value=value, derived_from=metrics.transaction_ids))
        except ValueError:
            missing.append('Complete payment history and policy are required.')
    if not sources and query.record_id != 'recent_20m':
        missing.append('Required source is unavailable: ' + query.tool + '/' + query.record_id)
    result = ToolResult(query=query, evidence=tuple(evidence), next_queries=tuple(dict.fromkeys(next_queries)), missing_information=tuple(missing))
    if len(evidence) > 20 or len(result.model_dump_json().encode()) > 8192:
        raise ServiceError('tool_output_limit', 422)
    return result

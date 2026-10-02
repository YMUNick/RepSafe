from datetime import timedelta

from .dataset import validate_bundle
from .models import Bundle, Metrics, RuleResult


def calculate_metrics(bundle: Bundle) -> Metrics:
    unique = {}
    for row in bundle.history:
        if row.transaction_id in unique and unique[row.transaction_id] != row:
            raise ValueError('conflicting_transaction')
        unique[row.transaction_id] = row
    if bundle.policy is None:
        raise ValueError('missing_policy')
    start = bundle.as_of - timedelta(minutes=bundle.policy.window_minutes)
    rows = [r for r in unique.values() if r.transaction_id != bundle.current.transaction_id
            and r.recipient_account_id == bundle.current.recipient_account_id and r.status == 'SETTLED'
            and start <= r.at < bundle.as_of and r.recorded_at <= bundle.as_of]
    return Metrics(transaction_ids=tuple(sorted(r.transaction_id for r in rows)), count=len(rows),
                   total_minor=sum(r.amount_minor for r in rows), window_start=start, window_end=bundle.as_of)


def check_payment(bundle: Bundle) -> RuleResult:
    try:
        validate_bundle(bundle)
        metrics = calculate_metrics(bundle)
    except ValueError:
        return RuleResult(payment_status='CHECK_FAILED', evaluated_rule_ids=(), matched_rule_ids=(), metrics=None,
                          reason_codes=('invalid_payment_data',), policy_id='', policy_version='', dataset_version=bundle.dataset_version)
    p, current = bundle.policy, bundle.current
    matches = []
    if current.purpose == 'verification_fee' and current.amount_minor >= p.fee_min_minor and not current.invoice_verified:
        matches.append('H1')
    if metrics.count >= p.history_min_count and metrics.total_minor >= p.history_min_minor and not current.invoice_verified:
        matches.append('H2')
    return RuleResult(payment_status='HOLD_PENDING_REVIEW' if matches else 'SIMULATED_PASSED',
                      evaluated_rule_ids=('H1', 'H2'), matched_rule_ids=tuple(matches), metrics=metrics,
                      reason_codes=(), policy_id=p.policy_id, policy_version=p.policy_version, dataset_version=bundle.dataset_version)

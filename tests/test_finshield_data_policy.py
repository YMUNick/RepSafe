from datetime import timedelta

import pytest

from app.finshield.dataset import load_bundle
from app.finshield.policy import check_payment


@pytest.mark.parametrize('name,expected', [('risk-fee', 'HOLD_PENDING_REVIEW'), ('normal-invoice', 'SIMULATED_PASSED')])
def test_policy_and_time_boundary(name, expected):
    b = load_bundle(name, 'case-a')
    future = b.history[0].model_copy(update={'transaction_id': 'case-a:future', 'at': b.as_of + timedelta(seconds=1)})
    r = check_payment(b.model_copy(update={'history': b.history + (b.history[0], future)}))
    assert r.payment_status == expected
    assert (r.metrics.count, r.metrics.total_minor) == (3, 270000)
    assert len(set(r.metrics.transaction_ids)) == 3
    assert b.current.transaction_id not in r.metrics.transaction_ids
    assert r.evaluated_rule_ids == ('H1', 'H2')


@pytest.mark.parametrize('change', [{'policy': None}, {'history_complete': False}])
def test_required_inputs_fail_closed(change):
    assert check_payment(load_bundle('normal-invoice', 'case-a').model_copy(update=change)).payment_status == 'CHECK_FAILED'


def test_conflicting_duplicate_is_not_silently_deduplicated():
    b = load_bundle('risk-fee', 'case-a')
    row = b.history[0].model_copy(update={'amount_minor': 1})
    assert check_payment(b.model_copy(update={'history': b.history + (row,)})).payment_status == 'CHECK_FAILED'


@pytest.mark.parametrize('amount', [True, 5.0, 0, -1])
def test_invalid_amount_fails_closed(amount):
    b = load_bundle('risk-fee', 'case-a')
    assert check_payment(b.model_copy(update={'current': b.current.model_copy(update={'amount_minor': amount})})).payment_status == 'CHECK_FAILED'


def test_recorded_at_and_window_boundaries():
    b = load_bundle('risk-fee', 'case-a')
    rows = tuple(r.model_copy(update={'recorded_at': b.as_of + timedelta(seconds=1)}) for r in b.history)
    assert check_payment(b.model_copy(update={'history': rows})).metrics.count == 0
    row = b.history[0].model_copy(update={'at': b.as_of - timedelta(minutes=20)})
    assert check_payment(b.model_copy(update={'history': (row,)})).metrics.count == 1


def test_instances_and_sources_are_isolated():
    a, b = (load_bundle('risk-fee', cid) for cid in ['case-a', 'case-b'])
    assert a.current.transaction_id.startswith('case-a:')
    assert not {s.source_id for s in a.sources} & {s.source_id for s in b.sources}


def test_policy_quote_has_actual_thresholds_and_window():
    b = load_bundle('risk-fee', 'case-a')
    small = b.model_copy(update={'current':b.current.model_copy(update={'amount_minor':1}), 'history':()})
    assert check_payment(small).payment_status == 'SIMULATED_PASSED'
    text = next(s.fields['policy'] for s in b.sources if s.record_id == 'DEMO-PAYMENT')
    assert '50000 SGD minor units' in text and '200000 SGD minor units' in text
    assert '3 unique settled' in text and '20-minute' in text
    assert 'without a verified invoice' in text


@pytest.mark.parametrize('template', ['risk-fee', 'normal-invoice'])
def test_relationship_record_has_attributable_scoped_endpoints(template):
    b = load_bundle(template, 'case-a')
    source = next(s for s in b.sources if 'relationship' in s.fields)
    assert source.fields['payer_account_id'] == b.current.payer_account_id
    assert source.fields['recipient_account_id'] == b.current.recipient_account_id
    assert source.fields['device_id'].startswith(b.case_id + ':')
    assert source.fields['source_system'] == 'Synthetic platform device-link log'
    assert source.at < b.as_of and source.recorded_at <= b.as_of

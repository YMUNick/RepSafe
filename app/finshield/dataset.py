import json
from pathlib import Path

from .models import Bundle, DemoPolicy, SourceRecord, ToolQuery


def load_bundle(template_id: str, case_id: str) -> Bundle:
    data = json.loads((Path(__file__).parent / 'fixtures/demo-v1.json').read_text(encoding='utf-8'))
    if template_id not in ('risk-fee', 'normal-invoice'):
        raise ValueError('unknown_template')
    raw = data['templates'][template_id]
    policy = DemoPolicy.model_validate(data['policy'])
    prefix = raw['prefix']
    ids = {key: case_id + ':' + raw[key] for key in ('customer_id', 'payer_account_id', 'recipient_account_id')}
    def row(value):
        return {**value, **ids, 'case_id': case_id, 'transaction_id': case_id + ':' + value['transaction_id']}
    profile = case_id + ':' + prefix + '-profile'
    relation = case_id + ':' + prefix + '-rel'
    precedent = case_id + ':' + prefix + '-precedent'
    def source(record_id, fields, queries=(), *, at=None, recorded_at=None):
        return SourceRecord(case_id=case_id, source_id=case_id + ':source:' + record_id,
                            record_id=record_id, dataset_version=data['dataset_version'], policy_version='1',
                            fields=fields, at=at or data['as_of'], recorded_at=recorded_at or data['as_of'], next_queries=queries)
    policy_text = (f'Demo policy {policy.policy_version}. H1: verification_fee at least {policy.fee_min_minor} SGD minor units. '
                   f'H2: at least {policy.history_min_count} unique settled payments to the same recipient totaling at least {policy.history_min_minor} SGD minor units '
                   f'in the {policy.window_minutes}-minute window [as_of-{policy.window_minutes}m, as_of), excluding current, both timestamps no later than as_of. '
                   'Either rule holds only without a verified invoice. VIP is no exception. Authorized review alone may approve/cancel a hold.')
    relationship = raw['relationship_record']
    sources = (
        source('current', {'conversation': raw['conversation'], 'amount_minor': raw['current']['amount_minor'],
                          'invoice_verified': raw['current']['invoice_verified']},
               (ToolQuery(tool='profile_kyc', record_id=profile), ToolQuery(tool='transactions', record_id='recent_20m'))),
        source(profile, {'profile': raw['profile']}, (ToolQuery(tool='known_relationships', record_id=relation),)),
        source(relation, {'relationship': raw['relationship'], 'payer_account_id':ids['payer_account_id'],
                          'recipient_account_id':ids['recipient_account_id'], 'device_id':case_id + ':' + relationship['device_id'],
                          'source_system':relationship['source_system']},
               (ToolQuery(tool='policy_case_history', record_id='DEMO-PAYMENT'),), at=relationship['at'], recorded_at=relationship['recorded_at']),
        source('DEMO-PAYMENT', {'policy': policy_text},
               (ToolQuery(tool='policy_case_history', record_id=precedent),)),
        source(precedent, {'precedent': raw['precedent']}),
    )
    return Bundle(case_id=case_id, template_id=template_id, dataset_version=data['dataset_version'],
                  conversation_id=case_id + ':' + prefix + '-conv', as_of=data['as_of'], current=row(raw['current']),
                  history=tuple(row(value) for value in raw['history']), history_complete=True,
                  policy=policy, sources=sources, allowed_precedent_ids=(precedent,))


def validate_bundle(bundle: Bundle) -> None:
    if any(type(row.amount_minor) is not int or row.amount_minor <= 0 for row in (bundle.current, *bundle.history)):
        raise ValueError('invalid_payment_data')
    b = Bundle.model_validate(bundle.model_dump(mode='json'))
    if b.dataset_version != 'fs-demo-v1' or not b.history_complete or b.policy is None:
        raise ValueError('invalid_payment_data')
    if b.policy.effective_at > b.as_of or b.current.at > b.as_of or b.current.recorded_at > b.as_of:
        raise ValueError('invalid_payment_data')
    for row in (b.current, *b.history):
        if row.case_id != b.case_id or not row.transaction_id.startswith(b.case_id + ':'):
            raise ValueError('invalid_payment_data')
    if any(s.case_id != b.case_id or s.dataset_version != b.dataset_version or s.policy_version != b.policy.policy_version for s in b.sources):
        raise ValueError('invalid_payment_data')

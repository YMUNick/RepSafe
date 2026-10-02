from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

JsonDoc = dict[str, Any]
Fact = StrictStr | StrictInt | StrictBool
PaymentStatus = Literal['PENDING_CHECK', 'HOLD_PENDING_REVIEW', 'SIMULATED_PASSED', 'CHECK_FAILED', 'SIMULATED_CANCELLED']
InvestigationStatus = Literal['NOT_STARTED', 'RUNNING', 'READY', 'INCOMPLETE']


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    @field_validator('*')
    @classmethod
    def aware_times(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('timezone_required')
            return value.astimezone(timezone.utc)
        return value


@dataclass(frozen=True)
class Scope:
    session_id: str
    case_id: str
    actor_id: str
    can_review: bool


class ServiceError(Exception):
    def __init__(self, code: str, status_code: int = 409):
        super().__init__(code)
        self.code, self.status_code = code, status_code


class LedgerRow(Model):
    case_id: str
    transaction_id: str
    customer_id: str
    payer_account_id: str
    recipient_account_id: str
    amount_minor: Annotated[StrictInt, Field(gt=0)]
    currency: Literal['SGD']
    at: datetime
    recorded_at: datetime


class Payment(LedgerRow):
    purpose: Literal['verification_fee', 'service_fee']
    invoice_verified: StrictBool


class HistoryRow(LedgerRow):
    status: Literal['SETTLED']


class ToolQuery(Model):
    tool: Literal['transactions', 'profile_kyc', 'known_relationships', 'policy_case_history']
    record_id: str = Field(min_length=1, max_length=200)


class SourceRecord(Model):
    case_id: str
    source_id: str
    record_id: str
    dataset_version: str
    policy_version: str
    fields: dict[str, Fact]
    at: datetime
    recorded_at: datetime
    next_queries: tuple[ToolQuery, ...] = ()

    @field_validator('fields')
    @classmethod
    def plain_text(cls, value):
        if any(isinstance(v, str) and ('<' in v or '>' in v) for v in value.values()):
            raise ValueError('html_not_allowed')
        return value


class DemoPolicy(Model):
    policy_id: Literal['DEMO-PAYMENT']
    policy_version: Literal['1']
    effective_at: datetime
    fee_min_minor: Literal[50000]
    window_minutes: Literal[20]
    history_min_count: Literal[3]
    history_min_minor: Literal[200000]


class Bundle(Model):
    case_id: str
    template_id: str
    dataset_version: str
    conversation_id: str
    as_of: datetime
    current: Payment
    history: tuple[HistoryRow, ...]
    history_complete: StrictBool
    policy: DemoPolicy | None
    sources: tuple[SourceRecord, ...]
    allowed_precedent_ids: tuple[str, ...]


class Metrics(Model):
    transaction_ids: tuple[str, ...]
    count: int
    total_minor: int
    window_start: datetime
    window_end: datetime


class RuleResult(Model):
    payment_status: PaymentStatus
    evaluated_rule_ids: tuple[str, ...]
    matched_rule_ids: tuple[str, ...]
    metrics: Metrics | None
    reason_codes: tuple[str, ...]
    policy_id: str
    policy_version: str
    dataset_version: str


class Citation(Model):
    case_id: str
    source_id: str
    record_id: str
    field: str
    quote: str
    dataset_version: str
    policy_version: str
    call_index: int


class Evidence(Citation):
    fact_key: str
    fact_value: Fact
    derived_from: tuple[str, ...] = ()


class ToolResult(Model):
    query: ToolQuery
    evidence: tuple[Evidence, ...]
    next_queries: tuple[ToolQuery, ...] = ()
    missing_information: tuple[str, ...] = ()


class Claim(Model):
    text: str = Field(min_length=1, max_length=400)
    fact_key: str
    fact_value: Fact
    citations: tuple[Citation, ...] = Field(min_length=1, max_length=3)


class Report(Model):
    findings: tuple[Claim, ...] = Field(max_length=4)
    counter_evidence: tuple[Claim, ...] = Field(max_length=4)
    policy_basis: tuple[Claim, ...] = Field(max_length=4)
    missing_information: tuple[Annotated[str, Field(max_length=400)], ...] = Field(max_length=8)
    suggested_next_steps: tuple[Literal['Review the cited evidence', 'Request the missing records', 'Use the separate review form'], ...] = Field(max_length=3)


class Action(Model):
    kind: Literal['call_tool', 'finish']
    query: ToolQuery | None = None
    based_on: tuple[Citation, ...] = Field(default=(), max_length=4)
    report: Report | None = None

    @model_validator(mode='after')
    def shape(self):
        if (self.kind == 'call_tool' and (self.query is None or self.report is not None)) or (self.kind == 'finish' and (self.report is None or self.query is not None)):
            raise ValueError('invalid_action')
        return self


class ModelReply(Model):
    action: Action
    model: str
    mode: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None


class TraceStep(Model):
    index: int
    action: Action
    tool_result: ToolResult | None = None
    model: str
    mode: str
    elapsed_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    thinking_tokens: int | None = None


class RunResult(Model):
    status: Literal['READY', 'INCOMPLETE']
    report: Report | None = None
    reason_codes: tuple[str, ...] = ()
    trace: tuple[TraceStep, ...] = ()
    elapsed_ms: int = 0


class ReviewCommand(Model):
    action: Literal['approve', 'cancel', 'keep_hold', 'escalate', 'dismiss']
    reason: str = Field(min_length=1, max_length=500)
    expected_version: Annotated[StrictInt, Field(ge=0)]
    evidence_refs: tuple[Citation, ...] = Field(default=(), max_length=12)

    @field_validator('reason', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class AuditEvent(Model):
    event_id: str
    actor_id: str
    case_id: str
    transaction_id: str
    action: str
    reason: str
    policy_id: str
    policy_version: str
    dataset_version: str
    at: datetime
    before: PaymentStatus
    after: PaymentStatus
    evidence_refs: tuple[Citation, ...] = ()


class Operation(Model):
    request_hash: str
    response: JsonDoc


class CaseRecord(Model):
    case_id: str
    session_id: str
    bundle: Bundle
    version: int = 0
    payment_status: PaymentStatus = 'PENDING_CHECK'
    investigation_status: InvestigationStatus = 'NOT_STARTED'
    rule_result: RuleResult | None = None
    result: RunResult | None = None
    events: tuple[AuditEvent, ...] = ()
    operations: dict[str, Operation] = Field(default_factory=dict)
    run_id: str | None = None
    lease_until: datetime | None = None
    vip_used: bool = False
    vip_answer: str | None = None
    model_calls: int = 0


class ReviewerGrant(Model):
    actor_id: str
    case_id: str
    expires_at: datetime


class Session(Model):
    session_id: str
    token_hash: str
    csrf_hash: str
    expires_at: datetime
    case_ids: tuple[str, ...] = ()
    review_grants: dict[str, ReviewerGrant] = Field(default_factory=dict)
    failed_logins: int = 0
    operations: dict[str, Operation] = Field(default_factory=dict)


class RunLease(Model):
    case_id: str
    run_id: str
    lease_until: datetime
    acquired: bool
    current: CaseRecord

import pytest

from app.finshield.citations import validate_citation, validate_report
from app.finshield.dataset import load_bundle
from app.finshield.models import Citation, Claim, Report, Scope, ServiceError, ToolQuery
from app.finshield.tools import dispatch


def sample():
    b = load_bundle('risk-fee', 'case-a')
    scope = Scope('s', b.case_id, 'visitor', False)
    result = dispatch(scope, b, ToolQuery(tool='transactions', record_id='current'), 1)
    evidence = result.evidence[0]
    citation = Citation.model_validate(evidence.model_dump(include=set(Citation.model_fields)))
    return scope, result.evidence, citation


@pytest.mark.parametrize('field,value', [('case_id','case-b'), ('source_id','invented'), ('record_id','wrong'), ('dataset_version','v2'), ('policy_version','2'), ('quote','Unrelated assertion'), ('call_index',7)])
def test_citation_must_have_been_returned(field, value):
    scope, evidence, citation = sample()
    assert validate_citation(citation, evidence, scope) == evidence[0]
    with pytest.raises(ServiceError, match='invalid_citation'):
        validate_citation(citation.model_copy(update={field: value}), evidence, scope)
    with pytest.raises(ServiceError):
        validate_citation(citation, (), scope)


def test_fact_mismatch_rejected_even_with_valid_citation():
    scope, evidence, citation = sample()
    report = Report(findings=(Claim(text='Unrelated claim', fact_key=evidence[0].fact_key, fact_value='false assertion', citations=(citation,)),), counter_evidence=(), policy_basis=(), missing_information=(), suggested_next_steps=())
    with pytest.raises(ServiceError, match='invalid_fact'):
        validate_report(report, evidence, scope)

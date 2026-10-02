from .models import Citation, ServiceError


def validate_citation(citation, returned, scope):
    if citation.case_id != scope.case_id:
        raise ServiceError('invalid_citation', 422)
    fields = set(Citation.model_fields)
    for evidence in returned:
        if evidence.model_dump(include=fields) == citation.model_dump():
            return evidence
    raise ServiceError('invalid_citation', 422)


def validate_report(report, returned, scope):
    for claim in (*report.findings, *report.counter_evidence, *report.policy_basis):
        for citation in claim.citations:
            evidence = validate_citation(citation, returned, scope)
            if claim.fact_key != evidence.fact_key or type(claim.fact_value) is not type(evidence.fact_value) or claim.fact_value != evidence.fact_value:
                raise ServiceError('invalid_fact', 422)
    return report

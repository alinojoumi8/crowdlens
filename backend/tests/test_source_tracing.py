from app.services.source_tracing import SourceIndex, trace_claims
from app.services.evidence_verifier import verify_claims
from app.services.decision_gateway import DecisionResult

SCOPE = {'graph_id': 'g', 'case_id': 'c', 'case_version_id': 'v'}

def source(i, text, **kw):
    return {**SCOPE, 'uuid': str(i), 'document_id': 'doc', 'filename': 'record.pdf', 'page': i,
            'data': text, **kw}


def test_search_original_chunks_beyond_card_limit_and_scope_isolation():
    rows = [source(i, 'Unrelated account information.') for i in range(1, 40)]
    rows += [source(40, 'Alex filed the motion on 4 May 2025.'), source(41, 'Alex filed the motion on 4 May 2025.', case_version_id='other')]
    index = SourceIndex(rows, SCOPE)
    claims, evidence = trace_claims([{'claim_id': 'c1', 'text': 'Alex filed the motion on 4 May 2025.'}], index)
    assert evidence[0]['locator']['page'] == 40
    assert all(e['case_version_id'] == 'v' for e in evidence)
    assert claims[0]['evidence_ids'] == ['episode:40']
    assert evidence[0]['excerpt'] == rows[39]['data']
    assert SourceIndex(rows[:-2], SCOPE).digest != index.digest


class Runner:
    def __init__(self, labels): self.labels = iter(labels)
    def evaluate(self, **kw):
        return DecisionResult('ok', model='test', answers={key: {'choice': next(self.labels), 'confidence': .95} for key in kw['questions']})


def test_candidate_search_separates_conflicts_and_insufficient_matches():
    index = SourceIndex([source(1, 'Alex filed the motion on 4 May 2025.'), source(2, 'Alex filed the motion on 5 May 2025.')], SCOPE)
    claims, evidence = trace_claims([{'claim_id': 'c', 'text': 'Alex filed the motion on 4 May 2025.'}], index)
    check = verify_claims(claims, evidence, mode='shadow', runner=Runner(['supported', 'contradicted']))[0]
    assert check['outcome'] == 'conflicting'
    assert check['claim_text'] == claims[0]['text']
    assert {s['judgment']['choice'] for s in check['sources']} == {'supported', 'contradicted'}
    check = verify_claims(claims, evidence, mode='shadow', runner=Runner(['supported', 'insufficient']))[0]
    assert check['outcome'] == 'supported'


def test_unknown_scope_cannot_search_private_source_pool():
    assert not SourceIndex([source(1, 'Alex filed a motion.')], {'graph_id': 'g'}).sources


def test_unextracted_prose_remains_visible_and_is_not_silently_certified():
    from app.services.source_tracing import include_uncovered_blocks
    text = 'The report makes an additional assertion without an extracted claim.'
    claims = include_uncovered_blocks(text, [], SCOPE)
    assert claims[0]['text'] == text
    assert claims[0]['kind'] == 'unextracted_passage'


def test_uncertain_candidate_cannot_hide_behind_a_supported_source():
    class UncertainRunner:
        def evaluate(self, **kw):
            return DecisionResult('ok', answers={k: {'choice': 'supported', 'confidence': .95 if i == 0 else .4} for i,k in enumerate(kw['questions'])})
    index = SourceIndex([source(1, 'Alex filed the motion on 4 May 2025.'), source(2, 'Alex filed the motion on 5 May 2025.')], SCOPE)
    claims, evidence = trace_claims([{'claim_id': 'c', 'text': 'Alex filed the motion on 4 May 2025.'}], index)
    assert verify_claims(claims, evidence, mode='shadow', runner=UncertainRunner())[0]['outcome'] == 'unverified'


def test_report_summary_checks_are_persisted_and_kept_distinct():
    from app.services.report_agent import Report, ReportOutline, ReportManager, ReportStatus
    check={'claim_text':'Summary factual assertion.','outcome':'unverified','sources':[]}
    report=Report('r','s','g','req',ReportStatus.NEEDS_REVIEW,
                  outline=ReportOutline('Title','Summary factual assertion.',[],summary_claim_checks=[check]))
    loaded=ReportManager._dict_to_report('r',report.to_dict())
    assert loaded.outline.summary_claim_checks==[check]

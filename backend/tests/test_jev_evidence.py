import hashlib

from app.services.evidence_verifier import precheck_citation, verify_claims, associate_claims
from app.services.decision_gateway import DecisionResult
from app.services.report_agent import Report, ReportSection, ReportOutline, ReportManager, ReportStatus

TEXT = 'The response is due Friday. The hearing is Monday.'
EVIDENCE = {'evidence_id': 'e1', 'origin': 'source_document', 'excerpt': TEXT,
            'source_hash': hashlib.sha256(TEXT.encode()).hexdigest(), 'graph_id': 'g',
            'case_version_id': 'v1', 'document_id': 'doc1', 'episode_id': 'chunk1',
            'locator': {'chunk_index': 0, 'char_start': 0, 'char_end': len(TEXT)}}
CLAIM = {'claim_id': 'c1', 'text': 'The response is due Friday.', 'kind': 'source_fact',
         'graph_id': 'g', 'case_version_id': 'v1', 'evidence_ids': ['e1'], 'critical': True}


def test_source_prechecks():
    assert precheck_citation(CLAIM, None) == 'missing_source'
    assert precheck_citation(CLAIM, {'origin': 'simulation', 'excerpt': TEXT}) == 'wrong_origin'
    assert precheck_citation(CLAIM, {**EVIDENCE, 'case_version_id': 'v2'}) == 'scope_mismatch'
    assert precheck_citation(CLAIM, {**EVIDENCE, 'graph_id': 'other'}) == 'scope_mismatch'
    assert precheck_citation({**CLAIM, 'quote': 'Tuesday'}, EVIDENCE) == 'quote_absent'
    assert precheck_citation(CLAIM, {**EVIDENCE, 'excerpt': 'changed'}) == 'source_hash_mismatch'
    assert precheck_citation(CLAIM, EVIDENCE) is None
    assert precheck_citation({**CLAIM, 'text': 'Friday is the response deadline.'}, EVIDENCE) is None


class Runner:
    def __init__(self, status='ok', choice='supported', confidence=.95):
        self.calls = []
        self.status, self.choice, self.confidence = status, choice, confidence
    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return DecisionResult(self.status, model='jev-1.13.0', answers={key: {
            'choice': self.choice, 'confidence': self.confidence,
            'probabilities': {'supported': .025, 'contradicted': .95, 'insufficient': .025},
        } for key in kwargs['questions']})


def test_missing_and_unknown_sources_make_no_calls():
    runner = Runner()
    checks = verify_claims([CLAIM], [], mode='on', runner=runner)
    assert checks[0]['outcome'] == 'unverified'
    assert checks[0]['reason'] == 'missing_source'
    assert not runner.calls


def test_source_context_is_used_and_failures_unverified():
    for status, choice, confidence, expected in [('ok', 'contradicted', .95, 'contradicted'), ('ok', 'supported', .4, 'unverified'), ('unavailable', 'supported', .95, 'unverified')]:
        runner = Runner(status, choice, confidence)
        checks = verify_claims([CLAIM], [EVIDENCE], mode='on', runner=runner)
        assert checks[0]['outcome'] == expected
        assert runner.calls[0]['state']['pairs'][0]['evidence']['excerpt'] == TEXT


def test_claim_associations_must_exist_in_report_and_reference_retrieved_ids():
    class LLM:
        def chat_json(self, **kwargs):
            return {'claims': [{'text': CLAIM['text'], 'evidence_ids': ['e1']},
                               {'text': 'Invented claim.', 'evidence_ids': ['e1']},
                               {'text': CLAIM['text'], 'evidence_ids': ['unknown']}]}
    claims = associate_claims(CLAIM['text'], [EVIDENCE], LLM(), {'graph_id': 'g', 'case_version_id': 'v1'})
    assert len(claims) == 2
    assert claims[0]['evidence_ids'] == ['e1']
    assert claims[1]['association_error'] == 'unknown_evidence_id'


def test_claim_checks_roundtrip_and_critical_review_cannot_average_away():
    section = ReportSection('Section', content=CLAIM['text'], claims=[CLAIM], claim_checks=[{'outcome': 'contradicted', 'critical': True, 'mode': 'on'}])
    report = Report('r', 's', 'g', 'req', ReportStatus.GENERATING,
                    outline=ReportOutline('Title', 'Summary', [section]),
                    claim_checks=section.claim_checks, quality_score={'score': 100})
    loaded = ReportManager._dict_to_report('r', report.to_dict())
    assert loaded.outline.sections[0].claims == [CLAIM]
    assert loaded.claim_checks == report.claim_checks
    ReportManager.apply_quality_status(loaded)
    assert loaded.status == ReportStatus.NEEDS_REVIEW
    loaded.claim_checks[0]['mode'] = 'shadow'
    ReportManager.apply_quality_status(loaded)
    assert loaded.status == ReportStatus.COMPLETED


def test_changed_section_invalidates_cached_checks(monkeypatch):
    from app.config import Config
    from app.services.report_agent import ReportAgent
    from app.services import evidence_verifier
    monkeypatch.setattr(Config, 'JEV_EVIDENCE_MODE', 'shadow')
    calls = []
    monkeypatch.setattr(evidence_verifier, 'associate_claims', lambda text, *args: calls.append(text) or [{**CLAIM, 'text': text}])
    monkeypatch.setattr(evidence_verifier, 'verify_claims', lambda claims, *args, **kw: [{'claim_id': claims[0]['claim_id'], 'outcome': 'unverified', 'mode': 'shadow'}])
    agent = object.__new__(ReportAgent)
    agent.graph_id, agent.simulation_id, agent.simulation_config, agent.llm = 'g', 's', {}, object()
    section = ReportSection('Section', content=CLAIM['text'], evidence_cards=[EVIDENCE])
    report = Report('r', 's', 'g', 'req', ReportStatus.GENERATING, outline=ReportOutline('Title', '', [section]))
    agent._check_report_claims(report)
    first_hash = section.claim_check_hash
    agent._check_report_claims(report)
    assert len(calls) == 1
    section.content = 'The response is due Thursday.'
    agent._check_report_claims(report)
    assert calls == [CLAIM['text'], section.content]
    assert section.claim_check_hash != first_hash
    assert section.claims[0]['text'] == section.content


def test_storage_resolves_original_episode_not_extracted_fact():
    from app.storage.neo4j_storage import Neo4jStorage
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def run(self, query, **params):
            assert params == {'gid': 'g', 'ids': ['chunk1']}
            return [{'episode': {'uuid': 'chunk1', 'data': TEXT, 'document_id': 'doc1', 'case_version_id': 'v1', 'page': 4}}]
    class Driver:
        def session(self):
            return Session()
    class Search:
        def search_edges(self, *args):
            return [{'uuid': 'edge', 'fact': 'An incorrect extracted summary.', 'episode_ids': ['chunk1']}]
    storage = object.__new__(Neo4jStorage)
    storage._driver, storage._search = Driver(), Search()
    storage._assert_embedding_compatible = lambda graph_id: None
    result = storage.search('g', 'deadline')
    source = result['edges'][0]['source_evidence'][0]
    assert source['excerpt'] == TEXT
    assert source['document_id'] == 'doc1'
    assert source['locator']['page'] == 4
    assert source['locator']['offset_basis'] == 'stored_chunk'
    assert source['origin'] == 'source_document'


def test_shadow_tool_text_is_identical_to_off(monkeypatch):
    from app.config import Config
    from app.services.report_agent import ReportAgent
    class Result:
        edges = [{'fact': 'Extracted fact.', 'source_evidence': [EVIDENCE]}]
        def to_text(self):
            return 'Baseline tool output.'
    agent = object.__new__(ReportAgent)
    monkeypatch.setattr(Config, 'JEV_EVIDENCE_MODE', 'off')
    original = agent._render_evidence_result(Result())
    monkeypatch.setattr(Config, 'JEV_EVIDENCE_MODE', 'shadow')
    assert agent._render_evidence_result(Result()) == original
    assert agent._last_tool_evidence[0]['excerpt'] == TEXT


def test_rollback_preserves_historical_checks_without_applying_them(monkeypatch):
    from app.config import Config
    from app.services.report_agent import ReportAgent
    monkeypatch.setattr(Config, 'JEV_EVIDENCE_MODE', 'off')
    agent = object.__new__(ReportAgent)
    agent.graph_id, agent.simulation_id, agent.simulation_config = 'g', 's', {}
    check = {'critical': True, 'mode': 'on', 'outcome': 'contradicted', 'section_title': 'Original'}
    report = Report('r', 's', 'g', 'req', ReportStatus.GENERATING,
                    outline=ReportOutline('Title', '', [ReportSection('Original'), ReportSection('Regenerated')]),
                    claim_checks=[check], quality_score={'score': 100})
    agent._check_report_claims(report)
    ReportManager.apply_quality_status(report)
    assert report.status == ReportStatus.COMPLETED
    assert report.claim_checks == [check]

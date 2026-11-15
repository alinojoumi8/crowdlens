"""Public provider syntax and fictional sources; no client documents."""
from types import SimpleNamespace
from copy import deepcopy

import pytest

from app.services.report_agent import Report, ReportAgent, ReportManager, ReportStatus
from app.utils.llm_client import EmptyLLMResponseError


NATIVE = (']<]minimax[>[<tool_call>]<]minimax[>[<invoke name="quick_search">'
          ']<]minimax[>[<query>the original email</query>'
          ']<]minimax[>[<limit>4</limit>]<]minimax[>[</invoke>'
          ']<]minimax[>[</tool_call>')


def chat_agent(monkeypatch, responses):
    grounding = {'report_contract': 'report-grounding-v1', 'status': 'available',
        'original_sources': [{'document_id': 'doc_fictional', 'excerpt':
            'The examiner wrote: We will request the records after authorization.'}],
        'simulation_activity': {'summary': {}, 'actions': []}, 'limitations': []}
    report = Report('r', 's', 'g', 'Analyze the original email.', ReportStatus.NEEDS_REVIEW,
        evidence_only=True, report_mode='legal_case', source_grounding=grounding,
        forecast={'status': 'unavailable', 'reason': 'evidence_only', 'probabilities': []},
        markdown_content='Generated draft: authority already existed. ' + 'x' * 16000)
    monkeypatch.setattr(ReportManager, 'get_report_by_simulation', lambda *a, **kw: report)
    agent = ReportAgent.__new__(ReportAgent)
    agent.simulation_id, agent.graph_id, agent.simulation_config = 's', 'g', {}
    agent.report_mode, agent.evidence_only = 'legal_case', False
    agent.report_logger = None
    agent.simulation_requirement = report.simulation_requirement
    agent._get_tools_description = lambda: 'quick_search(query, limit)'
    calls, tools = [], []
    remaining = iter(responses)
    def chat(**kwargs):
        calls.append(deepcopy(kwargs))
        result = next(remaining)
        if isinstance(result, Exception):
            raise result
        return result
    agent.llm = SimpleNamespace(chat=chat, chat_json=lambda **kw: {'conflicts': []})
    agent._execute_tool = lambda name, params: tools.append((name, params)) or 'Original email: future request.'
    return agent, calls, tools


def test_native_xml_tool_call_is_executed_instead_of_becoming_garbled_chat(monkeypatch):
    agent, calls, tools = chat_agent(monkeypatch, [NATIVE, 'The quoted words describe a future request.'])
    result = agent.chat('Was authorization already granted?')
    assert result['response'] == 'The quoted words describe a future request.'
    assert tools == [('quick_search', {'query': 'the original email', 'limit': 4})]
    assert len(calls) == 2


def test_chat_binds_saved_evidence_only_contract_and_original_sources(monkeypatch):
    agent, calls, _ = chat_agent(monkeypatch, ['The source does not establish that.'])
    agent.chat('Can the generated draft be trusted?')
    messages = calls[0]['messages']
    assert agent.evidence_only is True
    assert any('We will request the records after authorization.' in m['content'] for m in messages)
    system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
    assert 'burden' in system and 'standard of proof' in system
    assert 'numerical forecasts disabled' in system
    assert 'Generated draft: authority already existed.' not in system


def test_chat_repairs_an_unverified_quote_without_discarding_a_usable_answer(monkeypatch):
    draft = 'The memo describes “a planned request.” [doc_fictional] Preserve this supported context.'
    agent, calls, _ = chat_agent(monkeypatch, [draft])
    responses = iter([{'conflicts': []}, {'replacements': [
        {'target_id': 0, 'replacement': 'a future request.'}]}, {'conflicts': []}])
    agent.llm.chat_json = lambda **kw: next(responses)
    result = agent.chat('What does the memo describe?')
    assert result['response'] == (
        'The memo describes a future request. [doc_fictional] Preserve this supported context.')
    assert len(calls) == 1


def test_chat_replaces_an_unsupported_legal_test_with_a_verification_gap(monkeypatch):
    draft = 'The opponent must prove bias beyond reasonable doubt.'
    agent, calls, _ = chat_agent(monkeypatch, [draft])
    gap = 'The supplied memo does not establish the burden or standard; verify the governing authorities.'
    responses = iter([{'conflicts': [], 'unsupported_legal_rules': [
        {'draft_span': draft, 'explanation': 'This legal rule is not established by the source.'}]},
        {'replacements': [{'target_id': 0, 'replacement': gap}]},
        {'conflicts': [], 'unsupported_legal_rules': []}])
    agent.llm.chat_json = lambda **kw: next(responses)
    assert agent.chat('Who bears the burden?')['response'] == gap
    assert len(calls) == 1


def test_unresolved_legal_rules_return_an_actionable_review_notice_without_another_answer(monkeypatch):
    draft = 'The opponent must prove bias beyond reasonable doubt.'
    agent, calls, _ = chat_agent(monkeypatch, [draft])
    review = {'conflicts': [], 'unsupported_legal_rules': [
        {'draft_span': draft, 'explanation': 'This legal rule is not established by the source.'}]}
    responses = iter([review, {'replacements': [{'target_id': 0, 'replacement': draft}]}, review])
    agent.llm.chat_json = lambda **kw: next(responses)
    result = agent.chat('Who bears the burden?')
    assert result['quality_status'] == 'needs_review'
    assert result['reason'] == 'legal_rule_verification_failed'
    assert 'withholding' in result['response'] and 'governing authorities' in result['response']
    assert 'beyond reasonable doubt' not in result['response']
    assert len(calls) == 1


@pytest.mark.parametrize('resolved', [True, False])
def test_chat_with_authorities_retries_a_rejected_legal_draft_once(monkeypatch, resolved):
    draft = 'The opponent must prove bias beyond reasonable doubt.'
    corrected = 'The offering party bears the burden. [doc_law_fictional]'
    agent, calls, tools = chat_agent(monkeypatch, [draft, corrected if resolved else draft])
    report = ReportManager.get_report_by_simulation('s')
    report.source_grounding['authority_sources'] = [{
        'document_id': 'doc_law_fictional', 'excerpt': 'The offering party bears the burden.'}]
    review = {'conflicts': [], 'unsupported_legal_rules': [
        {'draft_span': draft, 'explanation': 'The authority assigns the burden to the offering party.'}]}
    rejected_correction = {'replacements': [{'target_id': 0, 'replacement': draft}]}
    remaining_reviews = iter([review, rejected_correction] + (
        [{'conflicts': []}] if resolved else [review, rejected_correction]))
    agent.llm.chat_json = lambda **kw: next(remaining_reviews)

    result = agent.chat('Who bears the burden?', report=report)

    assert len(calls) == 2 and tools == []
    assert 'authority_sources' in calls[-1]['messages'][-1]['content']
    if resolved:
        assert result['response'] == corrected
    else:
        assert result['reason'] == 'legal_rule_verification_failed'
        assert 'supplied authorities' in result['response']


@pytest.mark.parametrize('bad', [']<]minimax[>[', '<tool_call><invoke name="unknown"/></tool_call>',
    '<tool_call><invoke name="quick_search"><query>unfinished'])
def test_unusable_chat_gets_bounded_plain_answer_continuation(monkeypatch, bad):
    agent, calls, tools = chat_agent(monkeypatch, [bad, 'A usable answer.'])
    assert agent.chat('Synthetic question')['response'] == 'A usable answer.'
    assert len(calls) == 2 and tools == []


def test_repeated_malformed_chat_is_an_error_instead_of_success(monkeypatch):
    agent, calls, tools = chat_agent(monkeypatch, [']<]minimax[>['] * 4)
    with pytest.raises(EmptyLLMResponseError):
        agent.chat('Synthetic question')
    assert len(calls) == 2 and tools == []


@pytest.mark.parametrize('native', [
    '<tool_call><invoke name="unknown"><query>x</query></invoke></tool_call>',
    '<tool_call><invoke name="quick_search"><query>x</query><query>y</query></invoke></tool_call>',
    '<tool_call><!DOCTYPE x [<!ENTITY x "bad">]><invoke name="quick_search"/></tool_call>',
])
def test_native_xml_rejects_unknown_duplicate_or_declared_entities(native):
    agent = ReportAgent.__new__(ReportAgent)
    assert agent._parse_tool_calls(native) == []


def test_native_xml_preserves_numeric_search_text_as_a_string():
    agent = ReportAgent.__new__(ReportAgent)
    native = '<tool_call><invoke name="quick_search"><query>2025</query><limit>4</limit></invoke></tool_call>'
    assert agent._parse_tool_calls(native) == [{'name': 'quick_search', 'parameters': {'query': '2025', 'limit': 4}}]


@pytest.fixture
def chat_api(monkeypatch):
    from flask import Flask
    from app.api import report as api, report_bp
    saved = Report('current', 's', 'g', 'Fictional source', ReportStatus.NEEDS_REVIEW,
                   evidence_only=True, report_mode='legal_case', report_depth='fast')
    monkeypatch.setattr(api.SimulationManager, 'get_simulation', lambda *_: SimpleNamespace(project_id='p', graph_id='g'))
    monkeypatch.setattr(api.ProjectManager, 'get_project', lambda *_: SimpleNamespace(graph_id='g', simulation_requirement='Fictional'))
    monkeypatch.setattr(api, 'GraphToolsService', lambda **kw: object())
    monkeypatch.setattr(api.ReportManager, 'get_report', lambda rid: saved if rid == 'current' else None)
    calls = []
    def chat(**kwargs):
        calls.append(kwargs)
        return {'response': 'Fictional answer.'}
    monkeypatch.setattr(api, 'ReportAgent', lambda **kw: SimpleNamespace(chat=chat))
    app = Flask(__name__); app.register_blueprint(report_bp, url_prefix='/api/report')
    app.extensions['neo4j_storage'] = object()
    return app.test_client(), saved, calls


def test_chat_uses_the_report_the_user_is_viewing(chat_api):
    client, saved, calls = chat_api
    response = client.post('/api/report/chat', json={'simulation_id': 's', 'report_id': 'current', 'message': 'Question'})
    assert response.status_code == 200
    assert calls[0]['report'] is saved


def test_chat_rejects_report_from_another_simulation(chat_api):
    client, saved, calls = chat_api; saved.simulation_id = 'foreign'
    response = client.post('/api/report/chat', json={'simulation_id': 's', 'report_id': 'current', 'message': 'Question'})
    assert response.status_code == 409 and calls == []


@pytest.mark.parametrize('message', [12, [], ' ', 'x' * 15001])
def test_chat_rejects_invalid_question_before_model_execution(chat_api, message):
    client, _, calls = chat_api
    response = client.post('/api/report/chat', json={'simulation_id': 's', 'message': message})
    assert response.status_code == 400 and calls == []


@pytest.mark.parametrize('body', [[], ['question'], 'question', None,
    {'simulation_id': 12, 'message': 'Question'}])
def test_chat_rejects_nonobject_requests_and_invalid_simulation_ids(chat_api, body):
    client, _, calls = chat_api
    response = client.post('/api/report/chat', json=body)
    assert response.status_code == 400 and calls == []


def test_chat_model_protocol_failure_returns_a_safe_error(chat_api, monkeypatch):
    from app.api import report as api
    client, _, _ = chat_api
    def chat(**kwargs):
        raise EmptyLLMResponseError('PRIVATE provider payload')
    monkeypatch.setattr(api, 'ReportAgent', lambda **kw: SimpleNamespace(chat=chat))
    response = client.post('/api/report/chat', json={'simulation_id': 's', 'report_id': 'current', 'message': 'Question'})
    assert response.status_code == 502
    assert 'traceback' not in response.json and 'PRIVATE' not in response.text


def test_chat_preserves_invalid_artifact_identifier_status(chat_api, monkeypatch):
    from app.api import report as api
    from app.services.proposal_store import ProposalError
    client, _, calls = chat_api
    def invalid_identifier(_):
        raise ProposalError('invalid_id', 400)
    monkeypatch.setattr(api.ReportManager, 'get_report', invalid_identifier)
    response = client.post('/api/report/chat', json={
        'simulation_id': 's', 'report_id': '../wrong', 'message': 'Question'})
    assert response.status_code == 400 and calls == []
    assert response.json == {'success': False, 'error': 'invalid_id'}

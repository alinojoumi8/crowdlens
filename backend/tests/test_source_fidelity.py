from types import SimpleNamespace

import pytest

from app.services.source_fidelity import source_fidelity_issues
from app.services.report_agent import ReportAgent


SOURCE = 'The examiner wrote that we will request the records after authorization.'
GROUNDING = {'report_contract': 'report-grounding-v1', 'status': 'available',
             'original_sources': [{'document_id': 'doc_fictional', 'excerpt': SOURCE}]}
DRAFT = 'The examiner claimed authority already existed.'
CONFLICT = {'draft_span': DRAFT, 'document_id': 'doc_fictional', 'source_span': SOURCE,
            'explanation': 'The draft changes a future request into a claim of existing authority.'}


@pytest.mark.parametrize('field,value', [('source_span', 'Invented evidence'),
    ('draft_span', 'Not in the draft'), ('document_id', 'doc_foreign')])
def test_review_cannot_invent_source_anchors(field, value):
    item = {**CONFLICT, field: value}
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [item]})
    with pytest.raises(ValueError, match='unanchored'):
        source_fidelity_issues(llm, DRAFT, GROUNDING)


def test_unanchored_review_has_one_counted_format_recovery():
    attempts = []
    responses = iter([{'conflicts': [{**CONFLICT, 'source_span': 'A paraphrase, not source text'}]},
                      {'conflicts': [CONFLICT]}])
    def review(**kwargs):
        attempts.append(kwargs)
        return next(responses)
    issues = source_fidelity_issues(SimpleNamespace(chat_json=review), DRAFT, GROUNDING)
    assert len(attempts) == 2 and issues[0]['code'] == 'source_fidelity_conflict'
    assert 'Copy short, exact contiguous' in attempts[-1]['messages'][-1]['content']


def test_empty_source_review_has_one_counted_recovery():
    from app.utils.llm_client import EmptyLLMResponseError
    attempts = []
    def review(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise EmptyLLMResponseError('No answer text')
        return {'conflicts': []}
    assert source_fidelity_issues(SimpleNamespace(chat_json=review), DRAFT, GROUNDING) == []
    assert len(attempts) == 2


def test_documentary_review_receives_the_separate_executed_action_context():
    import json
    action_context = {'actions': [{'origin': 'model_action', 'reference': 'reddit:trace:4',
        'action_args': {'content': 'A fictional analytical response.'}}]}
    def review(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['executed_action_context'] == action_context
        return {'conflicts': []}
    assert source_fidelity_issues(SimpleNamespace(chat_json=review),
        'A fictional persona wrote an analytical response. [reddit:trace:4]',
        {**GROUNDING, 'simulation_activity': action_context}) == []


def test_legal_drafting_guidance_preserves_record_scope_and_timing():
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode, agent.evidence_only = 'legal_case', True
    agent._forecast_available = lambda: False

    guidance = ' '.join(agent._report_mode_guidance().split())

    assert 'expressly lists as reviewed' in guidance
    assert 'application counts separate from order counts' in guidance
    assert 'later records can test a historical claim' in guidance
    assert 'do not by themselves establish earlier knowledge' in guidance


def test_report_repairs_and_rechecks_attribution_to_saved_activity():
    import json
    agenda = 'The proposed agenda lists each bank and an alternative request.'
    comment = 'The June report cannot establish what was known in May.'
    actions = [
        {'reference': 'reddit:legacy:7', 'origin': 'scheduled_event', 'action_type': 'SCHEDULED_EVENT',
         'action_args': {'content': agenda}},
        {'reference': 'reddit:trace:11', 'origin': 'model_action', 'action_type': 'CREATE_COMMENT',
         'action_args': {'content': comment}},
        {'reference': 'reddit:trace:12', 'origin': 'model_action', 'action_type': 'LIKE_POST',
         'action_args': {'post_content': agenda}},
    ]
    scheduled = 'The scheduled input proposed a review of each bank. [reddit:legacy:7]'
    broad_comment = 'The simulated comment ruled out every later report. [reddit:trace:11]'
    broad_like = 'The like endorsed the alternative request. [reddit:trace:12]'
    draft = f'{scheduled}\n\n{broad_comment} {broad_like}'
    scoped_comment = 'The simulated comment addressed what the June report could establish. [reddit:trace:11]'
    scoped_like = 'The simulation recorded a like on the agenda post. [reddit:trace:12]'
    scope = {'target_id': 0, 'status': 'supported', 'draft_span': scheduled, 'document_id': 'reddit:legacy:7',
             'source_span': agenda, 'explanation': 'The scope is expressly attributed to a scheduled input.'}
    conflicts = [
        {'draft_span': broad_comment, 'document_id': 'reddit:trace:11', 'source_span': comment,
         'explanation': 'The comment addresses one report.'},
        {'draft_span': broad_like, 'document_id': 'reddit:trace:12', 'source_span': agenda,
         'explanation': 'The reaction does not identify an endorsed proposition.'},
    ]
    grounding = {**GROUNDING, 'simulation_activity': {'actions': actions}}
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode, agent.report_logger = 'legal_case', None
    agent._load_source_grounding = lambda: grounding
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    repairs = []

    def review(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        if 'targets' not in packet:
            return {'conflicts': [] if repairs else conflicts, 'scope_checks': [scope]}
        findings = [target['findings'][0] for target in packet['targets']]
        assert [finding['activity_reference'] for finding in findings] == ['reddit:trace:11', 'reddit:trace:12']
        assert all('document_id' not in finding and finding['blocking'] for finding in findings)
        repairs.append(packet)
        return {'replacements': [{'target_id': 0, 'replacement': scoped_comment},
                                 {'target_id': 1, 'replacement': scoped_like}]}

    agent.llm = SimpleNamespace(chat_json=review)
    assert agent._repair_grounded_text(draft, 'Activity', 0) == f'{scheduled}\n\n{scoped_comment} {scoped_like}'
    assert len(repairs) == 1


@pytest.mark.parametrize('reference,source_span', [
    ('reddit:trace:9', 'The participant proposed an agenda.'),
    ('reddit:trace:4', 'The participant agreed to the request.'),
])
def test_activity_conflict_requires_the_exact_record_and_words(reference, source_span):
    actions = [{'reference': 'reddit:trace:4', 'origin': 'model_action',
                'action_args': {'content': 'The participant proposed an agenda.'}}]
    item = {**CONFLICT, 'document_id': reference, 'source_span': source_span}
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [item]})
    with pytest.raises(ValueError, match='unanchored_source_fidelity_review'):
        source_fidelity_issues(llm, DRAFT, {**GROUNDING, 'simulation_activity': {'actions': actions}})


@pytest.mark.parametrize('select_entire_paragraph', [False, True])
def test_activity_cannot_support_a_documentary_scope_claim(select_entire_paragraph):
    claim = 'The examiner contacted each bank.'
    draft = f'{claim} The scheduled input repeated that claim. [reddit:legacy:7]'
    actions = [{'reference': 'reddit:legacy:7', 'origin': 'scheduled_event',
                'action_args': {'content': claim}}]
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'scope_checks': [
        {'target_id': 0, 'status': 'supported', 'draft_span': draft if select_entire_paragraph else claim,
         'document_id': 'reddit:legacy:7',
         'source_span': claim, 'explanation': 'The scheduled input repeats these words.'}]})
    with pytest.raises(ValueError, match='unanchored_source_scope_review'):
        source_fidelity_issues(llm, draft, {**GROUNDING, 'simulation_activity': {'actions': actions}})


def test_report_corrects_and_rechecks_a_source_conflict():
    reviews = iter([{'conflicts': [CONFLICT]},
                    {'replacements': [{'target_id': 0, 'replacement': 'The source describes a planned request.'}]},
                    {'conflicts': []}])
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode, agent.report_logger = 'legal_case', None
    agent._load_source_grounding = lambda: GROUNDING
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    draft = DRAFT + ' Unrelated supported text. [doc_fictional]'
    corrected = 'The source describes a planned request. Unrelated supported text. [doc_fictional]'
    calls = []
    agent.llm = SimpleNamespace(chat_json=lambda **kw: next(reviews),
        chat=lambda **kw: calls.append(kw) or corrected)
    assert agent._repair_grounded_text(draft, 'Source', 0) == corrected
    assert not calls


def test_unresolved_source_conflict_cannot_be_published():
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode, agent.report_logger = 'legal_case', None
    agent._load_source_grounding = lambda: GROUNDING
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    replies = iter([{'conflicts': [CONFLICT]},
                    {'replacements': [{'target_id': 0, 'replacement': DRAFT}]},
                    {'conflicts': [CONFLICT]}])
    agent.llm = SimpleNamespace(chat_json=lambda **kw: next(replies))
    with pytest.raises(ValueError, match='Grounding correction failed'):
        agent._repair_grounded_text(DRAFT, 'Source', 0)


@pytest.mark.parametrize('replacements', [
    [], [{'target_id': True, 'replacement': 'bad'}],
    [{'target_id': 1, 'replacement': 'bad'}],
    [{'target_id': 0, 'replacement': 42}],
    [{'target_id': 0, 'replacement': 'first'}, {'target_id': 0, 'replacement': 'second'}],
])
def test_targeted_correction_rejects_missing_or_invalid_targets(replacements):
    from app.services.source_fidelity import repair_source_conflicts
    llm = SimpleNamespace(chat_json=lambda **kw: {'replacements': replacements})
    with pytest.raises(ValueError, match='invalid_source_fidelity_correction'):
        repair_source_conflicts(llm, DRAFT, [CONFLICT], GROUNDING)


def test_targeted_correction_cannot_change_unflagged_surrounding_content():
    import json
    from app.services.source_fidelity import repair_source_conflicts
    prefix, suffix = 'Keep this exact opening.\n\n', '\n\nKeep this exact ending.'
    def correction(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['targets'][0]['draft_span'] == DRAFT
        assert SOURCE in kwargs['messages'][1]['content']
        return {'replacements': [{'target_id': 0, 'replacement': 'A prospective request was described.'}]}
    assert repair_source_conflicts(SimpleNamespace(chat_json=correction), prefix + DRAFT + suffix,
        [CONFLICT], GROUNDING) == prefix + 'A prospective request was described.' + suffix


def test_legal_rule_repair_includes_its_attribution_and_complete_paragraph():
    import json
    from app.services.source_fidelity import repair_source_conflicts
    prefix, suffix = '# Source review\n\n', '\n\nKeep this separate paragraph.'
    rule = 'an opponent must establish the objection beyond reasonable doubt'
    paragraph = 'The memo invokes an authority to say ' + rule + '. The source does not supply that authority.'
    content = prefix + paragraph + suffix
    issue = {'code': 'unsupported_legal_rule', 'blocking': True, 'draft_span': rule,
        'draft_start': content.index(rule), 'draft_end': content.index(rule) + len(rule)}
    replacement = 'The governing rule is not established by the source and requires verification.'
    def correction(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['targets'][0]['draft_span'] == paragraph
        assert packet['targets'][0]['scope'] == 'paragraph'
        return {'replacements': [{'target_id': 0, 'replacement': replacement}]}
    assert repair_source_conflicts(SimpleNamespace(chat_json=correction), content,
        [issue], GROUNDING) == prefix + replacement + suffix


def test_report_repairs_a_new_conflict_found_during_recheck_and_retains_both_attempts():
    first = 'The source describes a planned request.'
    second = 'An additional contact was made.'
    final = 'The source describes a planned request. The other contacts remain unverified.'
    calls, events = [], []
    replies = iter([
        {'conflicts': [CONFLICT]},
        {'replacements': [{'target_id': 0, 'replacement': first}]},
        {'conflicts': [{**CONFLICT, 'draft_span': second}]},
        {'replacements': [{'target_id': 0, 'replacement': 'The other contacts remain unverified.'}]},
        {'conflicts': []},
    ])
    def complete(**kwargs):
        calls.append(kwargs)
        return next(replies)
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode = 'legal_case'
    agent.report_logger = SimpleNamespace(log=lambda **kw: events.append(kw))
    agent._load_source_grounding = lambda: GROUNDING
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    agent.llm = SimpleNamespace(chat_json=complete)
    assert agent._repair_grounded_text(DRAFT + ' ' + second, 'Source', 0) == final
    results = [event['details'] for event in events if event['action'] == 'grounding_correction_result']
    assert len(calls) == 5
    assert [row['attempt'] for row in results] == [1, 2]
    assert [row['accepted'] for row in results] == [False, True]
    assert results[0]['content'] == first + ' ' + second
    assert results[1]['content'] == final


@pytest.mark.parametrize('limit', [1, 2])
def test_rejected_corrections_are_bounded_and_retained(limit):
    calls, events = [], []
    candidates = iter(['First unsupported claim.', 'Second unsupported claim.'])
    def complete(**kwargs):
        import json
        packet = json.loads(kwargs['messages'][1]['content'])
        calls.append(packet)
        if 'targets' in packet:
            return {'replacements': [{'target_id': 0, 'replacement': next(candidates)}]}
        return {'conflicts': [{**CONFLICT, 'draft_span': packet['draft']}]}
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode = 'legal_case'
    agent.report_logger = SimpleNamespace(log=lambda **kw: events.append(kw))
    agent._load_source_grounding = lambda: GROUNDING
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    agent.llm = SimpleNamespace(chat_json=complete)
    with pytest.raises(ValueError, match='Grounding correction failed'):
        agent._repair_grounded_text(DRAFT, 'Source', 0, max_corrections=limit)
    results = [event['details'] for event in events if event['action'] == 'grounding_correction_result']
    assert len(calls) == 1 + 2 * limit
    assert len(results) == limit and not any(row['accepted'] for row in results)


def test_unchanged_rejected_correction_does_not_trigger_another_model_review():
    calls = []
    replies = iter([{'conflicts': [CONFLICT]},
                    {'replacements': [{'target_id': 0, 'replacement': DRAFT}]}])
    def complete(**kwargs):
        calls.append(kwargs)
        return next(replies)
    agent = ReportAgent.__new__(ReportAgent)
    agent.report_mode, agent.report_logger = 'legal_case', None
    agent._load_source_grounding = lambda: GROUNDING
    agent._frozen_forecast = lambda: {'status': 'unavailable', 'reason': 'evidence_only'}
    agent.llm = SimpleNamespace(chat_json=complete)
    with pytest.raises(ValueError, match='Grounding correction failed'):
        agent._repair_grounded_text(DRAFT, 'Source', 0)
    assert len(calls) == 2


def test_unverified_quotation_is_repaired_without_rewriting_surrounding_prose():
    from app.services.source_fidelity import repair_source_conflicts
    content = 'Keep this sentence. The memo uses “planned request.” [doc_fictional]'
    issue = {'code': 'unverified_quotation', 'blocking': True, 'quote': 'planned request.'}
    llm = SimpleNamespace(chat_json=lambda **kw: {'replacements': [
        {'target_id': 0, 'replacement': 'a prospective request'}]})
    assert repair_source_conflicts(llm, content, [issue], GROUNDING) == (
        'Keep this sentence. The memo uses a prospective request [doc_fictional]')


def test_overlapping_quote_and_factual_conflict_are_repaired_as_one_span():
    import json
    from app.services.report_grounding import provenance_issues
    from app.services.source_fidelity import repair_source_conflicts
    draft = 'The examiner claimed “existing authority” to the bank.'
    issues = provenance_issues(draft, GROUNDING, {'reason': 'evidence_only'})
    issues.append({**CONFLICT, 'code': 'source_fidelity_conflict', 'draft_span': draft})
    def correction(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert len(packet['targets']) == 1 and packet['targets'][0]['draft_span'] == draft
        return {'replacements': [{'target_id': 0, 'replacement': 'The examiner described a future request.'}]}
    assert repair_source_conflicts(SimpleNamespace(chat_json=correction), draft, issues, GROUNDING) == (
        'The examiner described a future request.')


def test_repeated_unverified_quotes_keep_their_distinct_positions():
    from app.services.report_grounding import provenance_issues
    from app.services.source_fidelity import repair_source_conflicts
    draft = 'First “planned”.\n\nLater “planned”.'
    issues = provenance_issues(draft, GROUNDING, {'reason': 'evidence_only'})
    llm = SimpleNamespace(chat_json=lambda **kw: {'replacements': [
        {'target_id': 0, 'replacement': 'prospective'}, {'target_id': 1, 'replacement': 'anticipated'}]})
    assert repair_source_conflicts(llm, draft, issues, GROUNDING) == 'First prospective.\n\nLater anticipated.'


def test_documentary_review_requires_an_unambiguous_draft_anchor():
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [CONFLICT]})
    with pytest.raises(ValueError, match='unanchored'):
        source_fidelity_issues(llm, DRAFT + '\n\n' + DRAFT, GROUNDING)


def test_unsupported_legal_rule_requires_verification_even_when_hedged():
    draft = 'Subject to verification, the opponent must prove disqualification beyond reasonable doubt.'
    finding = {'draft_span': draft, 'explanation': 'The supplied source does not establish this legal rule.'}
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'unsupported_legal_rules': [finding]})
    issues = source_fidelity_issues(llm, draft, GROUNDING)
    assert len(issues) == 1 and issues[0]['code'] == 'unsupported_legal_rule'
    assert issues[0]['blocking'] and issues[0]['draft_span'] == draft


def test_unsupported_legal_rule_review_cannot_invent_a_draft_anchor():
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'unsupported_legal_rules': [
        {'draft_span': 'Not in this draft.', 'explanation': 'A legal rule requires verification.'}]})
    with pytest.raises(ValueError, match='unanchored'):
        source_fidelity_issues(llm, DRAFT, GROUNDING)


def test_group_scope_review_cannot_silently_skip_a_broad_institution_claim():
    draft = 'The analyst contacted all institutions before any order existed.'
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'unsupported_legal_rules': []})
    with pytest.raises(ValueError, match='scope'):
        source_fidelity_issues(llm, draft, GROUNDING)


def test_group_scope_overstatement_is_blocking_even_without_a_documentary_conflict():
    import json
    draft = 'The analyst contacted all institutions before any order existed.'
    def review(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['scope_targets'][0]['draft_span'] == draft
        return {'conflicts': [], 'unsupported_legal_rules': [], 'scope_checks': [
            {'target_id': 0, 'status': 'unsupported', 'draft_span': draft,
             'explanation': 'The source identifies a narrower group and does not establish this universal claim.'}]}
    issues = source_fidelity_issues(SimpleNamespace(chat_json=review), draft, GROUNDING)
    assert issues[0]['code'] == 'unsupported_source_scope' and issues[0]['blocking']


def test_scope_support_requires_an_exact_admitted_source_anchor():
    draft = 'The analyst contacted the institutions listed in the memo.'
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'scope_checks': [
        {'target_id': 0, 'status': 'supported', 'draft_span': draft,
         'explanation': 'A supported scope.', 'document_id': 'doc_fictional', 'source_span': 'Invented support.'}]})
    with pytest.raises(ValueError, match='scope'):
        source_fidelity_issues(llm, draft, GROUNDING)


@pytest.mark.parametrize('middle,second_bank,valid', [
    ('The examiner waited for authorization.\n', 'B', True),
    ('The examiner waited for authorization.\n', 'C', False),
    ('', 'B', False),
])
def test_scope_support_may_omit_locator_labels_only(middle, second_bank, valid):
    draft = 'The examiner contacted the two banks.'
    source = ('[Paragraph 8] The examiner contacted Bank A.\n\n'
              '[Paragraph 9] The examiner waited for authorization.\n\n'
              '[Paragraph 10] The examiner contacted Bank B.')
    span = f'The examiner contacted Bank A.\n{middle}The examiner contacted Bank {second_bank}.'
    grounding = {**GROUNDING, 'original_sources': [{'document_id': 'doc_fictional', 'excerpt': source}]}
    llm = SimpleNamespace(chat_json=lambda **kw: {'conflicts': [], 'scope_checks': [
        {'target_id': 0, 'status': 'supported', 'draft_span': draft,
         'explanation': 'The excerpt lists both banks.', 'document_id': 'doc_fictional', 'source_span': span}]})

    if valid:
        assert source_fidelity_issues(llm, draft, grounding) == []
    else:
        with pytest.raises(ValueError, match='unanchored_source_scope_review'):
            source_fidelity_issues(llm, draft, grounding)


def test_scope_retry_identifies_a_draft_span_from_the_wrong_paragraph():
    recommendation = 'Assess the orders separately for each bank.'
    draft = f'{SOURCE}\n\n{recommendation}'
    wrong_paragraph = {'target_id': 0, 'status': 'supported', 'draft_span': SOURCE,
        'explanation': 'The source contains the quoted words.',
        'document_id': 'doc_fictional', 'source_span': SOURCE}
    corrected = {'target_id': 0, 'status': 'not_factual', 'draft_span': recommendation,
        'explanation': 'This is a recommendation about how to assess the orders.'}

    def review(**kwargs):
        retry = kwargs['messages'][-1]['content']
        check = corrected if 'scope_target 0 has a mismatched draft_span' in retry else wrong_paragraph
        return {'conflicts': [], 'scope_checks': [check]}

    assert source_fidelity_issues(SimpleNamespace(chat_json=review), draft, GROUNDING) == []


def test_reference_law_is_supplied_to_review_separately_from_case_allegations():
    import json
    legal = {'document_id': 'doc_law', 'excerpt': 'A synthetic legal rule.', 'citation': 'Fictional Reference'}
    def review(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['authority_sources'] == [legal]
        assert packet['original_sources'] == GROUNDING['original_sources']
        return {'conflicts': []}
    assert source_fidelity_issues(SimpleNamespace(chat_json=review), 'An attributed analysis.',
        {**GROUNDING, 'authority_sources': [legal]}) == []


def test_scope_audit_distinguishes_a_recommendation_within_a_mixed_paragraph():
    import json
    draft = ('The memo is working analysis. As an organizing recommendation, '
             'assess the orders separately for each bank.')
    def review(**kwargs):
        packet = json.loads(kwargs['messages'][1]['content'])
        assert packet['scope_targets'][0]['scope_phrases'] == ['the orders', 'each bank']
        assert 'mixed paragraph' in kwargs['messages'][0]['content']
        return {'conflicts': [], 'scope_checks': [{'target_id': 0, 'status': 'not_factual',
            'draft_span': 'assess the orders separately for each bank.',
            'explanation': 'The scope phrases occur in an organizing recommendation, not an event claim.'}]}
    assert source_fidelity_issues(SimpleNamespace(chat_json=review), draft, GROUNDING) == []


def test_legal_rule_gap_is_reported_when_no_source_is_admitted():
    draft = 'The applicant must prove the claim beyond a reasonable doubt.'
    grounding = {'report_contract': 'report-grounding-v1', 'status': 'unavailable'}
    calls = []
    def review(**kwargs):
        calls.append(kwargs)
        return {'conflicts': [], 'unsupported_legal_rules': [
            {'draft_span': draft, 'explanation': 'No admitted source establishes this standard of proof.'}]}
    issues = source_fidelity_issues(SimpleNamespace(chat_json=review), draft, grounding)
    assert len(calls) == 1
    assert [(issue['code'], issue['blocking']) for issue in issues] == [('unsupported_legal_rule', True)]

import copy
import pytest
from evidence_draft_samples import SCOPE, TEXT, sample_source, sample_claim


def validate(claims=None, sources=None):
    from app.services.claim_ledger import validate_ledger
    return validate_ledger([sample_claim()] if claims is None else claims,
                           [sample_source()] if sources is None else sources, SCOPE)


def test_source_provenance_and_valid_allegation():
    assert not any(f['blocking'] for f in validate())


@pytest.mark.parametrize('mutation,code', [
    ({'citation_ids': ['invented']}, 'unknown_citation'),
    ({'citation_ids': []}, 'missing_citation'),
    ({'attribution': ''}, 'missing_attribution'),
    ({'quote': 'The hearing is Thursday.'}, 'quote_absent'),
    ({'scope': {**SCOPE, 'case_version_id': 'v2'}}, 'scope_mismatch'),
    ({'kind': 'simulation_observation'}, 'new_simulation_observation'),
])
def test_invalid_claim_cannot_pass(mutation, code):
    findings = validate([{**sample_claim(), **mutation}])
    assert any(f['code'] == code and f['blocking'] for f in findings)


@pytest.mark.parametrize('mutation', [
    {'source_hash': 'bad'}, {'window_hash': 'bad'}, {'window_start': 1},
    {'case_id': 'foreign'}, {'origin': 'simulation'}, {'episode_id': ''},
])
def test_invalid_source_cannot_establish_provenance(mutation):
    assert any(f['blocking'] for f in validate(sources=[{**sample_source(), **mutation}]))


def analysis(identifier, premises):
    return {**sample_claim(), 'claim_id': identifier, 'kind': 'analysis',
            'citation_ids': [], 'premise_claim_ids': premises}


@pytest.mark.parametrize('claims,code', [
    ([analysis('a', ['a'])], 'premise_cycle'),
    ([analysis('a', ['b']), analysis('b', ['a'])], 'premise_cycle'),
    ([analysis('a', [])], 'missing_premises'),
    ([analysis('a', ['missing'])], 'unknown_premise'),
    ([sample_claim(), sample_claim()], 'duplicate_claim_id'),
])
def test_premise_graph_rejects_ungrounded_analysis(claims, code):
    assert any(f['code'] == code and f['blocking'] for f in validate(claims))


def test_grounded_chain_retains_unresolved_premise():
    source_claim = sample_claim()
    source_claim['checks'] = [{'outcome': 'conflicting'}]
    claims = [source_claim, analysis('b', ['claim_01']), analysis('c', ['b'])]
    findings = validate(claims)
    assert not any(f['blocking'] for f in findings)
    assert {f['claim_id'] for f in findings if f['code'] == 'premise_conflicting'} == {'b', 'c'}


@pytest.mark.parametrize('ledger', [None, {}, ['invalid'], [{'claim_id': []}]])
def test_malformed_ledger_fails_as_findings(ledger):
    from app.services.claim_ledger import validate_ledger
    assert any(f['blocking'] for f in validate_ledger(ledger, [], SCOPE))


@pytest.mark.parametrize('change', [{'kind': []}, {'checks': [{'outcome': []}]}, {'quote': []}])
def test_malformed_model_fields_do_not_crash_validation(change):
    assert any(f['blocking'] for f in validate([{**sample_claim(), **change}]))


def test_summary_unicode_edits_preserve_unselected_text():
    from app.services.claim_ledger import apply_summary_edits
    original = '🙂 Thursday. Other issues remain open.'
    edited = apply_summary_edits(original, [{'start': 2, 'end': 10, 'old_text': 'Thursday',
                               'new_text': 'Friday', 'claim_ids': ['claim_01']}], [sample_claim()])
    assert edited == '🙂 Friday. Other issues remain open.'
    assert apply_summary_edits(original, [], [sample_claim()]) == original


@pytest.mark.parametrize('edit', [
    {'start': 0, 'end': 8, 'old_text': 'Wrong', 'new_text': 'Friday', 'claim_ids': ['claim_01']},
    {'start': True, 'end': 8, 'old_text': 'Thursday', 'new_text': 'Friday', 'claim_ids': ['claim_01']},
    {'start': 0, 'end': 8, 'old_text': 'Thursday', 'new_text': 'Friday', 'claim_ids': ['unknown']},
])
def test_invalid_summary_edits_rejected(edit):
    from app.services.claim_ledger import apply_summary_edits
    with pytest.raises(ValueError):
        apply_summary_edits('Thursday', [edit], [sample_claim()])


def test_overlapping_summary_edits_rejected():
    from app.services.claim_ledger import apply_summary_edits
    edit = {'start': 0, 'end': 8, 'old_text': 'Thursday', 'new_text': 'Friday', 'claim_ids': ['claim_01']}
    with pytest.raises(ValueError):
        apply_summary_edits('Thursday', [edit, edit], [sample_claim()])


def test_paragraph_links_and_rendering():
    from app.services.claim_ledger import validate_paragraphs, render_paragraphs
    paragraphs = [{'text': TEXT, 'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}]
    original = copy.deepcopy(paragraphs)
    assert not validate_paragraphs(paragraphs, [sample_claim()])
    assert render_paragraphs(paragraphs, [sample_claim()]) == TEXT + ' [1]'
    assert paragraphs == original
    paragraphs[0]['claim_ids'] = ['unknown']
    assert any(f['blocking'] for f in validate_paragraphs(paragraphs, [sample_claim()]))


def test_short_unlinked_assertion_is_blocked():
    from app.services.claim_ledger import validate_paragraphs
    findings = validate_paragraphs([{'text': 'Alex wins.', 'kind': 'source_statement', 'claim_ids': []}], [sample_claim()])
    assert any(f['blocking'] for f in findings)


def test_paragraph_kind_cannot_disguise_analysis():
    from app.services.claim_ledger import validate_paragraphs
    assert any(f['blocking'] for f in validate_paragraphs(
        [{'text': TEXT, 'kind': 'analysis', 'claim_ids': ['claim_01']}], [sample_claim()]))

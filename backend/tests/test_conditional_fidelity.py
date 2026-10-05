import pytest
from evidence_draft_samples import sample_source, sample_claim, SCOPE
from app.services.evidence_verifier import text_hash
from app.services.claim_ledger import validate_ledger, validate_paragraphs

SOURCE = 'Sora says the group could assist if accessible benches are confirmed. This is possible future assistance, not an existing commitment.'

def source(text=SOURCE):
    return {**sample_source(), 'excerpt': text, 'window': text,
            'source_hash': text_hash(text), 'window_hash': text_hash(text), 'window_end': len(text)}

def claim(text=SOURCE.split('. ')[0] + '.'):
    return {**sample_claim(), 'text': text, 'attribution': 'Sora'}

@pytest.mark.parametrize('text', [
    'Confirmation of accessible benches must hold before any group assistance could occur.',
    'The group will assist when accessible benches are confirmed.',
    'Sora offers unconditional assistance.',
    'Sora says the group could assist',
    'accessible benches are confirmed.',
])
def test_conditional_source_paraphrases_fail_closed(text):
    assert any(f['code'] == 'conditional_source_requires_extract' and f['blocking']
               for f in validate_ledger([claim(text)], [source()], SCOPE))

def test_exact_conditional_source_is_allowed():
    assert not any(f['blocking'] for f in validate_ledger([claim()], [source()], SCOPE))

def test_explicit_only_when_restriction_can_be_paraphrased():
    text = 'Two glazing sessions are permitted only when a certified instructor is present.'
    assert not any(f['blocking'] for f in validate_ledger(
        [claim('A certified instructor is required for the permitted glazing sessions.')], [source(text)], SCOPE))

def test_conditional_premise_analysis_is_blocked_transitively():
    first = {**claim(), 'claim_id': 'a'}
    second = {**claim('Confirmation is required.'), 'claim_id': 'b', 'kind': 'analysis',
              'citation_ids': [], 'premise_claim_ids': ['a']}
    third = {**second, 'claim_id': 'c', 'premise_claim_ids': ['b']}
    findings = validate_ledger([first, second, third], [source()], SCOPE)
    assert {f['claim_id'] for f in findings if f['code'] == 'conditional_analysis_requires_review'} == {'b', 'c'}

def test_paragraph_cannot_strengthen_extract():
    findings = validate_paragraphs([{'text': 'The group will assist.',
        'kind': 'attributed_allegation', 'claim_ids': ['claim_01']}], [claim()])
    assert any(f['code'] == 'conditional_paragraph_requires_extract' for f in findings)

@pytest.mark.parametrize('text', ['Sora says the group may assist provided benches are confirmed.',
                                 'If benches are confirmed, Sora says the group might assist.'])
def test_conditional_orders_and_modal_variants(text):
    assert any(f['code'] == 'conditional_source_requires_extract' for f in
        validate_ledger([claim('The group is committed.')], [source(text)], SCOPE))

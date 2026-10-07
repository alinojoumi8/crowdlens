import pytest
from evidence_draft_samples import SCOPE, sample_source, sample_claim
from app.services.source_quotes import resolve_source_quotes
from app.services.evidence_verifier import text_hash


def test_unique_whitespace_projection_retains_exact_source_offsets():
    text = 'Alex states\nthat the hearing was postponed\tuntil Friday.'
    source = {**sample_source(), 'excerpt':text, 'window':text,
              'source_hash':text_hash(text), 'window_hash':text_hash(text), 'window_end':len(text)}
    original = {**sample_claim(), 'quote':'Alex states that the hearing was postponed until Friday.'}
    resolved, records = resolve_source_quotes([original], [source], SCOPE)
    assert resolved[0]['quote'] == text
    assert original['quote'] != text
    assert records[0]['source_start'] == 0 and records[0]['source_end'] == len(text)


@pytest.mark.parametrize('quote', ['Alex states that the hearing was postponed until Thursday.',
    'Alex states that the hearing was NOT postponed until Friday.',
    'alex states that the hearing was postponed until Friday.'])
def test_projection_never_corrects_substantive_or_case_changes(quote):
    original = [{**sample_claim(), 'quote':quote}]
    assert resolve_source_quotes(original, [sample_source()], SCOPE) == (original, [])


def test_repeated_whitespace_match_is_ambiguous_and_stays_unresolved():
    text = 'Alex\nstates. Alex\tstates.'
    source = {**sample_source(), 'excerpt':text, 'window':text,
              'source_hash':text_hash(text), 'window_hash':text_hash(text), 'window_end':len(text)}
    original = [{**sample_claim(), 'quote':'Alex states.'}]
    assert resolve_source_quotes(original, [source], SCOPE) == (original, [])

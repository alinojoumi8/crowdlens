import pytest
from evidence_draft_samples import SCOPE, TEXT
from app.utils.draft_budget import DraftBudget


def episode(identifier, text=TEXT, **kw):
    return {**SCOPE, 'uuid': str(identifier), 'document_id': 'doc', 'data': text, 'page': 1, **kw}


def test_scope_digest_and_exact_window():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.claim_ledger import validate_source
    rows = [episode('one', 'padding '*500 + TEXT + ' tail'*500), episode('two', case_version_id='old')]
    corpus = freeze_sources(rows, SCOPE)
    assert [s['episode_id'] for s in corpus['sources']] == ['one']
    packet = retrieve_sources(corpus, [f'"{TEXT}"'], budget=DraftBudget())
    assert TEXT in packet['sources'][0]['window']
    assert validate_source(packet['sources'][0], SCOPE) is None
    assert freeze_sources(list(reversed(rows)), SCOPE)['digest'] == corpus['digest']
    rows[0]['page'] = 3
    assert freeze_sources(rows, SCOPE)['digest'] != corpus['digest']


def test_no_fabricated_fallback_and_contradictions_retained():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    corpus = freeze_sources([episode('one', 'Alex filed the motion on Friday.'),
                              episode('two', 'Alex did not file the motion on Friday.')], SCOPE)
    assert len(retrieve_sources(corpus, ['Alex filed motion Friday'], budget=DraftBudget())['sources']) == 2
    assert retrieve_sources(corpus, ['zebras swimming'], budget=DraftBudget())['sources'] == []


def test_local_semantics_and_invalid_vectors():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    class Embedder:
        provider, model, dimensions = 'ollama', 'fake', 2
        def provider_id(self): return 'ollama:fake:2'
        def embed(self, text, **kw): return [1., 0.] if text == 'legal chronology' else [0., 1.]
    rows = [episode('one', 'Unrelated words.', embedding=[1., 0.], embedding_provider_id='ollama:fake:2'),
            episode('two', 'Different words.', embedding=[float('nan'), 1], embedding_provider_id='ollama:fake:2')]
    packet = retrieve_sources(freeze_sources(rows, SCOPE), ['legal chronology'], budget=DraftBudget(), embedder=Embedder())
    assert packet['sources'][0]['episode_id'] == 'one'
    assert packet['rankings']['semantic_covered'] == 2


def test_remote_embeddings_never_called_and_neighbors_stay_scoped():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    class Remote:
        provider = 'gemini'
        def embed(self, *a, **kw): raise AssertionError('remote')
    rows = [episode('one', chunk_index=1), episode('two', 'Nearby context.', chunk_index=2),
            episode('three', 'Foreign.', chunk_index=3, case_version_id='old')]
    packet = retrieve_sources(freeze_sources(rows, SCOPE), [TEXT], budget=DraftBudget(), embedder=Remote())
    assert {s['episode_id'] for s in packet['sources']} == {'one', 'two'}
    assert 'remote_embeddings_skipped' in packet['limitations']


def test_window_never_cuts_a_second_requested_literal_quote():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    quote = 'A long quotation ' * 40
    text = 'First quotation.' + 'x' * 1850 + quote + ' tail'
    packet = retrieve_sources(freeze_sources([episode('one',text)],SCOPE),
        ['"First quotation."', '"'+quote+'"'],budget=DraftBudget())
    assert quote in packet['sources'][0]['window']


def test_lexical_window_includes_nonliteral_late_match_and_discloses_clipping():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    relevant = 'The hearing now appears on the Friday schedule.'
    text = 'Unrelated administrative paragraph. ' * 70 + relevant
    packet = retrieve_sources(freeze_sources([episode('one', text)], SCOPE),
                              ['Hearing schedule'], budget=DraftBudget())
    assert relevant in packet['sources'][0]['window']
    assert 'source_windows_clipped' in packet['limitations']

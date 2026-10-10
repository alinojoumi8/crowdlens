import pytest
from evidence_draft_samples import SCOPE, TEXT
from app.utils.draft_budget import DraftBudget


def episode(identifier, text=TEXT, **kw):
    return {**SCOPE, 'uuid': str(identifier), 'document_id': 'doc', 'data': text, 'page': 1, **kw}


def test_long_pdf_chunk_retrieves_complete_page_with_original_offsets():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.claim_ledger import validate_source
    text = '[PDF page 7]\n' + 'Administrative material. ' * 190 + '\n[PDF page 8]\nSora could assist if benches are confirmed.\n[PDF page 9]\nContinued context.'
    packet = retrieve_sources(freeze_sources([episode('pdf', text)], SCOPE),
        ['Sora benches confirmed'], budget=DraftBudget())
    result = packet['sources'][0]
    assert result['window'] == '[PDF page 8]\nSora could assist if benches are confirmed.\n'
    assert result['locator']['page'] == 8
    assert text[result['window_start']:result['window_end']] == result['window']
    assert result['excerpt'] == text and validate_source(result, SCOPE) is None
    assert any(l.startswith('pdf_page_context_bounded') for l in packet['limitations'])


def test_quote_across_pdf_page_boundary_is_not_cut():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    quote = 'Sora could assist\n[PDF page 9]\nif funding is secured.'
    text = '[PDF page 8]\n' + quote + '\n[PDF page 10]\nEnd.'
    packet = retrieve_sources(freeze_sources([episode('pdf', text)], SCOPE),
        ['"'+quote+'"'], budget=DraftBudget())
    assert quote in packet['sources'][0]['window']


def test_fragment_hit_reranks_only_a_relevant_complete_page():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    text = 'hearing evidence schedule '*50 + '\n[PDF page 2]\nThe hearing evidence schedule remains disputed.\n[PDF page 3]\nTail.'
    packet = retrieve_sources(freeze_sources([episode('pdf', text)], SCOPE),
        ['hearing evidence schedule'], budget=DraftBudget())
    # An explicit literal hit in the fragment is retained, rather than hidden.
    assert packet['sources'][0]['window_start'] == 0
    packet = retrieve_sources(freeze_sources([episode('pdf', text)], SCOPE),
        ['schedule evidence hearing'], budget=DraftBudget())
    assert packet['sources'][0]['locator']['page'] == 2
    assert any(l.startswith('pdf_complete_page_reranked') for l in packet['limitations'])


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


def split_conditional_pdf_rows():
    # Page 2 is cut across the stored boundary; neither chunk has it complete.
    padding = '[PDF page 1]\n' + 'Background administrative material. ' * 140
    page = '\n[PDF page 2]\nSora could offer repair only if the purchaser supplies independent testing. No endorsement is given.\n'
    text = padding + page + '[PDF page 3]\nFollowing.'
    cut = len(padding) + page.index('independent')
    return [episode('left', text[:cut], chunk_index=0),
            episode('right', text[cut-100:], chunk_index=1)]


def test_recover_complete_conditional_page_from_exact_original_chunks():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.conditional_extracts import build_extract_contract
    from app.services.claim_ledger import validate_source
    rows = split_conditional_pdf_rows()
    packet = retrieve_sources(freeze_sources(rows, SCOPE), ['Sora repair purchaser testing'], budget=DraftBudget())
    assert packet['sources']
    assert len({s['evidence_id'] for s in packet['sources']}) == len(packet['sources'])
    recovered = [s for s in packet['sources'] if s.get('reconstruction')]
    assert recovered
    for s in recovered:
        assert validate_source(s, SCOPE) is None
        assert [c['episode_id'] for c in s['reconstruction']['components']] == ['left', 'right']
        assert s['locator']['page'] == 2
        assert s['locator']['offset_basis'] == 'joined_original_chunks'
    contract = build_extract_contract(recovered, SCOPE)
    assert contract and all('only if the purchaser supplies independent testing' in c['text']
                            and 'No endorsement is given.' in c['text'] for c in contract)
    changed = {**recovered[0], 'reconstruction': {'kind':'exact_overlapping_original_chunks', 'components':[]}}
    assert validate_source(changed, SCOPE) == 'invalid_chunk_reconstruction'


@pytest.mark.parametrize('mutation', ['gap', 'foreign_document', 'foreign_version', 'wrong_overlap', 'duplicate_index'])
def test_chunk_recovery_refuses_unproven_boundaries(mutation):
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    rows = split_conditional_pdf_rows()
    if mutation == 'gap': rows[1]['chunk_index'] = 2
    if mutation == 'foreign_document': rows[1]['document_id'] = 'foreign'
    if mutation == 'foreign_version': rows[1]['case_version_id'] = 'foreign'
    if mutation == 'wrong_overlap': rows[1]['data'] = 'Different original boundary.' + rows[1]['data']
    if mutation == 'duplicate_index': rows.append({**rows[1], 'uuid':'duplicate'})
    packet = retrieve_sources(freeze_sources(rows, SCOPE), ['Sora repair purchaser testing'], budget=DraftBudget())
    assert not any(s.get('reconstruction') for s in packet['sources'])


def test_repeated_or_short_overlap_is_not_a_reconstruction_proof():
    from app.services.pdf_chunk_context import exact_overlap
    assert exact_overlap('A' * 200, 'A' * 200) is None
    assert exact_overlap('left short boundary', 'boundary right') is None


def test_physical_pdf_recovers_a_page_split_between_stored_chunks(tmp_path):
    import fitz
    from app.utils.file_parser import FileParser, split_text_into_chunks
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.conditional_extracts import build_extract_contract
    from app.services.pdf_source_pages import complete_pages
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((36, 36), '\n'.join(f'Fictional background item {i} remains disputed without a finding' for i in range(25)), fontsize=9)
    page = pdf.new_page()
    page.insert_text((36, 36), 'Sora could offer repair only if the purchaser supplies independent testing\n' + '\n'.join(f'Fictional testing detail {i} requires a complete original review' for i in range(25)) + '\nNo endorsement is given and no testing has been received', fontsize=9)
    page = pdf.new_page()
    page.insert_text((36, 36), 'Following fictional material', fontsize=9)
    path = tmp_path/'split-page.pdf'; pdf.save(path); pdf.close()
    text = FileParser.extract_text(str(path))
    chunks = split_text_into_chunks(text, 1100, 100)
    assert not any(2 in [p for p, _, _ in complete_pages(c)] for c in chunks)
    rows = [episode(f'pdf-{i}', c, chunk_index=i) for i,c in enumerate(chunks)]
    packet = retrieve_sources(freeze_sources(rows, SCOPE), ['Sora repair independent testing'], budget=DraftBudget())
    recovered = [s for s in packet['sources'] if s.get('reconstruction')]
    assert len({s['window'] for s in recovered}) == len(recovered)
    contract = build_extract_contract(recovered, SCOPE)
    assert contract
    assert any('only if the purchaser supplies independent testing' in c['text']
               and 'No endorsement is given and no testing has been received' in c['text'] for c in contract)

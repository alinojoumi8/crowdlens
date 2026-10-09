import copy
import pytest
from evidence_draft_samples import SCOPE
from test_conditional_fidelity import source, claim


def helpers():
    from app.services.conditional_extracts import build_extract_contract, resolve_extract_claims, render_extract_paragraphs
    return build_extract_contract, resolve_extract_claims, render_extract_paragraphs


def test_complete_pdf_page_resolves_exactly_without_allowing_paraphrase():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.claim_ledger import validate_ledger
    from app.utils.draft_budget import DraftBudget
    text = '[PDF page 1]\n' + 'Background. ' * 400 + '\n[PDF page 2]\nSora could assist if benches are confirmed. No commitment is made.\n[PDF page 3]\nFollowing context.'
    corpus = freeze_sources([{**SCOPE, 'uuid':'pdf', 'document_id':'doc', 'data':text}], SCOPE)
    evidence = retrieve_sources(corpus, ['Sora benches confirmed'], budget=DraftBudget())['sources'][0]
    build, resolve, _ = helpers()
    contract = build([evidence], SCOPE)
    assert len(contract) == 1 and contract[0]['text'].startswith('[PDF page 2]')
    raw = [{**claim(), 'kind':'source_statement', 'citation_ids':[evidence['evidence_id']],
            'source_sentence_id':contract[0]['source_sentence_id']}]
    ledger, _ = resolve(raw, contract)
    assert validate_ledger(ledger, [evidence], SCOPE) == []
    ledger[0]['text'] = 'Sora commits to assist.'
    assert any(f['code'] == 'conditional_source_requires_extract' for f in validate_ledger(ledger, [evidence], SCOPE))


@pytest.mark.parametrize('middle', ['No page end marker. ' * 260, 'Long conditional page ' * 260])
def test_incomplete_or_oversized_pdf_page_stays_blocked(middle):
    from app.services.evidence_verifier import text_hash
    build, _, _ = helpers()
    text = '[PDF page 1]\nSora could assist if funding is secured. ' + middle
    if middle.startswith('Long'):
        text += '\n[PDF page 2]\nFollowing.'
    evidence = {**source(text), 'window':text[:2000], 'window_end':min(2000,len(text)), 'window_hash':text_hash(text[:2000])}
    assert build([evidence], SCOPE) == []


def test_selected_sentence_owns_text_even_when_model_paraphrases():
    build, resolve, paragraphs = helpers()
    evidence = source('Fictional workshop note: Sora says the group could assist if benches are confirmed. This is possible assistance, not a commitment.')
    contract = build([evidence], SCOPE)
    raw = [{**claim('Sora says the group could assist if benches are confirmed.'),
            'source_sentence_id': contract[0]['source_sentence_id']}]
    before = copy.deepcopy(raw)
    ledger, changes = resolve(raw, contract)
    assert ledger[0]['text'] == contract[0]['text']
    assert raw == before and changes[0]['claim_id'] == 'claim_01'
    draft = [{'text': 'Sora confirms assistance.', 'kind': ledger[0]['kind'], 'claim_ids': ['claim_01']}]
    rendered, records = paragraphs(draft, ledger, [evidence])
    assert rendered[0]['text'] == ledger[0]['text']
    assert draft[0]['text'] == 'Sora confirms assistance.'
    assert records[0]['paragraph_index'] == 0

@pytest.mark.parametrize('mutation', [
    {'source_sentence_id': 'invented'}, {'source_sentence_id': []},
    {'citation_ids': ['foreign']}, {'citation_ids': ['episode:one', 'foreign']},
    {'kind': 'analysis', 'citation_ids': [], 'premise_claim_ids': ['other']},
    {'premise_claim_ids': ['other']},
])
def test_extract_selection_rejects_wrong_linkage(mutation):
    build, resolve, _ = helpers()
    contract = build([source()], SCOPE)
    raw = [{**claim(), 'source_sentence_id': contract[0]['source_sentence_id'], **mutation}]
    with pytest.raises(ValueError):
        resolve(raw, contract)


def test_clipped_condition_has_no_selectable_partial_sentence():
    from app.services.evidence_verifier import text_hash
    build, _, _ = helpers()
    text = 'Sora says the group could assist if benches are confirmed ' + ('and volunteers review the plan ' * 100) + 'provided funding is secured.'
    evidence = {**source(text), 'window': text[:1000], 'window_end': 1000, 'window_hash': text_hash(text[:1000])}
    assert build([evidence], SCOPE) == []


def test_duplicate_sentence_ids_and_source_scope_are_not_ambiguous():
    build, _, _ = helpers()
    assert build([{**source(), 'case_id': 'foreign'}], SCOPE) == []
    assert build([source(), source()], SCOPE) == build([source()], SCOPE)

@pytest.mark.parametrize('changes', [
    {'kind': 'source_statement'}, {'claim_ids': ['missing']},
    {'claim_ids': ['claim_01','claim_01']}, {'text': None}, {'claim_ids': [[]]},
])
def test_render_does_not_repair_bad_paragraph_contract(changes):
    _, _, render = helpers()
    raw = [{'text': 'Paraphrase.', 'kind': 'attributed_allegation', 'claim_ids': ['claim_01'], **changes}]
    result, records = render(raw, [claim()], [source()])
    assert result == raw and records == []


def test_nonconditional_paragraphs_and_exact_legacy_claims_remain_unchanged():
    _, resolve, render = helpers()
    raw = [claim()]
    assert resolve(raw, [])[0] == raw
    p = [{'text': 'A separate fact.', 'kind': 'source_statement', 'claim_ids': ['other']}]
    assert render(p, [{**claim('A separate fact.'), 'claim_id':'other', 'kind':'source_statement', 'citation_ids':['another']}], [source()]) == (p, [])


def generate_selected(tmp_path, *, invalid_summary=False, ordinary=False, illegal_duplicate=False, guarded_count=1):
    import json
    from evidence_draft_samples import sample_report, sample_claim, TEXT
    from app.services.proposal_store import ProposalStore
    from app.services.evidence_drafting import EvidenceDraftingService
    from app.utils.draft_budget import DraftBudget
    text = 'Fictional hearing workshop note: Sora says the group could assist if benches are confirmed. This is possible assistance, not a commitment.'
    class Storage:
        def get_source_chunks(self, **scope):
            return [{**SCOPE, 'uuid':'one'+str(i) if guarded_count>1 else 'one','document_id':'doc','data':text,'page':1} for i in range(guarded_count)] + ([{**SCOPE,'uuid':'two','document_id':'doc2','data':TEXT,'page':1}] if ordinary else [])
    class LLM:
        model = 'synthetic-conditional-selection'
        def chat_json(self, messages, **kwargs):
            context = json.loads(messages[1]['content'])
            phase = messages[0]['content'].splitlines()[0]
            if phase == 'EVIDENCE_LEDGER_V1':
                assert ordinary and 'conditional_extract_contract' not in context
                assert [s['evidence_id'] for s in context['sources']] == ['episode:two']
                value = {'claims':[{**sample_claim(), 'citation_ids':['episode:one'] if illegal_duplicate else ['episode:two']}],'gaps':[]}
            elif phase == 'EVIDENCE_DRAFT_V1':
                value = {'paragraphs':[{'text':'The group is committed.' if 'source_sentence_id' in c else c['text'], 'kind':c['kind'], 'claim_ids':[c['claim_id']]} for c in context['ledger']],
                         'section_summary_claim_ids':['unknown'] if invalid_summary else [c['claim_id'] for c in context['ledger']]}
            else:
                value = {'audit_protocol':'target_reviews_v1','summary_consistent':True,
                    'claim_reviews':[{'claim_id':c['claim_id'],'outcome':'supported','evidence_ids':c['citation_ids'],'detail':'Synthetic exact sentence comparison.'} for c in context['ledger']],
                    'paragraph_reviews':[{'target_index':i,'outcome':'supported','detail':'Synthetic exact sentence.'} for i,p in enumerate(context['paragraphs'])],
                    'summary_reviews':[{'target_index':i,'outcome':'supported','detail':'Synthetic exact summary.'} for i,e in enumerate(context['summary_edits'])],
                    'document_reviews':[{'document_id':i,'outcome':'complete','detail':'Synthetic full coverage.'} for i in context['audit_contract']['reviewed_document_ids']]}
            kwargs['response_callback'](json.dumps(value))
            return value
    store = ProposalStore(tmp_path)
    record, lease = store.admit('report_root','selected','selected')
    store.update(record['proposal_id'], {'queued'}, {'state':'running','scope':SCOPE,'section_index':1})
    try:
        result = EvidenceDraftingService(Storage(), LLM(), store).generate(record['proposal_id'], sample_report().to_dict(), budget=DraftBudget())
    finally:
        lease.close()
    return result, store, Storage()


def test_service_renders_selected_sentences_and_preserves_raw_responses(tmp_path):
    record, store, _ = generate_selected(tmp_path)
    assert record['state'] == 'ready'
    assert 'The group is committed.' not in record['after']['section']
    assert record['after']['summary'].endswith(' Other issues remain open.')
    diagnostics = store.load_snapshot(record['proposal_id'], 'diagnostics', record['diagnostics_digest'])
    assert diagnostics['drafting']['parsed_response']['paragraphs'][0]['text'] == 'The group is committed.'
    assert record['extract_provenance']['paragraph_resolutions'][0]['model_text'] == 'The group is committed.'
    assert record['extract_provenance']['ledger_resolutions'][0]['model_text'] == ''
    assert record['extract_provenance']['origin'] == 'server_materialized_complete_source_excerpts'


def test_acceptance_rechecks_sentence_selection_without_changing_parent(tmp_path, monkeypatch):
    from app.services.report_agent import ReportManager
    from app.services.report_revisions import ReportRevisionService
    from evidence_draft_samples import sample_report
    monkeypatch.setattr(ReportManager,'REPORTS_DIR',str(tmp_path))
    ReportManager.save_report(sample_report())
    original = {p.name:p.read_bytes() for p in (tmp_path/'report_root').iterdir()}
    record, store, storage = generate_selected(tmp_path)
    revised = ReportRevisionService(store, storage=storage).accept('report_root',record['proposal_id'],record['proposal_digest'])
    assert revised.outline.sections[0].content == record['after']['section']
    assert {p.name:p.read_bytes() for p in (tmp_path/'report_root').iterdir()} == original


def test_new_provenance_is_sealed_without_changing_legacy_digests():
    from app.services.proposal_store import proposal_digest
    legacy = {'policy':'evidence-draft-v6-conditional-extract'}
    assert proposal_digest(legacy) == proposal_digest({**legacy,'extract_provenance':{'changed':True}})
    current = {'policy':'evidence-draft-v7-server-source-sentences','extract_provenance':{'contract':[]}}
    assert proposal_digest(current) != proposal_digest({**current,'extract_provenance':{'contract':['changed']}})


def test_finished_server_rendering_provenance_is_immutable(tmp_path):
    from app.services.proposal_store import ProposalError
    record, store, _ = generate_selected(tmp_path)
    with pytest.raises(ProposalError, match='immutable_proposal'):
        store.update(record['proposal_id'], {'ready'}, {'extract_provenance': {'contract':[]}})


def test_abbreviation_cannot_detach_reported_offer_from_negation():
    build, resolve, _ = helpers()
    text = 'It is false that Dr. Sora said the group could assist if benches are confirmed.'
    contract = build([source(text)], SCOPE)
    assert len(contract) == 1 and contract[0]['text'] == text
    from app.services.claim_ledger import validate_ledger
    assert any(f['blocking'] for f in validate_ledger(
        [claim('Sora said the group could assist if benches are confirmed.')], [source(text)], SCOPE))
    resolved, _ = resolve([{**claim('Detached model words.'), 'source_sentence_id':contract[0]['source_sentence_id']}],contract)
    assert resolved[0]['text'] == text


def test_resolved_paragraphs_remain_exportable_when_summary_blocks(tmp_path):
    from app.services.claim_ledger import render_paragraphs
    record, store, _ = generate_selected(tmp_path, invalid_summary=True)
    assert record['state'] == 'blocked'
    assert any(f['code']=='invalid_summary_edits' for f in record['findings'])
    section = render_paragraphs(record['paragraphs'],record['ledger'])
    assert 'could assist if benches are confirmed' in section
    assert 'The group is committed.' not in section
    diagnostics = store.load_snapshot(record['proposal_id'],'diagnostics',record['diagnostics_digest'])
    assert diagnostics['drafting']['parsed_response']['paragraphs'][0]['text'] == 'The group is committed.'


def test_planner_handles_only_ordinary_sources_when_guarded_excerpts_exist(tmp_path):
    record, store, _ = generate_selected(tmp_path, ordinary=True)
    assert record['state'] == 'ready'
    assert len(record['ledger']) == 2
    assert record['ledger'][0]['citation_ids'] == ['episode:two']
    assert record['ledger'][1]['text'].startswith('Fictional hearing workshop note:')
    diagnostics = store.load_snapshot(record['proposal_id'],'diagnostics',record['diagnostics_digest'])
    assert len(diagnostics['planning']['parsed_response']['claims']) == 1


def test_model_cannot_add_duplicate_guarded_source_claims(tmp_path):
    record, _, _ = generate_selected(tmp_path, ordinary=True, illegal_duplicate=True)
    assert record['state'] == 'blocked'
    assert record['findings'][0]['code'] == 'invalid_ledger'


def test_all_guarded_claims_can_fill_entire_capacity_without_planner_slot(tmp_path):
    record, _, _ = generate_selected(tmp_path, guarded_count=5)
    assert record['state'] == 'ready'
    assert len(record['ledger']) == 5
    assert len(record['extract_provenance']['contract']) == 5


def test_offer_and_payment_condition_across_complete_pages_are_preserved():
    from app.services.source_retrieval import freeze_sources, retrieve_sources
    from app.services.conditional_extracts import build_extract_contract
    from app.utils.draft_budget import DraftBudget
    from evidence_draft_samples import SCOPE
    text = '[PDF page 1]\nRana could offer replacement of eight disputed panels. The conditions continue on the next page.\n[PDF page 2]\nReplacement is offered only if the purchaser first pays $900. No liability is admitted.\n[PDF page 3]\n' + ('Unrelated filing history. ' * 250) + '\n[PDF page 4]\nTail.'
    corpus = freeze_sources([{**SCOPE,'uuid':'continued','document_id':'doc','data':text,'page':1,'chunk_index':0}], SCOPE)
    packet = retrieve_sources(corpus, ['Rana replacement eight panels'], budget=DraftBudget())
    source = packet['sources'][0]
    assert source['locator']['page'] == 1 and source['locator']['page_end'] == 2
    contract = build_extract_contract(packet['sources'], SCOPE)
    assert len(contract) == 1
    assert 'only if the purchaser first pays $900' in contract[0]['text']
    assert '[PDF page 3]' not in contract[0]['text']

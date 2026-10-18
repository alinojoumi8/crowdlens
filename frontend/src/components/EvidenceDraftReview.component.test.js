import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import EvidenceDraftReview from './EvidenceDraftReview.vue'
import * as api from '../api/report'
vi.mock('../api/report', () => ({ createEvidenceProposal: vi.fn(), getEvidenceProposal: vi.fn(), listEvidenceProposals: vi.fn(), acceptEvidenceProposal: vi.fn(), continueEvidenceProposal: vi.fn(), retryEvidenceAudit: vi.fn(), rejectEvidenceProposal: vi.fn() }))
vi.mock('./HumanClaimReview.vue', () => ({ default: { template: '<div />' } }))
const proposal = (state = 'ready') => ({ proposal_id: 'proposal_1', state, phase: 'review', proposal_digest: 'digest',
  before: { section: 'Original section.', summary: 'Original summary.' }, after: { section: 'Alex says Friday.', summary: 'Updated summary.' }, findings: [], limitations: [],
  ledger: [{ claim_id: 'claim_01', text: 'Alex says Friday.', kind: 'attributed_allegation', attribution: 'Alex', citation_ids: ['episode:one'], checks: [] }],
  sources: [{ evidence_id: 'episode:one', filename: 'record.txt', window: '<img src=x onerror=alert(1)> Friday.', locator: { page: 1 }, source_hash: 'hash' }] })
const mountReview = () => mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1 } })
const button = (w, text) => w.findAll('button').find(b => b.text() === text)
beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear() })

describe('evidence draft review', () => {
  it('shows separate comparisons, escapes sources, and accepts exact digest', async () => {
    api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal() })
    api.acceptEvidenceProposal.mockResolvedValue({ success: true, data: { report_id: 'report_revision' } })
    const wrapper = mountReview()
    await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('Original section.')
    expect(wrapper.text()).toContain('Updated summary.')
    expect(wrapper.text()).toContain('page 1')
    expect(wrapper.find('img').exists()).toBe(false)
    await button(wrapper, 'Save as new revision').trigger('click'); await flushPromises()
    expect(api.acceptEvidenceProposal).toHaveBeenCalledWith('report_root', 'proposal_1', 'digest')
    expect(wrapper.emitted('revision-created')[0]).toEqual(['report_revision'])
    wrapper.unmount()
  })
  it.each(['blocked', 'stale', 'failed', 'rejected', 'review_pending'])('cannot accept %s proposals', async state => {
    api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal(state) })
    const wrapper = mountReview()
    await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
    expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })
  it('keeps request key on explicit retry and ignores a previous report response', async () => {
    api.createEvidenceProposal.mockRejectedValueOnce(new Error('network'))
    const wrapper = mountReview()
    await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
    let finish
    api.createEvidenceProposal.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
    await button(wrapper, 'Retry request').trigger('click')
    expect(api.createEvidenceProposal.mock.calls[0][1].request_key).toBe(api.createEvidenceProposal.mock.calls[1][1].request_key)
    await wrapper.setProps({ reportId: 'different' })
    finish({ success: true, data: proposal() }); await flushPromises()
    expect(wrapper.text()).not.toContain('Original section.')
    wrapper.unmount()
  })
})

it('continues a saved source batch only on explicit request with its exact digest', async () => {
  const pending = { ...proposal('review_pending'), source_review: { batch_count: 9, completed_batches: [{}, {}], complete: false },
    source_completeness: { complete: false, inventory_available: true, documents: [], rejected_sources: [] } }
  api.getEvidenceProposal.mockResolvedValue({ data: pending })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1, initialProposalId: 'proposal_1' } })
  await flushPromises()
  expect(wrapper.text()).toContain('2 of 9 batches checked')
  expect(api.continueEvidenceProposal).not.toHaveBeenCalled()
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  let finish
  api.continueEvidenceProposal.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  await wrapper.get('[data-test="continue-source-review"]').trigger('click')
  await wrapper.get('[data-test="continue-source-review"]').trigger('click')
  expect(api.continueEvidenceProposal).toHaveBeenCalledTimes(1)
  expect(api.continueEvidenceProposal).toHaveBeenCalledWith('report_root', 'proposal_1', 'digest')
  finish({ data: { ...pending, source_review: { ...pending.source_review, completed_batches: [{}, {}, {}] } } })
  await flushPromises()
  expect(wrapper.text()).toContain('3 of 9 batches checked')
  wrapper.unmount()
})

it('retains saved progress after an allowance refusal', async () => {
  const pending = { ...proposal('review_pending'), source_review: { batch_count: 2, completed_batches: [], complete: false },
    source_completeness: { complete: false, inventory_available: true, documents: [], rejected_sources: [] } }
  api.createEvidenceProposal.mockResolvedValue({ data: pending })
  api.continueEvidenceProposal.mockRejectedValue({ response: { data: { error: 'authorization_required' } } })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  await wrapper.get('[data-test="continue-source-review"]').trigger('click'); await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('authorization required')
  expect(wrapper.text()).toContain('0 of 2 batches checked')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})

it('allows one acceptance request and ignores its result after navigation', async () => {
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal() })
  let finish
  api.acceptEvidenceProposal.mockImplementation(() => new Promise(resolve => { finish = resolve }))
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  await button(wrapper, 'Save as new revision').trigger('click')
  await button(wrapper, 'Save as new revision').trigger('click')
  expect(api.acceptEvidenceProposal).toHaveBeenCalledTimes(1)
  await wrapper.setProps({ reportId: 'different' })
  finish({ success: true, data: { report_id: 'old_revision' } }); await flushPromises()
  expect(wrapper.emitted('revision-created')).toBeUndefined()
  wrapper.unmount()
})

it('polls without recreating and stops after unmount', async () => {
  vi.useFakeTimers()
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal('running') })
  api.getEvidenceProposal.mockResolvedValue({ success: true, data: proposal('running') })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  await vi.advanceTimersByTimeAsync(1000)
  expect(api.getEvidenceProposal).toHaveBeenCalledTimes(1)
  expect(api.createEvidenceProposal).toHaveBeenCalledTimes(1)
  wrapper.unmount()
  await vi.advanceTimersByTimeAsync(3000)
  expect(api.getEvidenceProposal).toHaveBeenCalledTimes(1)
  vi.useRealTimers()
})

it('immediately disables saving after a stale acceptance response', async () => {
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal() })
  api.acceptEvidenceProposal.mockRejectedValue({ response: { status: 409, data: { error: 'stale_sources' } } })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  await button(wrapper, 'Save as new revision').trigger('click'); await flushPromises()
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('source documents changed')
  wrapper.unmount()
})

it('can recover an interrupted save after loading persisted accepting state', async () => {
  sessionStorage.setItem('evidence-proposal:report_root:1', JSON.stringify({ requestKey: 'key', proposalId: 'proposal_1' }))
  api.getEvidenceProposal.mockResolvedValue({ success: true, data: proposal('accepting') })
  api.acceptEvidenceProposal.mockResolvedValue({ success: true, data: { report_id: 'recovered_revision' } })
  const wrapper = mountReview(); await flushPromises()
  await button(wrapper, 'Retry saving revision').trigger('click'); await flushPromises()
  expect(api.acceptEvidenceProposal).toHaveBeenCalledWith('report_root', 'proposal_1', 'digest')
  expect(wrapper.emitted('revision-created')[0]).toEqual(['recovered_revision'])
  wrapper.unmount()
})

it.each(['reject', 'accept'])('ignores an older status response after %s succeeds', async action => {
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: proposal() })
  let finish
  api.getEvidenceProposal.mockImplementation(() => new Promise(resolve => { finish = resolve }))
  api.acceptEvidenceProposal.mockRejectedValueOnce(new Error('network'))
  api.acceptEvidenceProposal.mockResolvedValue({ success: true, data: { report_id: 'revision_saved' } })
  api.rejectEvidenceProposal.mockResolvedValue({ success: true, data: proposal('rejected') })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  await button(wrapper, 'Save as new revision').trigger('click'); await flushPromises()
  await button(wrapper, 'Refresh status').trigger('click')
  await button(wrapper, action === 'reject' ? 'Keep original' : 'Save as new revision').trigger('click')
  await flushPromises()
  finish({ success: true, data: proposal() }); await flushPromises()
  expect(wrapper.text()).toContain(action === 'reject' ? 'Original retained' : 'Revision saved')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})

it('keeps complete claims available and links to focusable page-range sources', async () => {
  const draft = proposal()
  const fullClaim = 'A long attributed statement. '.repeat(20)
  draft.ledger[0].text = fullClaim
  draft.sources[0].locator.page_end = 2
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: draft })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1 }, attachTo: document.body })
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(wrapper.find('.claim summary').text().length).toBeLessThan(fullClaim.length)
  expect(wrapper.find('.claim-text').text()).toBe(fullClaim.trim())
  const source = wrapper.find('.source')
  expect(wrapper.find('.claim-sources a').attributes('href')).toBe(`#${source.attributes('id')}`)
  expect(source.text()).toContain('pages 1–2')
  expect(source.find('blockquote').attributes('tabindex')).toBe('0')
  source.element.parentElement.open = false
  await wrapper.find('.claim-sources a').trigger('click')
  expect(source.element.parentElement.open).toBe(true)
  expect(document.activeElement).toBe(source.find('blockquote').element)
  wrapper.unmount()
})

it('distinguishes reconstructed text from its original chunk provenance', async () => {
  const value = proposal()
  value.sources[0] = { ...value.sources[0], reconstruction: { components: [
    { episode_id: 'original-left', chunk_index: 3, source_hash: 'left-sha' },
    { episode_id: 'original-right', chunk_index: 4, source_hash: 'right-sha' }
  ] }, locator: { page: 2, offset_basis: 'joined_original_chunks' } }
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: value })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('Reconstructed text SHA-256')
  expect(wrapper.text()).toContain('Original original-left · chunk 3 · SHA-256 left-sha')
  expect(wrapper.text()).toContain('Original original-right · chunk 4 · SHA-256 right-sha')
  expect(wrapper.text()).toContain('joined_original_chunks')
  wrapper.unmount()
})

it('submits a focused correction separately and freezes its payload for retries', async () => {
  api.createEvidenceProposal.mockRejectedValueOnce(new Error('network'))
  api.createEvidenceProposal.mockResolvedValueOnce({ success: true, data: proposal() })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_focused', sectionIndex: 2 } })
  await wrapper.find('input').setValue('May 29, 2025')
  await wrapper.findAll('input')[1].setValue('May 29, 2023')
  await wrapper.find('form textarea').setValue('In the May 29, 2023 affidavit, Alex denies signing.')
  await wrapper.find('form').trigger('submit'); await flushPromises()
  await button(wrapper, 'Retry request').trigger('click'); await flushPromises()
  const bodies = api.createEvidenceProposal.mock.calls.map(call => call[1])
  expect(bodies[0]).toEqual(bodies[1])
  expect(bodies[0].focused_correction.new_text).toBe('May 29, 2023')
  expect(bodies[0].section_index).toBe(2)
  wrapper.unmount()
})

it('allows editing a new focused request after an invalid request response', async () => {
  api.createEvidenceProposal.mockRejectedValueOnce({response:{status:400,data:{error:'invalid_request'}}})
  const wrapper = mount(EvidenceDraftReview, {props:{reportId:'report_invalid_focused',sectionIndex:1}})
  await wrapper.find('input').setValue('an invalid date')
  await wrapper.findAll('input')[1].setValue('another date')
  await wrapper.find('form textarea').setValue('Source quotation.')
  await wrapper.find('form').trigger('submit'); await flushPromises()
  expect(wrapper.find('input').element.disabled).toBe(true)
  await button(wrapper, 'New proposal').trigger('click')
  expect(wrapper.find('input').element.disabled).toBe(false)
  expect(api.createEvidenceProposal).toHaveBeenCalledTimes(1)
  wrapper.unmount()
})


it('submits a bounded wording correction with an explicit kind', async () => {
  api.createEvidenceProposal.mockResolvedValueOnce({success:true,data:proposal()})
  const wrapper = mount(EvidenceDraftReview, {props:{reportId:'report_wording',sectionIndex:1}})
  await wrapper.find('select').setValue('wording')
  await wrapper.find('input').setValue('The July 4 index.')
  await wrapper.findAll('input')[1].setValue('The index on PDF page 4.')
  await wrapper.find('form textarea').setValue('[PDF page 4] INDEX')
  await wrapper.find('form').trigger('submit'); await flushPromises()
  expect(api.createEvidenceProposal.mock.calls[0][1].focused_correction.kind).toBe('wording')
  expect(api.createEvidenceProposal.mock.calls[0][1].focused_correction.source_quote).toBe('[PDF page 4] INDEX')
  expect(api.createEvidenceProposal.mock.calls[0][1]).not.toHaveProperty('summary_selection')
  expect(wrapper.text()).toContain('Review proposed changes')
  wrapper.unmount()
})

it('finds saved proposals without relying on browser session storage', async () => {
  api.listEvidenceProposals.mockResolvedValue({data:[{proposal_id:'proposal_1',section_index:1,state:'ready',created_at:'2026-10-10T12:00:00Z'}]})
  api.getEvidenceProposal.mockResolvedValue({data:proposal()})
  const wrapper = mountReview(); await flushPromises()
  expect(wrapper.text()).toContain('Saved proposals for this section')
  await wrapper.find('.saved-proposals select').setValue('proposal_1'); await flushPromises()
  expect(wrapper.text()).toContain('Original section.')
  expect(api.createEvidenceProposal).not.toHaveBeenCalled()
  wrapper.unmount()
})

it('separates unmapped scope from an AI contradiction and keeps saving blocked', async () => {
  const record = proposal('blocked')
  record.summary_assessment = { outcome: 'contradicted', detail: 'The source says Friday, not Thursday.', evidence_ids: ['episode:one'] }
  record.findings = [{ code: 'summary_scope_unmapped', blocking: true,
    detail: 'The mapping failure does not establish a factual contradiction.',
    next_action: 'Use a focused source-backed correction.' },
    { code: 'summary_inconsistent', blocking: true, detail: record.summary_assessment.detail }]
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: record })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('summary scope unmapped')
  expect(wrapper.text()).toContain('AI summary assessment: contradicted')
  expect(wrapper.text()).toContain('Next step: Use a focused source-backed correction.')
  expect(wrapper.text()).toContain('not factual certification')
  expect(wrapper.find('[aria-label="Summary assessment sources"] a').text()).toBe('Read Source 1')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  expect(api.acceptEvidenceProposal).not.toHaveBeenCalled()
  wrapper.unmount()
})


it('does not present a historical boolean audit as proof of contradiction', async () => {
  const record = proposal('blocked')
  record.before.summary_scope_contract = { unmapped_summary_requires_review: true }
  record.findings = [{ code: 'summary_inconsistent', blocking: true }]
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: record })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(wrapper.text()).toContain('Summary scope needs review')
  expect(wrapper.text()).toContain('Summary consistency not established by AI audit')
  expect(wrapper.text()).not.toContain('AI summary assessment: contradicted')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})


it('links summary contradiction evidence outside the ledger without source zero', async () => {
  const record = proposal('blocked')
  record.sources.push({ evidence_id: 'episode:context', filename: 'context.txt', window: 'Friday.' })
  record.summary_assessment = { outcome: 'contradicted', detail: 'Retrieved context conflicts.', evidence_ids: ['episode:context'] }
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: record })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  const link = wrapper.find('[aria-label="Summary assessment sources"] a')
  expect(link.text()).toBe('Read retrieved source')
  expect(wrapper.text()).not.toContain('Read Source 0')
  expect(wrapper.find(link.attributes('href')).exists()).toBe(true)
  wrapper.unmount()
})

it('explains omitted passages and missing extraction while blocking saving', async () => {
  const record = proposal('blocked')
  record.findings = [{ code: 'source_completeness_unresolved', blocking: true, next_action: 'Restore missing source text.' }]
  record.source_completeness = { complete: false, inventory_available: true, corpus_limited: false,
    rejected_sources: [{ document_id: 'empty' }], documents: [
      { document_id: 'doc', filename: 'notes.txt', admitted_chunks: 2, expected_chunks: 2, inventory_verified: true,
        complete: false, chunks: [{ episode_id: 'late', omitted_characters: 120 }] },
      { document_id: 'empty', admitted_chunks: 0, expected_chunks: null, inventory_verified: false, complete: false, chunks: [] }] }
  api.createEvidenceProposal.mockResolvedValue({ success: true, data: record })
  const wrapper = mountReview()
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(wrapper.get('[aria-label="Source coverage"]').text()).toContain('120 characters outside review')
  expect(wrapper.text()).toContain('0 of unknown expected passages')
  expect(wrapper.text()).toContain('1 source passage(s) could not be admitted')
  expect(wrapper.text()).toContain('Restore missing source text.')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  wrapper.unmount()
})

it('sends the exact selected summary passage and freezes it on request retry', async () => {
  api.createEvidenceProposal.mockRejectedValueOnce(new Error('network'))
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_summary', sectionIndex: 1, summaryText: 'Abstract forecast. Protected text.' } })
  await wrapper.get('.summary-selection textarea').setValue('Abstract forecast.')
  await button(wrapper, 'Draft with sources').trigger('click'); await flushPromises()
  expect(api.createEvidenceProposal.mock.calls[0][1].summary_selection).toBe('Abstract forecast.')
  expect(wrapper.get('.summary-selection textarea').attributes('disabled')).toBeDefined()
  await button(wrapper, 'Retry request').trigger('click'); await flushPromises()
  expect(api.createEvidenceProposal.mock.calls[1][1]).toEqual(api.createEvidenceProposal.mock.calls[0][1])
  wrapper.unmount()
})

it('reopens a failed audit without retrying and preserves the retry key across reload', async () => {
  const failed = { ...proposal('failed'), error_code: 'audit_timeout', audit_recovery: { available: true, digest: 'saved-checkpoint' } }
  api.getEvidenceProposal.mockResolvedValue({ data: failed })
  sessionStorage.setItem('evidence-proposal:report_root:1', JSON.stringify({ proposalId: 'proposal_1' }))
  let wrapper = mountReview(); await flushPromises()
  expect(api.retryEvidenceAudit).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('billing may be unknown')
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeDefined()
  api.retryEvidenceAudit.mockRejectedValueOnce(new Error('network'))
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  const first = api.retryEvidenceAudit.mock.calls[0]
  expect(first[2].recovery_digest).toBe('saved-checkpoint')
  wrapper.unmount()
  wrapper = mountReview(); await flushPromises()
  api.retryEvidenceAudit.mockResolvedValue({ data: { ...proposal(), proposal_id: 'proposal_recovered' } })
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  expect(api.retryEvidenceAudit.mock.calls[1]).toEqual(first)
  expect(button(wrapper, 'Save as new revision').attributes('disabled')).toBeUndefined()
  wrapper.unmount()
})

it('keeps the failed draft after allowance refusal and ignores retry completion after navigation', async () => {
  api.getEvidenceProposal.mockResolvedValue({ data: { ...proposal('failed'), audit_recovery: { available: true, digest: 'saved-checkpoint' } } })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1, initialProposalId: 'proposal_1' } })
  await flushPromises()
  api.retryEvidenceAudit.mockRejectedValueOnce({ response: { data: { error: 'stopped' } } })
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toBe('stopped')
  expect(wrapper.text()).toContain('Original section.')
  let finish
  api.retryEvidenceAudit.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  await button(wrapper, 'Retry saved audit').trigger('click')
  await button(wrapper, 'Retry saved audit').trigger('click')
  expect(api.retryEvidenceAudit).toHaveBeenCalledTimes(2)
  api.getEvidenceProposal.mockResolvedValue({ data: { proposal_id: 'proposal_other', state: 'failed' } })
  await wrapper.setProps({ reportId: 'other', initialProposalId: 'proposal_other' })
  finish({ data: { ...proposal(), after: { section: 'Old retry result.' } } }); await flushPromises()
  expect(wrapper.text()).not.toContain('Old retry result.')
  wrapper.unmount()
})

it('requires a summary selection before an unmapped full-section draft', async () => {
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_unmapped', sectionIndex: 1,
    summaryText: 'A forecast. Protected text.', sectionText: 'Different section prose.' } })
  expect(wrapper.get('.summary-selection').attributes('open')).toBeDefined()
  expect(button(wrapper, 'Draft with sources').attributes('disabled')).toBeDefined()
  await wrapper.get('.summary-selection textarea').setValue('A forecast.')
  expect(button(wrapper, 'Draft with sources').attributes('disabled')).toBeUndefined()
  expect(api.createEvidenceProposal).not.toHaveBeenCalled()
  wrapper.unmount()
})

it('uses a fresh retry key and checkpoint after a definite server refusal', async () => {
  const failed = { ...proposal('failed'), audit_recovery: { available: true, digest: 'old-digest' } }
  api.getEvidenceProposal.mockResolvedValue({ data: failed })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1, initialProposalId: 'proposal_1' } })
  await flushPromises()
  api.retryEvidenceAudit.mockRejectedValueOnce({ response: { status: 409, data: { error: 'audit_checkpoint_changed' } } })
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  const first = api.retryEvidenceAudit.mock.calls[0][2]
  api.getEvidenceProposal.mockResolvedValue({ data: { ...failed, audit_recovery: { available: true, digest: 'new-digest' } } })
  await button(wrapper, 'Refresh status').trigger('click'); await flushPromises()
  api.retryEvidenceAudit.mockResolvedValue({ data: proposal() })
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  const second = api.retryEvidenceAudit.mock.calls[1][2]
  expect(second.request_key).not.toBe(first.request_key)
  expect(second.recovery_digest).toBe('new-digest')
  wrapper.unmount()
})

it('does not restore another proposal audit retry when opening a direct link', async () => {
  sessionStorage.setItem('evidence-proposal:report_root:1', JSON.stringify({
    proposalId: 'proposal_1',
    auditRetryRequest: { proposalId: 'proposal_1', request_key: 'old-request', recovery_digest: 'old-digest' }
  }))
  api.getEvidenceProposal.mockResolvedValue({ data: { ...proposal('failed'), proposal_id: 'proposal_2',
    audit_recovery: { available: true, digest: 'displayed-digest' } } })
  api.retryEvidenceAudit.mockResolvedValue({ data: proposal() })
  const wrapper = mount(EvidenceDraftReview, { props: { reportId: 'report_root', sectionIndex: 1, initialProposalId: 'proposal_2' } })
  await flushPromises()
  await button(wrapper, 'Retry saved audit').trigger('click'); await flushPromises()
  expect(api.retryEvidenceAudit).toHaveBeenCalledWith('report_root', 'proposal_2', {
    request_key: expect.any(String), recovery_digest: 'displayed-digest'
  })
  expect(api.retryEvidenceAudit.mock.calls[0][2].request_key).not.toBe('old-request')
  wrapper.unmount()
})

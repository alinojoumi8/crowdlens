import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import EvidenceDraftReview from './EvidenceDraftReview.vue'
import * as api from '../api/report'
vi.mock('../api/report', () => ({ createEvidenceProposal: vi.fn(), getEvidenceProposal: vi.fn(), acceptEvidenceProposal: vi.fn(), rejectEvidenceProposal: vi.fn() }))
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
  it.each(['blocked', 'stale', 'failed', 'rejected'])('cannot accept %s proposals', async state => {
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

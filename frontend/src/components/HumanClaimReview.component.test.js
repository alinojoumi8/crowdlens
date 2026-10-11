import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HumanClaimReview from './HumanClaimReview.vue'
import * as api from '../api/humanReviews'
vi.mock('../api/humanReviews', () => ({ getHumanReviews: vi.fn(), saveHumanReview: vi.fn(), exportHumanReviews: vi.fn() }))
const blank = () => ({ schema_version:1, packet_id:'packet_fixture', packet_sha256:'hash', reviewer_id:null, reviewer_kind:null, reviewed_at:null,
  review_seconds:null, claims:[{claim_id:'c1', support:null, attribution_correct:null, citation_support_correct:null, rationale:null}],
  reference_facts:null, omitted_reference_fact_ids:null, conflicts_handled:null, notes:null })
const view = () => ({ packet:{claims:[{claim_id:'c1',text:'Alex said Friday.',citation_ids:['source_1']}]}, packet_sha256:'hash', blank_form:blank(), reviews:[], history:[], assessment:{disagreements:[]} })
const button = (w,text) => w.findAll('button').find(b => b.text() === text)
const mountReview = () => mount(HumanClaimReview,{props:{reportId:'report_fixture', proposalId:'proposal_fixture', proposalDigest:'digest'}})
beforeEach(() => { vi.resetAllMocks(); api.getHumanReviews.mockResolvedValue({data:view()}) })

describe('human claim review', () => {
  it('saves partial labels and reloads them without filling other judgments or time', async () => {
    const wrapper = mountReview(); await flushPromises()
    await wrapper.find('input').setValue('Synthetic reviewer')
    await button(wrapper,'Open review').trigger('click')
    const claim = wrapper.find('fieldset')
    await claim.find('select').setValue('supported')
    await claim.find('textarea').setValue('Source 1, page 1 quotes Alex.')
    api.saveHumanReview.mockImplementation(async (_r,_p,form,version) => ({data:{...view(),reviews:[{version:version+1,form:{...form,reviewed_at:'2026-10-10T12:00:00Z'}}]}}))
    await wrapper.find('form').trigger('submit'); await flushPromises()
    const payload = api.saveHumanReview.mock.calls[0][2]
    expect(payload.claims[0].support).toBe('supported')
    expect(payload.claims[0].attribution_correct).toBeNull()
    expect(payload.claims[0].citation_support_correct).toBeNull()
    expect(payload.review_seconds).toBeNull()
    expect(payload.reference_facts).toBeNull()
    expect(wrapper.text()).toContain('Review saved')
    expect(api.saveHumanReview.mock.calls[0][3]).toBe(0)
    wrapper.unmount()
    api.getHumanReviews.mockResolvedValue({data:{...view(),reviews:[{version:1,form:{...payload,reviewed_at:'2026-10-10T12:00:00Z'}}]}})
    const reloaded = mountReview(); await flushPromises()
    await button(reloaded,'Synthetic reviewer · version 1').trigger('click')
    expect(reloaded.find('fieldset select').element.value).toBe('supported')
    expect(reloaded.find('fieldset textarea').element.value).toContain('page 1')
    reloaded.unmount()
  })

  it('preserves and displays conflicting reviewers as separate judgments', async () => {
    api.getHumanReviews.mockResolvedValue({data:{...view(),assessment:{disagreements:[{claim_id:'c1',field:'support',judgments:[{reviewer_id:'A',value:'supported'},{reviewer_id:'B',value:'unsupported'}]}]}}})
    const wrapper = mountReview(); await flushPromises()
    expect(wrapper.text()).toContain('A: supported; B: unsupported')
    wrapper.unmount()
  })

  it('starts timing only explicitly and pauses when the window loses focus', async () => {
    const wrapper = mountReview(); await flushPromises()
    await wrapper.find('input').setValue('Synthetic reviewer')
    await button(wrapper,'Open review').trigger('click')
    let time = 100
    vi.spyOn(performance,'now').mockImplementation(() => time)
    await button(wrapper,'Start review timer').trigger('click')
    time = 2600; window.dispatchEvent(new Event('blur')); await flushPromises()
    expect(wrapper.text()).toContain('2.5 seconds')
    expect(button(wrapper,'Start review timer')).toBeDefined()
    wrapper.unmount(); vi.restoreAllMocks()
  })

  it('rejects late data from a different proposal', async () => {
    let resolve
    api.getHumanReviews.mockReturnValueOnce(new Promise(r => {resolve=r}))
    const wrapper = mountReview()
    await wrapper.setProps({proposalId:'proposal_new',proposalDigest:'new'})
    await flushPromises()
    resolve({data:{...view(),history:[{reviewer_id:'wrong proposal',version:1,reviewed_at:'2026-10-10T12:00:00Z'}]}})
    await flushPromises()
    expect(wrapper.text()).not.toContain('wrong proposal')
    wrapper.unmount()
  })
})

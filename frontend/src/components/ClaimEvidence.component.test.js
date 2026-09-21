import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ClaimEvidence from './ClaimEvidence.vue'

describe('claim evidence', () => {
  it('shows conflict, exact source location and escaped original text', async () => {
    const wrapper = mount(ClaimEvidence, { props: { checks: [{ claim_id: 'c', claim_text: 'The hearing is Friday.', outcome: 'conflicting', sources: [{ evidence_id: 'ep:1', document_id: 'doc', filename: 'record.pdf', locator: { page: 7 }, excerpt: '<img src=x onerror=alert(1)> Thursday hearing.', judgment: { choice: 'contradicted' } }] }] } })
    await wrapper.find('summary').trigger('click')
    expect(wrapper.text()).toContain('1 need review')
    expect(wrapper.text()).toContain('Conflicting sources')
    expect(wrapper.text()).toContain('page 7')
    expect(wrapper.text()).toContain('Thursday hearing.')
    expect(wrapper.find('img').exists()).toBe(false)
  })
  it('does not fabricate a citation for an unlinked claim', () => {
    const wrapper = mount(ClaimEvidence, { props: { checks: [{ claim_text: 'Unlinked claim.', outcome: 'unverified', sources: [] }] } })
    expect(wrapper.text()).toContain('No original source linked')
    expect(wrapper.find('article').exists()).toBe(false)
  })
})

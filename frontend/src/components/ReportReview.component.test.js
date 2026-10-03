import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import ReportReview from './ReportReview.vue'

it('shows exact evidence, model audit provenance and coverage without executing report text', () => {
  const wrapper = mount(ReportReview, { props: { assessment: {
    saved_status: 'completed', requires_review: true, coverage: { matched_assertions: 1 },
    limitations: ['Only explicit trace claims are checked.'], issues: [
      { message: 'Count conflicts', claim_text: '<img src=x onerror=alert(1)>', evidence: [
        { reference: 'twitter:trace:11', agent_name: 'Maya Chen', round_num: 1, origin: 'model_action' }
      ] }, { message: 'Premise unverified', origin: 'proposal_model_audit', claim_id: 'claim_08' }
    ]
  } } })
  expect(wrapper.text()).toContain('Needs review')
  expect(wrapper.text()).toContain('twitter:trace:11 · Maya Chen · Round 1 · model_action')
  expect(wrapper.text()).toContain('not an independent truth judgment')
  expect(wrapper.text()).toContain('No general truth or completeness certification')
  expect(wrapper.find('img').exists()).toBe(false)
})

it('does not display a passing truth score when there are no matched assertions', () => {
  const wrapper = mount(ReportReview, { props: { assessment: { requires_review: false, issues: [], coverage: {}, limitations: [] } } })
  expect(wrapper.text()).toContain('Limited checks')
  expect(wrapper.text()).toContain('0 explicit assertions checked')
})

import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import ReportView from './ReportView.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { reportId: 'report_test' }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../api/graph', () => ({ getProject: vi.fn(), getGraphData: vi.fn() }))
vi.mock('../api/report', () => ({ getReport: vi.fn().mockResolvedValue({ success: false }) }))

let wrapper
afterEach(() => wrapper?.unmount())

it.each(['interrupted', 'failed', 'cancelled', 'stale'])('reflects the child %s state in the page header', async status => {
  wrapper = mount(ReportView, { global: { stubs: {
    GraphPanel: true,
    Step4Report: { template: '<div />', mounted() { this.$emit('update-status', status) } },
  } } })
  await flushPromises()
  expect(wrapper.get('.status-indicator').text()).toBe(status[0].toUpperCase() + status.slice(1))
})

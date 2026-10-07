import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HistoryDatabase from './HistoryDatabase.vue'
import { getSimulationHistory } from '../api/simulation'
vi.mock('../api/simulation', () => ({ getSimulationHistory: vi.fn() }))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }), useRoute: () => ({ path: '/' }) }))
beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} })
})
describe('history states', () => {
  it('makes an empty successful response explicit', async () => {
    getSimulationHistory.mockResolvedValue({ success: true, data: [] })
    const wrapper = mount(HistoryDatabase)
    await flushPromises()
    expect(wrapper.text()).toContain('No simulation records yet')
    wrapper.unmount()
  })
  it('shows a failed request and retries without relabelling it as empty', async () => {
    getSimulationHistory.mockRejectedValueOnce(new Error('synthetic unavailable'))
      .mockResolvedValueOnce({ success: true, data: [] })
    const wrapper = mount(HistoryDatabase)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Unable to load simulation records')
    expect(wrapper.text()).not.toContain('No simulation records yet')
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(getSimulationHistory).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('No simulation records yet')
    wrapper.unmount()
  })
})

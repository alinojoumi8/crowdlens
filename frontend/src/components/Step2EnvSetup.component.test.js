import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step2EnvSetup from './Step2EnvSetup.vue'
import { prepareSimulation, getPrepareStatus, getSimulationProfilesRealtime } from '../api/simulation'
vi.mock('../api/simulation', () => ({
  prepareSimulation: vi.fn(), getPrepareStatus: vi.fn(),
  getSimulationProfilesRealtime: vi.fn(), getSimulationConfig: vi.fn(),
  getSimulationConfigRealtime: vi.fn()
}))
vi.mock('../api/market', () => ({ resolveMarketTarget: vi.fn(), getMarketStatus: vi.fn() }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.clearAllMocks() })
it('refresh resumes preparation monitoring without admitting another generation', async () => {
  vi.useFakeTimers({toFake: ['setInterval','clearInterval']})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'processing',task_id:'task_existing',progress:25}})
  getSimulationProfilesRealtime.mockResolvedValue({success:true,data:{profiles:[],total_expected:6}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_existing',systemLogs:[]}})
  await flushPromises()
  expect(wrapper.text()).not.toContain('Prepare environment →')
  expect(wrapper.emitted('add-log').flat().join(' ')).toContain('Resumed monitoring')
  await vi.advanceTimersByTimeAsync(3000)
  expect(getPrepareStatus).toHaveBeenCalledWith({simulation_id:'sim_existing',task_id:'task_existing'})
  expect(getSimulationProfilesRealtime.mock.calls.length).toBeGreaterThan(1)
  expect(prepareSimulation).not.toHaveBeenCalled()
})

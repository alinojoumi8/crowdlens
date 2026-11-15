import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import SimulationView from './SimulationView.vue'
import { closeSimulationEnv, stopSimulation } from '../api/simulation'

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { simulationId: 'sim_test' }, query: {} }),
  useRouter: () => ({ push: vi.fn() }),
}))
vi.mock('../api/graph', () => ({ getProject: vi.fn(), getGraphData: vi.fn() }))
vi.mock('../api/simulation', () => ({
  getSimulation: vi.fn().mockResolvedValue({ success: true, data: { status: 'running' } }),
  getSimulationConfig: vi.fn(),
  getEnvStatus: vi.fn().mockResolvedValue({ success: true, data: { env_alive: true } }),
  closeSimulationEnv: vi.fn().mockResolvedValue({ success: true }),
  stopSimulation: vi.fn().mockResolvedValue({ success: true }),
}))

let wrapper
const open = () => mount(SimulationView, {
  props: { simulationId: 'sim_test' },
  global: { stubs: { GraphPanel: true, Step2EnvSetup: true } },
})
beforeEach(() => vi.clearAllMocks())
afterEach(() => { wrapper?.unmount(); vi.unstubAllGlobals() })

it('keeps a running simulation when the user does not confirm the stop', async () => {
  const confirm = vi.fn(() => false)
  vi.stubGlobal('confirm', confirm)
  wrapper = open()
  await flushPromises()
  expect(confirm).toHaveBeenCalledOnce()
  expect(closeSimulationEnv).not.toHaveBeenCalled()
  expect(stopSimulation).not.toHaveBeenCalled()
})

it('stops a running simulation after the user confirms', async () => {
  vi.stubGlobal('confirm', vi.fn(() => true))
  wrapper = open()
  await flushPromises()
  expect(closeSimulationEnv).toHaveBeenCalledWith({ simulation_id: 'sim_test', timeout: 10 })
})

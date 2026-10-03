import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step3Simulation from './Step3Simulation.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import { runEnsemble, startSimulation, stopSimulation, getRunStatus } from '../api/simulation'

vi.mock('vue-router', () => ({ useRoute:()=>({params:{simulationId:'sim_test'},query:{}}),useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../api/graph',()=>({getProject:vi.fn(),getGraphData:vi.fn()}))
vi.mock('../api/report', () => ({ generateReport: vi.fn() }))
vi.mock('../api/simulation', () => ({
  startSimulation: vi.fn().mockResolvedValue({ success: true, data: {} }),
  stopSimulation: vi.fn().mockResolvedValue({ success: true }),
  getRunStatus: vi.fn().mockResolvedValue({ success: false }),
  getSimulationConfig: vi.fn().mockResolvedValue({ success: true, data: { prediction_settings: { platform: 'twitter', memory_mode: 'off', seed: 42 } } }),
  getRunStatusDetail: vi.fn().mockResolvedValue({ success: false }),
  getRunDiagnostics: vi.fn().mockResolvedValue({ success: false }),
  getEconomySummary: vi.fn().mockResolvedValue({ success: false }),
  getEconomyEvents: vi.fn().mockResolvedValue({ success: false }),
  runEnsemble: vi.fn().mockResolvedValue({ success: true, data: { task_id: 'task_ensemble' } }),
  getEnsembleStatus: vi.fn(),
  getDiagnosticsExportUrl: vi.fn()
  ,getSimulation:vi.fn().mockResolvedValue({success:false}),getEnvStatus:vi.fn(),closeSimulationEnv:vi.fn()
}))

let wrapper
afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
})

it('opening or refreshing a simulation does not schedule generation', async () => {
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test' } })
  await flushPromises()
  expect(startSimulation).not.toHaveBeenCalled()
  expect(getRunStatus).toHaveBeenCalledWith('sim_test')
})

it('the simulation page header reflects the stopped child state',async()=>{
  wrapper=mount(SimulationRunView,{global:{stubs:{GraphPanel:true,Step3Simulation:{template:'<div />',mounted(){this.$emit('update-status','stopped')}}}}})
  await flushPromises()
  expect(wrapper.get('.status-indicator').text()).toBe('Stopped')
})

it('shows a usable Stop control and preserves the stopped state', async () => {
  getRunStatus.mockResolvedValueOnce({ success: true, data: { runner_status: 'running' } })
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test' } })
  await flushPromises()
  await wrapper.get('button.stop').trigger('click')
  await flushPromises()
  expect(stopSimulation).toHaveBeenCalledWith({ simulation_id: 'sim_test' })
  expect(wrapper.emitted('update-status').flat()).toContain('stopped')
})

it('passes the selected round cap and economic settings when running an ensemble', async () => {
  wrapper = mount(Step3Simulation, {
    props: {
      simulationId: 'sim_test',
      maxRounds: 17,
      ensembleRuns: 3,
      runtimeMode: 'realistic',
      economySettings: { enabled: true, initial_balance_cents: 2500, currency: 'CAD', max_decisions_per_tick: 8 }
    }
  })
  await flushPromises()
  await wrapper.get('button.ensemble').trigger('click')
  await flushPromises()
  expect(runEnsemble).toHaveBeenCalledWith({
    simulation_id: 'sim_test',
    runs: 3,
    max_rounds: 17,
    economy: { enabled: true, initial_balance_cents: 2500, currency: 'CAD', max_decisions_per_tick: 8 },
    enable_graph_memory_update: true
  })
})

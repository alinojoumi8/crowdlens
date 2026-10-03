import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step3Simulation from './Step3Simulation.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import { runEnsemble, startSimulation, stopSimulation, getRunStatus, getSimulationConfig, getRunStatusDetail } from '../api/simulation'

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
  vi.useRealTimers()
  vi.clearAllMocks()
})

it('retains detail accounting when a basic terminal poll omits the fields', async () => {
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
  getRunStatus.mockResolvedValueOnce({ success: true, data: { runner_status: 'running' } })
    .mockResolvedValueOnce({ success: true, data: { runner_status: 'completed' } })
  getRunStatusDetail.mockResolvedValueOnce({ success: true, data: {
    all_actions: [], activity_summary: { model_actions: 2, unique_posts: 9, initial_posts: 4, scheduled_posts: 4, logged_entries: 14, unknown_origin_actions: 0 },
    platform_activity: { twitter: { model_actions: 2 } },
  } })
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test' } })
  await flushPromises()
  await vi.advanceTimersByTimeAsync(2000)
  await flushPromises()
  expect(wrapper.get('.platform-status.twitter').text()).toContain('MODEL ACTIONS2')
  expect(wrapper.get('.activity-accounting').text()).toContain('9 unique posts')
})

it('opening or refreshing a simulation does not schedule generation', async () => {
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test' } })
  await flushPromises()
  expect(startSimulation).not.toHaveBeenCalled()
  expect(getRunStatus).toHaveBeenCalledWith('sim_test')
})

it('shows the selected platform and duration-derived bound before Start', async () => {
  getSimulationConfig.mockResolvedValueOnce({ success: true, data: {
    prediction_settings: { platform: 'twitter', memory_mode: 'off' },
    time_config: { total_simulation_hours: 2, minutes_per_round: 60 },
  } })
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test', maxRounds: 72 } })
  await flushPromises()
  expect(wrapper.find('.platform-status.reddit').exists()).toBe(false)
  expect(wrapper.get('.effective-settings').text()).toContain('effective rounds 2')
  expect(wrapper.get('.platform-status.runtime').text()).toContain('idle')
})

it('distinguishes model actions and unique posts from input entries', async () => {
  getRunStatus.mockResolvedValueOnce({ success: true, data: {
    runner_status: 'completed', twitter_actions_count: 18,
    activity_summary: { logged_entries: 14, unique_posts: 9, model_actions: 2, initial_posts: 4, scheduled_posts: 4, unknown_origin_actions: 0 },
    platform_activity: { twitter: { model_actions: 2, unique_posts: 9 } },
  } })
  wrapper = mount(Step3Simulation, { props: { simulationId: 'sim_test' } })
  await flushPromises()
  expect(wrapper.get('.platform-status.twitter').text()).toContain('MODEL ACTIONS2')
  expect(wrapper.get('.activity-accounting').text()).toContain('9 unique posts')
  expect(wrapper.get('.activity-accounting').text()).toContain('4 initial')
  expect(wrapper.get('.activity-accounting').text()).toContain('4 scheduled')
})

it('the simulation page header is idle before Start', async () => {
  wrapper = mount(SimulationRunView, { global: { stubs: { GraphPanel: true, Step3Simulation: true } } })
  await flushPromises()
  expect(wrapper.get('.status-indicator').text()).toBe('Idle')
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

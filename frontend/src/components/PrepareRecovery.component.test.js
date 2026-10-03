import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step2 from './Step2EnvSetup.vue'
import { prepareSimulation, getSimulationConfigRealtime } from '../api/simulation'
vi.mock('vue-router',()=>({useRouter:()=>({push:vi.fn()})}))
vi.mock('../api/graph',()=>({getGraphData:vi.fn().mockResolvedValue({success:false})}))
vi.mock('../api/simulation',()=>({
  getPrepareStatus:vi.fn().mockResolvedValue({success:true,data:{status:'ready',already_prepared:true}}),
  prepareSimulation:vi.fn().mockResolvedValue({success:true,data:{already_prepared:true}}),
  getSimulationProfiles:vi.fn().mockResolvedValue({success:true,data:{profiles:[]}}),
  getSimulationProfilesRealtime:vi.fn().mockResolvedValue({success:true,data:{profiles:[]}}),
  getSimulationConfig:vi.fn(),getSimulation:vi.fn(),
  getSimulationConfigRealtime:vi.fn().mockResolvedValue({success:true,data:{config_generated:true,config:{
    time_config:{total_simulation_hours:2,minutes_per_round:60},prediction_settings:{agent_count:4,simulation_duration:2,minutes_per_round:60,active_agents_per_round:1}
  }}}),getTaskStatus:vi.fn()
}))
let wrapper
afterEach(()=>{wrapper?.unmount();vi.clearAllMocks()})
it('opening a prepared environment reads saved settings without generation',async()=>{
  wrapper=mount(Step2,{props:{simulationId:'sim_prepared'}})
  await flushPromises()
  expect(prepareSimulation).not.toHaveBeenCalled()
  expect(getSimulationConfigRealtime).toHaveBeenCalledWith('sim_prepared')
})
it('shows two automatic rounds and clamps a custom cap to the actual configuration',async()=>{
  wrapper=mount(Step2,{props:{simulationId:'sim_prepared'}})
  await flushPromises()
  expect(wrapper.get('.auto-value .val-num').text()).toBe('2')
  await wrapper.get('.switch-control input').setValue(true)
  expect(wrapper.get('input[type="range"]').attributes('max')).toBe('2')
  expect(Number(wrapper.get('input[type="range"]').element.value)).toBeLessThanOrEqual(2)
})
it('reopens numeric controls from persisted effective settings',async()=>{
  wrapper=mount(Step2,{props:{simulationId:'sim_prepared'}})
  await flushPromises()
  const agents=wrapper.findAll('label').find(label=>label.text().trim()==='Agents')
  expect(agents.get('input').element.value).toBe('4')
})

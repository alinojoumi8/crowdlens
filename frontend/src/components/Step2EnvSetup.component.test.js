import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step2EnvSetup from './Step2EnvSetup.vue'
import { prepareSimulation, getSimulation, getPrepareStatus, getSimulationProfilesRealtime } from '../api/simulation'
vi.mock('../api/simulation', () => ({
  prepareSimulation: vi.fn(), getSimulation: vi.fn(), getPrepareStatus: vi.fn(),
  getSimulationProfilesRealtime: vi.fn(), getSimulationConfig: vi.fn(),
  getSimulationConfigRealtime: vi.fn()
}))
vi.mock('../api/market', () => ({ resolveMarketTarget: vi.fn(), getMarketStatus: vi.fn() }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.clearAllMocks() })
it('refresh resumes preparation monitoring without admitting another generation', async () => {
  vi.useFakeTimers({toFake: ['setInterval','clearInterval']})
  getSimulation.mockResolvedValue({success:true,data:{prediction_settings:{agent_count:6},participant_selection:{selected_by_type:{Plaintiff:1,Defendant:1},warnings:[]}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'processing',task_id:'task_existing',progress:25}})
  getSimulationProfilesRealtime.mockResolvedValue({success:true,data:{profiles:[],total_expected:6}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_existing',systemLogs:[]}})
  await flushPromises()
  expect(wrapper.text()).not.toContain('Prepare environment →')
  expect(wrapper.get('section[aria-label="Participant coverage"]').text()).toContain('Plaintiff: 1')
  expect(wrapper.get('section[aria-label="Participant coverage"]').text()).toContain('Defendant: 1')
  expect(wrapper.findAll('label').find(label => label.find('.forecast-label').exists() && label.find('.forecast-label').text() === 'Agents').get('input').element.value).toBe('6')
  expect(wrapper.emitted('add-log').flat().join(' ')).toContain('Resumed monitoring')
  await vi.advanceTimersByTimeAsync(3000)
  expect(getPrepareStatus).toHaveBeenCalledWith({simulation_id:'sim_existing',task_id:'task_existing'})
  expect(getSimulationProfilesRealtime.mock.calls.length).toBeGreaterThan(1)
  expect(prepareSimulation).not.toHaveBeenCalled()
})

it('sends an exact four-person roster including the shop owner and restores it on reload', async () => {
  const ids = ['maya','leo','priya','daniel']
  getSimulation.mockResolvedValue({success:true,data:{prediction_settings:{agent_count:4,participant_ids:ids}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  prepareSimulation.mockResolvedValue({success:false,error:'fixture stops before generation'})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_roster',systemLogs:[],graphData:{nodes:[
    {uuid:'city',name:'Cedarbrook',labels:['Entity','MunicipalGovernment']},
    ...ids.map(uuid => ({uuid,name:uuid,labels:['Entity',uuid==='leo'?'RetailBusinessOwner':'Person']}))
  ]}}})
  await flushPromises()
  const select = wrapper.get('select[aria-label="Specific participants"]')
  expect([...select.element.selectedOptions].map(option=>option.value).sort()).toEqual([...ids].sort())
  const button = wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  await button.trigger('click'); await flushPromises()
  expect(prepareSimulation).toHaveBeenCalledWith(expect.objectContaining({participant_ids:ids,
    prediction_settings:expect.objectContaining({agent_count:4,participant_ids:ids})}))
})

it('blocks preparation when an exact selection exceeds the cap or conflicts with type filters', async () => {
  getSimulation.mockResolvedValue({success:true,data:{prediction_settings:{agent_count:1,participant_ids:['one','two']}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_roster',systemLogs:[],graphData:{nodes:[
    {uuid:'one',name:'Same name',labels:['Entity','Person']},
    {uuid:'two',name:'Same name',labels:['Entity','Owner']}
  ]}}})
  await flushPromises()
  const button=wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  expect(button.attributes('disabled')).toBeDefined()
  expect(wrapper.get('[role="alert"]').text()).toContain('exceeds')
  await wrapper.get('select[aria-label="Specific participants"]').setValue(['two'])
  await wrapper.get('select[aria-label="Agent types"]').setValue(['Person'])
  expect(button.attributes('disabled')).toBeDefined()
  expect(wrapper.get('[role="alert"]').text()).toContain('excluded')
  await button.trigger('click')
  expect(prepareSimulation).not.toHaveBeenCalled()
})

it('allows an explicit participant when the type filter matches a secondary label', async () => {
  getSimulation.mockResolvedValue({success:true,data:{prediction_settings:{agent_count:4,participant_ids:['leo'],entity_types_include:['RetailBusinessOwner']}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  prepareSimulation.mockResolvedValue({success:false,error:'fixture stops before generation'})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_roster',systemLogs:[],graphData:{nodes:[
    {uuid:'leo',name:'Leo',labels:['Entity','Person','RetailBusinessOwner']}
  ]}}})
  await flushPromises()
  const button=wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  expect(button.attributes('disabled')).toBeUndefined()
  await button.trigger('click'); await flushPromises()
  expect(prepareSimulation).toHaveBeenCalledWith(expect.objectContaining({participant_ids:['leo'],
    prediction_settings:expect.objectContaining({entity_types_include:['RetailBusinessOwner']})}))
})

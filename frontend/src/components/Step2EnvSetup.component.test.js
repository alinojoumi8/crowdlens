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

it('restores and submits the explicit smoke activation mode without starting a run', async () => {
  getSimulation.mockResolvedValue({success:true,data:{prediction_settings:{activation_mode:'smoke_round_robin'}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  prepareSimulation.mockResolvedValue({success:false,error:'fixture stops before generation'})
  wrapper=mount(Step2EnvSetup,{props:{simulationId:'sim_smoke',systemLogs:[]}})
  await flushPromises()
  expect(wrapper.get('select[aria-label="Activation mode"]').element.value).toBe('smoke_round_robin')
  expect(wrapper.text()).toContain('not a realistic activity sample')
  await wrapper.findAll('button').find(b=>b.text()==='Prepare environment →').trigger('click')
  await flushPromises()
  expect(prepareSimulation).toHaveBeenCalledWith(expect.objectContaining({prediction_settings:expect.objectContaining({activation_mode:'smoke_round_robin'})}))
})

const fieldSelect = (w, name) => w.findAll('label').find(label => label.find('.forecast-label').exists() && label.find('.forecast-label').text() === name).get('select')

it('restores a preset legal report default as General prediction for a general-mode run', async () => {
  getSimulation.mockResolvedValue({success:true,data:{forecast_mode:'general',prediction_settings:{report_mode:'litigation_case'}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_general',systemLogs:[]}})
  await flushPromises()
  expect(fieldSelect(wrapper,'Report').element.value).toBe('prediction')
})

it('restores the same preset default as Legal case for a legal-mode run', async () => {
  getSimulation.mockResolvedValue({success:true,data:{forecast_mode:'legal_case',prediction_settings:{report_mode:'litigation_case'}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_legal',systemLogs:[]}})
  await flushPromises()
  expect(fieldSelect(wrapper,'Report').element.value).toBe('legal_case')
})

it('keeps an explicit report choice on reload and follows the Mode when the user changes it', async () => {
  getSimulation.mockResolvedValue({success:true,data:{forecast_mode:'general',prediction_settings:{report_mode:'product_risk'}}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_choice',systemLogs:[]}})
  await flushPromises()
  expect(fieldSelect(wrapper,'Report').element.value).toBe('product_risk')
  await fieldSelect(wrapper,'Mode').setValue('market_economy')
  expect(fieldSelect(wrapper,'Report').element.value).toBe('market_prediction')
  await fieldSelect(wrapper,'Mode').setValue('general')
  expect(fieldSelect(wrapper,'Report').element.value).toBe('prediction')
})

it('names presets by size, not by legal use', async () => {
  getSimulation.mockResolvedValue({success:true,data:{}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_names',systemLogs:[]}})
  await flushPromises()
  const labels = fieldSelect(wrapper,'Preset').findAll('option').map(option => option.text())
  expect(labels).toEqual(['Quick', 'Standard', 'Deep'])
})

it('explains a preparation stopped by the workflow time allowance', async () => {
  vi.useFakeTimers({toFake: ['setInterval','clearInterval']})
  getSimulation.mockResolvedValue({success:true,data:{}})
  getPrepareStatus.mockResolvedValueOnce({success:true,data:{status:'processing',task_id:'task_limit',progress:25}})
    .mockResolvedValue({success:true,data:{status:'failed',error:'runtime_limit'}})
  getSimulationProfilesRealtime.mockResolvedValue({success:true,data:{profiles:[],total_expected:48}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_limit',systemLogs:[]}})
  await flushPromises()
  await vi.advanceTimersByTimeAsync(3000)
  const logs = wrapper.emitted('add-log').flat().join(' ')
  expect(logs).toContain('time allowance ran out')
  expect(logs).toContain('Renew')
  // After the allowance is renewed, the user can submit preparation again.
  prepareSimulation.mockResolvedValue({success:true,data:{task_id:'task_retry'}})
  const button = wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  expect(button).toBeTruthy()
  await button.trigger('click'); await flushPromises()
  expect(prepareSimulation).toHaveBeenCalledTimes(1)
})

it('shows Prepare again when the prepare request itself is rejected by the allowance', async () => {
  getSimulation.mockResolvedValue({success:true,data:{}})
  getPrepareStatus.mockResolvedValue({success:true,data:{status:'not_started'}})
  prepareSimulation.mockRejectedValueOnce(new Error('runtime_limit'))
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_rejected',systemLogs:[]}})
  await flushPromises()
  const prepare = () => wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  await prepare().trigger('click'); await flushPromises()
  expect(wrapper.emitted('add-log').flat().join(' ')).toContain('time allowance ran out')
  expect(prepare()).toBeTruthy()
})

it('ignores a late status answer about an older preparation task', async () => {
  vi.useFakeTimers({toFake: ['setInterval','clearInterval']})
  let answerOldPoll
  getSimulation.mockResolvedValue({success:true,data:{}})
  getPrepareStatus
    .mockResolvedValueOnce({success:true,data:{status:'processing',task_id:'task_old',progress:25}})
    .mockImplementationOnce(() => new Promise(resolve => { answerOldPoll = resolve }))
    .mockResolvedValueOnce({success:true,data:{status:'failed',error:'runtime_limit'}})
    .mockResolvedValue({success:true,data:{status:'processing',task_id:'task_new',progress:5}})
  getSimulationProfilesRealtime.mockResolvedValue({success:true,data:{profiles:[],total_expected:48}})
  prepareSimulation.mockResolvedValue({success:true,data:{task_id:'task_new'}})
  wrapper = mount(Step2EnvSetup,{props:{simulationId:'sim_race',systemLogs:[]}})
  await flushPromises()
  await vi.advanceTimersByTimeAsync(3000)
  const prepare = () => wrapper.findAll('button').find(b=>b.text()==='Prepare environment →')
  await prepare().trigger('click'); await flushPromises()
  expect(prepare()).toBeFalsy()
  answerOldPoll({success:true,data:{status:'failed',error:'runtime_limit'}})
  await flushPromises()
  // The new task keeps running: the old failure does not reopen Prepare.
  expect(prepare()).toBeFalsy()
})

import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import WorkflowControls from './WorkflowControls.vue'
import { authorizeWorkflow, getExecutionConfiguration, getWorkflow, reauthorizeWorkflow, stopWorkflow } from '../api/execution'
vi.mock('../api/execution', () => ({
  getExecutionConfiguration: vi.fn().mockResolvedValue({success:true,data:{provider:'synthetic',model:'synthetic',controls_available:true,configured:true}}),
  authorizeWorkflow: vi.fn(), resolveWorkflow:vi.fn().mockResolvedValue({data:{workflow_id:null}}),
  getWorkflow:vi.fn(), stopWorkflow:vi.fn(), reauthorizeWorkflow:vi.fn()
}))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks(); vi.useRealTimers() })
it('uses administrator pricing without offering client price controls', async () => {
  getExecutionConfiguration.mockResolvedValueOnce({data:{provider:'synthetic',model:'synthetic',controls_available:true,configured:true,quotas:{managed:true,admission_open:true}}})
  authorizeWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_managed',state:'authorized',admitted:0,max_requests:60,in_flight:0}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,inputDescription:'fictional',inputFingerprint:'abc'}})
  await flushPromises()
  expect(wrapper.text()).toContain('Shared quotas and pricing are controlled by the administrator')
  expect(wrapper.find('.spend-toggle').exists()).toBe(false)
  await wrapper.get('button').trigger('click')
  await flushPromises()
  expect(authorizeWorkflow).toHaveBeenCalled()
  expect(authorizeWorkflow.mock.calls[0][0]).not.toHaveProperty('spend')
})
it('explains that a shared limit cannot be reset by renewal', async () => {
  authorizeWorkflow.mockRejectedValueOnce({response:{data:{error:'quota_daily_requests_limit'}}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,inputDescription:'fictional',inputFingerprint:'abc'}})
  await flushPromises()
  await wrapper.get('button').trigger('click')
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Starting or renewing a workflow does not reset shared usage')
})
it('withdraws parent start permission when a shared quota closes', async () => {
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_paused',state:'authorized',admission_closed:false,
    admitted:0,max_requests:60,in_flight:0,quotas:{managed:true,admission_open:false,reason:'quota_admission_closed'}}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,pendingId:'wf_paused'}})
  await flushPromises()
  expect(wrapper.emitted('authorized').at(-1)).toEqual([null])
  expect(wrapper.text()).toContain('New work is paused by the administrator')
})
it.each(['stopped', 'runtime_limit', 'request_limit', 'spend_limit', undefined])('does not grant parent start permission for state %s without an admission flag', async state => {
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_not_startable',state,
    admitted:0,max_requests:60,in_flight:0,quotas:{managed:true,admission_open:true}}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,pendingId:'wf_not_startable'}})
  await flushPromises()
  expect(wrapper.emitted('authorized').at(-1)).toEqual([null])
})
it('grants parent start permission only for an authorized workflow with open admission', async () => {
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_startable',state:'authorized',admission_closed:false,
    admitted:0,max_requests:60,in_flight:0,quotas:{managed:true,admission_open:true}}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,pendingId:'wf_startable'}})
  await flushPromises()
  expect(wrapper.emitted('authorized').at(-1)).toEqual(['wf_startable'])
})
it('ignores authorization for an input that changed while the response was delayed', async () => {
  let resolve
  authorizeWorkflow.mockReturnValue(new Promise(done => { resolve = done }))
  wrapper = mount(WorkflowControls, { props:{authorize:true,inputDescription:'original fictional input',inputFingerprint:'abc'} })
  await flushPromises()
  await wrapper.get('button').trigger('click')
  await wrapper.setProps({ inputDescription:'changed fictional input',inputFingerprint:'def' })
  resolve({data:{workflow_id:'wf_old',state:'authorized',admitted:0,max_requests:60,in_flight:0,elapsed_seconds:0}})
  await flushPromises()
  expect(wrapper.emitted('authorized')?.flat() || []).not.toContain('wf_old')
})

it('explains a server configuration blocker before authorization', async () => {
  getExecutionConfiguration.mockResolvedValueOnce({data:{provider:'synthetic',model:'synthetic',controls_available:true,configured:true,authorization_blocker:'secondary_provider_allowance_unsupported'}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,inputDescription:'PDF input',inputFingerprint:'abc'}})
  await flushPromises()
  expect(wrapper.get('button').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('optional Jev provider modes are enabled')
  expect(authorizeWorkflow).not.toHaveBeenCalled()
})
it('shows the actionable server reason for HTTP 400 instead of the status message', async () => {
  authorizeWorkflow.mockRejectedValueOnce({message:'Request failed with status code 400',response:{data:{error:'secondary_provider_allowance_unsupported'}}})
  wrapper = mount(WorkflowControls, {props:{authorize:true,inputDescription:'Website input',inputFingerprint:'abc'}})
  await flushPromises()
  await wrapper.get('button').trigger('click')
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('optional Jev provider modes are enabled')
  expect(wrapper.text()).not.toContain('Request failed with status code 400')
})

it('renews an expired allowance only on an explicit click without starting generation', async () => {
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_old',state:'runtime_limit',admission_closed:true,admitted:39,max_requests:60,in_flight:0,provider:'minimax',model:'MiniMax-M3'}})
  reauthorizeWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_old',state:'authorized',admission_closed:false,admitted:39,max_requests:60,in_flight:0}})
  wrapper=mount(WorkflowControls,{props:{pendingId:'wf_old'}})
  await flushPromises()
  expect(reauthorizeWorkflow).not.toHaveBeenCalled()
  await wrapper.findAll('button').find(button=>button.text()==='Renew workflow allowance').trigger('click')
  await flushPromises()
  expect(reauthorizeWorkflow).toHaveBeenCalledWith('wf_old',expect.objectContaining({confirmed:true,max_requests:60,max_seconds:1800,acknowledge_unknown:false}))
  expect(wrapper.text()).not.toContain('Renew workflow allowance')
  expect(wrapper.emitted('authorized')).toBeUndefined()
})
it('requires acknowledgment before renewing outstanding provider requests',async()=>{
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_unknown',state:'runtime_limit',admission_closed:true,admitted:3,max_requests:60,in_flight:1}})
  wrapper=mount(WorkflowControls,{props:{pendingId:'wf_unknown'}})
  await flushPromises()
  expect(wrapper.findAll('button').find(button=>button.text()==='Renew workflow allowance').attributes('disabled')).toBeDefined()
  expect(reauthorizeWorkflow).not.toHaveBeenCalled()
})


it('clears a transient poll failure after recovery without hiding a failed stop', async () => {
  vi.useFakeTimers()
  const data = {workflow_id:'wf_recovery',state:'authorized',admitted:2,max_requests:60,in_flight:0,elapsed_seconds:2}
  getWorkflow.mockRejectedValueOnce(new Error('Temporary backend outage')).mockResolvedValue({data})
  wrapper = mount(WorkflowControls,{props:{pendingId:'wf_recovery'}})
  await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Temporary backend outage')
  await vi.advanceTimersByTimeAsync(2000); await flushPromises()
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  stopWorkflow.mockRejectedValueOnce(new Error('Stop was not confirmed'))
  await wrapper.findAll('button').find(button=>button.text()==='Stop workflow').trigger('click'); await flushPromises()
  await vi.advanceTimersByTimeAsync(2000); await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('Stop was not confirmed')
})

const allowanceProps = {authorize:true,inputDescription:'fictional packet',inputFingerprint:'abc'}
const priceFields = ['1.00', '0.10', '1.25', '10', 'Fictional rates v1']
const fillPrices = async () => {
  await wrapper.get('.spend-toggle input').setValue(true)
  for (const [index, input] of wrapper.findAll('fieldset input').entries()) await input.setValue(priceFields[index])
}
it('requires explicit prices and submits exact decimal terms without assumed model prices', async () => {
  authorizeWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_budget',state:'authorized',admitted:0,max_requests:60,in_flight:0,elapsed_seconds:0}})
  wrapper = mount(WorkflowControls,{props:allowanceProps}); await flushPromises()
  await wrapper.get('.spend-toggle input').setValue(true)
  expect(wrapper.get('button').attributes('disabled')).toBeDefined()
  expect(wrapper.findAll('fieldset input').every(input => input.element.value === '')).toBe(true)
  await fillPrices()
  await wrapper.get('button').trigger('click'); await flushPromises()
  expect(authorizeWorkflow).toHaveBeenCalledWith(expect.objectContaining({spend:{currency:'USD',budget_usd:'1.00',reserve_usd:'0.10',input_usd_per_million:'1.25',output_usd_per_million:'10',price_reference:'Fictional rates v1'}}))
  expect(wrapper.text()).toContain('cannot cap the provider invoice')
})

it('discards delayed authorization after its spending terms change', async () => {
  let resolve
  authorizeWorkflow.mockReturnValueOnce(new Promise(done => {resolve = done}))
  wrapper = mount(WorkflowControls,{props:allowanceProps}); await flushPromises(); await fillPrices()
  await wrapper.get('button').trigger('click')
  // A programmatic change also invalidates an outstanding request snapshot.
  await wrapper.findAll('fieldset input')[0].setValue('2')
  resolve({data:{workflow_id:'wf_old_price',state:'authorized'}}); await flushPromises()
  expect(wrapper.emitted('authorized')?.flat() || []).not.toContain('wf_old_price')
})

it('shows unresolved money after reload and requires a sufficient total budget for renewal', async () => {
  const spend = {budget_micro_usd:100000, reserve_micro_usd:50000, estimated_micro_usd:10000,
    reserved_micro_usd:50000, available_micro_usd:40000, input_rate_micro_usd:1250000,
    output_rate_micro_usd:10000000, unpriced_attempts:1, overrun_attempts:0, price_reference:'Fictional v1'}
  getWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_spend',state:'spend_limit',admission_closed:true,reason:'spend_limit',admitted:2,max_requests:60,in_flight:0,elapsed_seconds:1,spend}})
  reauthorizeWorkflow.mockResolvedValueOnce({data:{workflow_id:'wf_spend',state:'authorized',admission_closed:false,admitted:2,max_requests:60,in_flight:0,spend}})
  wrapper = mount(WorkflowControls,{props:{pendingId:'wf_spend'}}); await flushPromises()
  expect(wrapper.text()).toContain('Reserved for unresolved usage: $0.05')
  expect(wrapper.text()).toContain('Actual provider billing is unknown')
  const button = wrapper.findAll('button').find(b => b.text()==='Renew workflow allowance')
  expect(button.attributes('disabled')).toBeDefined()
  const label = wrapper.findAll('label').find(l => l.text().includes('Total USD budget'))
  await label.get('input').setValue('0.20')
  await button.trigger('click'); await flushPromises()
  expect(reauthorizeWorkflow).toHaveBeenCalledWith('wf_spend',expect.objectContaining({budget_usd:'0.20'}))
})

it.each([
  { in_flight: 0, unknown_usage_attempts: 1 },
  { in_flight: 2, unknown_usage_attempts: 3 },
  { in_flight: 0, unknown_usage_attempts: 0 }
])('shows separate outstanding and unknown-usage counts: %j', async counts => {
  getWorkflow.mockResolvedValueOnce({ data: { workflow_id: 'wf_counts', state: 'stopped',
    admitted: 39, max_requests: 60, elapsed_seconds: 100, ...counts } })
  wrapper = mount(WorkflowControls, { props: { pendingId: 'wf_counts' } })
  await flushPromises()
  expect(wrapper.text()).toContain(`${counts.in_flight} in flight · ${counts.unknown_usage_attempts} with unknown token usage`)
  expect(wrapper.text()).not.toContain('in flight or delivery unknown')
  expect(wrapper.text().includes('Unknown token usage can include in-flight requests')).toBe(counts.unknown_usage_attempts > 0)
  expect(authorizeWorkflow).not.toHaveBeenCalled()
  expect(reauthorizeWorkflow).not.toHaveBeenCalled()
  expect(stopWorkflow).not.toHaveBeenCalled()
})

it('does not present an omitted unknown-usage count as zero', async () => {
  getWorkflow.mockResolvedValueOnce({ data: { workflow_id: 'wf_legacy', state: 'stopped',
    admitted: 39, max_requests: 60, elapsed_seconds: 100, in_flight: 0 } })
  wrapper = mount(WorkflowControls, { props: { pendingId: 'wf_legacy' } })
  await flushPromises()
  expect(wrapper.text()).toContain('Unknown token usage count not reported')
})

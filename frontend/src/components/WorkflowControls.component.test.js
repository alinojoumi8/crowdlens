import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import WorkflowControls from './WorkflowControls.vue'
import { authorizeWorkflow, getExecutionConfiguration, getWorkflow, reauthorizeWorkflow } from '../api/execution'
vi.mock('../api/execution', () => ({
  getExecutionConfiguration: vi.fn().mockResolvedValue({success:true,data:{provider:'synthetic',model:'synthetic',controls_available:true,configured:true}}),
  authorizeWorkflow: vi.fn(), resolveWorkflow:vi.fn().mockResolvedValue({data:{workflow_id:null}}),
  getWorkflow:vi.fn(), stopWorkflow:vi.fn(), reauthorizeWorkflow:vi.fn()
}))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
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

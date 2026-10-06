import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import WorkflowControls from './WorkflowControls.vue'
import { authorizeWorkflow, getExecutionConfiguration } from '../api/execution'
vi.mock('../api/execution', () => ({
  getExecutionConfiguration: vi.fn().mockResolvedValue({success:true,data:{provider:'synthetic',model:'synthetic',controls_available:true,configured:true}}),
  authorizeWorkflow: vi.fn(), resolveWorkflow:vi.fn().mockResolvedValue({data:{workflow_id:null}}),
  getWorkflow:vi.fn(), stopWorkflow:vi.fn()
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

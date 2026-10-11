import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi, afterEach } from 'vitest'
import SystemReadiness from './SystemReadiness.vue'
import service from '../api'
vi.mock('../api', () => ({ default: { get: vi.fn() } }))
let wrapper
const status = { readiness: 'ready', llm: {model:'model-x',state:'reachable',message:'Configured model is listed. Inference has not been tested.'}, embedding:{model:'local-embedding',state:'reachable',message:'Model listed.'},neo4j:{healthy:true},control_db:{healthy:true},disk:{areas:[{name:'uploads',free_bytes:1024**3*20,message:'Storage write check passed.'}]}}
afterEach(() => { wrapper?.unmount(); vi.clearAllMocks() })
it('shows metadata readiness without claiming inference success', async () => {
  service.get.mockResolvedValue({data:status}); wrapper=mount(SystemReadiness);await flushPromises()
  expect(wrapper.text()).toContain('Checks passed')
  expect(wrapper.text()).toContain('Inference has not been tested')
  expect(wrapper.text()).toContain('20.0 GiB free')
  expect(service.get).toHaveBeenCalledOnce()
})
it('shows low space and missing-model details', async () => {
  service.get.mockResolvedValue({data:{...status,readiness:'unavailable',llm:{state:'missing_model',message:'Configured model is absent.'},disk:{areas:[{name:'uploads',free_bytes:100,message:'Storage is nearly full.'}]}}})
  wrapper=mount(SystemReadiness);await flushPromises()
  expect(wrapper.text()).toContain('Needs attention'); expect(wrapper.text()).toContain('missing model');expect(wrapper.text()).toContain('Storage is nearly full')
})
it('clears stale healthy state after a failed refresh', async () => {
  service.get.mockResolvedValueOnce({data:status}).mockRejectedValueOnce(new Error('offline'))
  wrapper=mount(SystemReadiness);await flushPromises();await wrapper.get('button').trigger('click');await flushPromises()
  expect(wrapper.text()).toContain('Readiness unknown');expect(wrapper.text()).not.toContain('Checks passed');expect(wrapper.find('[role=alert]').exists()).toBe(true)
})
it('keeps unsupported checks unverified', async () => {
  service.get.mockResolvedValue({data:{...status,readiness:'unverified',llm:{state:'unverified',message:'Metadata unsupported.'}}})
  wrapper=mount(SystemReadiness);await flushPromises();expect(wrapper.text()).toContain('Readiness unverified')
})

import { mount,flushPromises } from '@vue/test-utils'
import { afterEach,expect,it,vi } from 'vitest'
import CaseDetail from './CaseDetailView.vue'
import { setPendingUpload } from '../store/pendingUpload'
vi.mock('vue-router',()=>({useRouter:()=>({push:vi.fn()})}))
vi.mock('../api/graph',()=>({getCase:vi.fn().mockResolvedValue({success:true,data:{name:'Fixture',simulation_requirement:'fictional goal',versions:[]}})}))
vi.mock('../store/pendingUpload',()=>({setPendingUpload:vi.fn()}))
vi.mock('../utils/workflowInput',()=>({workflowInputFingerprint:vi.fn().mockResolvedValue('fixture-hash')}))
let wrapper
afterEach(()=>{wrapper?.unmount();vi.clearAllMocks()})
it('requires input-bound authorization for adding a case version and forwards its ID',async()=>{
  wrapper=mount(CaseDetail,{props:{caseId:'case_fixture'},global:{stubs:{WorkflowControls:{props:['inputFingerprint'],template:'<button class="authorize-fixture" @click="$emit(\'authorized\',\'wf_fixture\')">Fixture authorization</button>'}}}})
  await flushPromises()
  await wrapper.findAll('button').find(b=>b.text().includes('Add version')).trigger('click')
  const input=wrapper.get('input[type="file"]')
  const file=new File(['fictional'],'fixture.md',{type:'text/markdown'})
  Object.defineProperty(input.element,'files',{value:[file]})
  await input.trigger('change');await flushPromises()
  const build=wrapper.findAll('button').find(b=>b.text()==='Build version')
  expect(build.attributes('disabled')).toBeDefined()
  expect(wrapper.findComponent({name:'WorkflowControls'}).exists()||wrapper.find('.authorize-fixture').exists()).toBe(true)
  await wrapper.get('.authorize-fixture').trigger('click')
  await build.trigger('click');await flushPromises()
  expect(setPendingUpload).toHaveBeenCalledWith([file],'fictional goal',[],'case_fixture','wf_fixture')
})

import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step4Report from './Step4Report.vue'
import { getReport, getReportProgress, generateReport, resumeReport } from '../api/report'

vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }), useRouter: () => ({ push: vi.fn() }) }))
vi.mock('../api/report', () => ({
  getReport: vi.fn().mockResolvedValue({success: true, data: {status: 'interrupted'}}),
  getReportProgress: vi.fn().mockResolvedValue({success:true, data: {status:'interrupted', effective_status:'interrupted', terminal:true, reason:'request_limit'}}),
  getAgentLog: vi.fn().mockResolvedValue({success:true, data:{logs:[], from_line:0}}),
  getConsoleLog: vi.fn().mockResolvedValue({success:true, data:{logs:[], from_line:0}}),
  generateReport: vi.fn(), resumeReport: vi.fn(), regenerateReportSection: vi.fn()
}))
vi.mock('../api/graph', () => ({ benchmarkGraphEmbeddings: vi.fn(), getGraphQuality: vi.fn(), reembedGraph: vi.fn() }))
let wrapper
afterEach(() => { wrapper?.unmount(); vi.useRealTimers(); vi.clearAllMocks() })
it('ends terminal report polling and never restarts on open', async () => {
  vi.useFakeTimers()
  wrapper = mount(Step4Report, { props: { reportId:'report_interrupted', systemLogs:[] },
    global: { stubs: { EvidenceDraftReview:true, ClaimEvidence:true, SafeMarkdown:true } } })
  await flushPromises()
  const reads = getReportProgress.mock.calls.length
  await vi.advanceTimersByTimeAsync(10000)
  await flushPromises()
  expect(getReportProgress).toHaveBeenCalledTimes(reads)
  expect(generateReport).not.toHaveBeenCalled()
  expect(resumeReport).not.toHaveBeenCalled()
  expect(wrapper.emitted('update-status').flat()).not.toContain('completed')
})
it('an explicit resume restarts polling after an interrupted snapshot', async () => {
  vi.useFakeTimers()
  getReport.mockResolvedValue({success:true,data:{status:'interrupted',outline:{title:'Partial',summary:'Fictional fixture',sections:[]}}})
  wrapper = mount(Step4Report, { props: { reportId:'report_interrupted', systemLogs:[] },
    global: { stubs: { EvidenceDraftReview:true, ClaimEvidence:true, SafeMarkdown:true } } })
  await flushPromises()
  resumeReport.mockResolvedValue({success:true,data:{task_id:'replacement'}})
  getReportProgress.mockResolvedValue({success:true,data:{status:'queued',effective_status:'queued',terminal:false}})
  getReport.mockResolvedValueOnce({success:true,data:{status:'interrupted'}})
  const button=wrapper.findAll('button').find(item=>item.text()==='Resume failed section')
  await button.trigger('click');await flushPromises()
  getReport.mockResolvedValue({success:true,data:{status:'generating'}})
  getReportProgress.mockResolvedValue({success:true,data:{status:'generating',effective_status:'generating',terminal:false}})
  const reads=getReportProgress.mock.calls.length
  await vi.advanceTimersByTimeAsync(6000);await flushPromises()
  expect(getReportProgress.mock.calls.length).toBeGreaterThan(reads)
  expect(resumeReport).toHaveBeenCalledTimes(1)
})

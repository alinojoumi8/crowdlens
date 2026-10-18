import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step4Report from './Step4Report.vue'
import { getReport, getReportProgress, generateReport, resumeReport, getAgentLog } from '../api/report'

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

it('current review survives historical completed progress and never regenerates the report', async () => {
  vi.useFakeTimers()
  getAgentLog.mockResolvedValue({success:true,data:{logs:[{action:'report_complete'}],from_line:0}})
  getReport.mockResolvedValue({success:true,data:{status:'completed',outline:{title:'Retained report',summary:'',sections:[]},
    current_review:{requires_review:true,saved_status:'completed',issues:[],limitations:[],coverage:{}}}})
  getReportProgress.mockResolvedValue({success:true,data:{effective_status:'completed',terminal:true}})
  wrapper=mount(Step4Report,{props:{reportId:'report_retained',systemLogs:[]},global:{stubs:{EvidenceDraftReview:true,ClaimEvidence:true,SafeMarkdown:true}}})
  await flushPromises()
  expect(wrapper.text()).toContain('Current assessment · Needs review')
  expect(wrapper.emitted('update-status').flat()).toContain('needs-review')
  expect(wrapper.emitted('update-status').flat()).not.toContain('completed')
  expect(generateReport).not.toHaveBeenCalled()
  expect(resumeReport).not.toHaveBeenCalled()
})

it('evidence-only reports hide stale numeric payloads and retain choice on regenerate', async () => {
  vi.useFakeTimers()
  getReport.mockResolvedValue({success:true,data:{status:'needs_review',simulation_id:'sim_evidence',evidence_only:true,
    outline:{title:'Evidence Review',summary:'Attributed claims.',sections:[]},
    forecast:{probabilities:[{outcome:'Success',probability:0.9}]},
    source_grounding:{simulation_activity:{summary:{model_actions:8,model_written_actions:6,model_reactions:2,
      model_noops:0,model_failed_actions:0,unique_posts:13,initial_posts:3,scheduled_posts:7,scheduled_events:7,logged_entries:25,unknown_origin_actions:0}}}}})
  getReportProgress.mockResolvedValue({success:true,data:{effective_status:'needs_review',terminal:true}})
  generateReport.mockResolvedValue({success:true,data:{report_id:'report_new'}})
  wrapper=mount(Step4Report,{props:{reportId:'report_evidence',systemLogs:[]},global:{stubs:{EvidenceDraftReview:true,ClaimEvidence:true,SafeMarkdown:true}}})
  await flushPromises()
  expect(wrapper.find('.forecast-summary-panel').exists()).toBe(false)
  expect(wrapper.get('[aria-label="Activity accounting"]').text()).toContain('6 written posts/comments')
  expect(wrapper.get('[aria-label="Activity accounting"]').text()).toContain('7 scheduled-event records')
  const regenerate=wrapper.findAll('button').find(b=>b.text()==='Regenerate')
  await regenerate.trigger('click'); await flushPromises()
  expect(generateReport.mock.calls[0][0].evidence_only).toBe(true)
})

it('explicit evidence-only generation opts out without changing an old report', async () => {
  vi.useFakeTimers()
  getReport.mockResolvedValue({success:true,data:{status:'needs_review',simulation_id:'sim_old',
    outline:{title:'Old report',summary:'',sections:[]},forecast:{probabilities:[{outcome:'Scenario A',probability:0.416}]}}})
  getReportProgress.mockResolvedValue({success:true,data:{effective_status:'needs_review',terminal:true}})
  generateReport.mockResolvedValue({success:true,data:{report_id:'report_new'}})
  wrapper=mount(Step4Report,{props:{reportId:'report_old',systemLogs:[]},global:{stubs:{EvidenceDraftReview:true,ClaimEvidence:true,SafeMarkdown:true}}})
  await flushPromises()
  expect(wrapper.find('.forecast-summary-panel').exists()).toBe(true)
  const button=wrapper.findAll('button').find(b=>b.text()==='Generate evidence-only report')
  await button.trigger('click'); await flushPromises()
  expect(generateReport.mock.calls[0][0]).toMatchObject({simulation_id:'sim_old',evidence_only:true,disable_interviews:true,force_regenerate:true})
})

it('passes raw section text to summary matching without the rendered heading', async () => {
  getReport.mockResolvedValue({ success: true, data: { status: 'needs_review', outline: {
    title: 'Synthetic report', summary: 'Original section. Protected text.',
    sections: [{ title: 'Section heading', content: 'Original section.' }]
  } } })
  getReportProgress.mockResolvedValue({ success: true, data: { effective_status: 'needs_review', terminal: true } })
  wrapper = mount(Step4Report, { props: { reportId: 'report_raw_section', systemLogs: [] },
    global: { stubs: { EvidenceDraftReview: true, ClaimEvidence: true, SafeMarkdown: true } } })
  await flushPromises()
  expect(wrapper.findComponent({ name: 'EvidenceDraftReview' }).props('sectionText')).toBe('Original section.')
})

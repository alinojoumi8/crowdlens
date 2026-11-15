import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import Step5Interaction from './Step5Interaction.vue'
import { chatWithReport, getReport } from '../api/report'

vi.mock('../api/report', () => ({
  chatWithReport: vi.fn(),
  getReport: vi.fn().mockRejectedValue(new Error('Network Error')),
  getAgentLog: vi.fn().mockResolvedValue({ success: true, data: { logs: [] } }),
}))
vi.mock('../api/simulation', () => ({
  interviewAgents: vi.fn(),
  getSimulationProfilesRealtime: vi.fn().mockResolvedValue({ success: true, data: { profiles: [] } }),
}))

let wrapper
afterEach(() => wrapper?.unmount())

it('shows a load failure on the page, not only in the hidden log', async () => {
  wrapper = mount(Step5Interaction, {
    props: { reportId: 'report_test', simulationId: 'sim_test' },
    global: { stubs: { SafeMarkdown: true } },
  })
  await flushPromises()
  expect(wrapper.get('[role="alert"].action-error').text()).toContain('Failed to load report: Network Error')
})

it('keeps the conversation target while a reply is pending', async () => {
  getReport.mockResolvedValue({ success: true, data: {} })
  let reply
  chatWithReport.mockReturnValue(new Promise(resolve => { reply = resolve }))
  wrapper = mount(Step5Interaction, {
    props: { reportId: 'report_test', simulationId: 'sim_test' },
    global: { stubs: { SafeMarkdown: true } },
  })
  await flushPromises()
  wrapper.vm.chatInput = 'What changed?'
  wrapper.vm.sendMessage()
  await flushPromises()

  wrapper.vm.selectAgent({ username: 'persona' }, 3)
  wrapper.vm.selectSurveyTab()
  await flushPromises()

  expect(wrapper.vm.chatTarget).toBe('report_agent')
  expect(wrapper.vm.activeTab).toBe('chat')
  expect(wrapper.get('[role="alert"].action-error').text()).toContain('Wait for the current reply')
  reply({ success: true, data: { response: 'Answer' } })
  await flushPromises()
  wrapper.vm.selectSurveyTab()
  expect(wrapper.vm.activeTab).toBe('survey')
})

it('does not carry the Report Agent conversation to a different report', async () => {
  getReport.mockResolvedValue({ success: true, data: {} })
  chatWithReport.mockResolvedValue({ success: true, data: { response: 'Answer about report A' } })
  wrapper = mount(Step5Interaction, {
    props: { reportId: 'report_a', simulationId: 'sim_test' },
    global: { stubs: { SafeMarkdown: true } },
  })
  await flushPromises()
  wrapper.vm.chatInput = 'Question about report A'
  await wrapper.vm.sendMessage()
  await flushPromises()
  expect(wrapper.vm.chatHistory.length).toBe(2)

  await wrapper.setProps({ reportId: 'report_b' })
  await flushPromises()

  expect(wrapper.vm.chatHistory).toEqual([])
  expect(wrapper.vm.chatHistoryCache.report_agent).toBeUndefined()
})

it.each(['reply', 'error'])('discards a pending Report Agent %s when the report changes', async outcome => {
  getReport.mockResolvedValue({ success: true, data: {} })
  let resolveReply
  let rejectReply
  chatWithReport.mockReturnValue(new Promise((resolve, reject) => {
    resolveReply = resolve
    rejectReply = reject
  }))
  wrapper = mount(Step5Interaction, {
    props: { reportId: 'report_a', simulationId: 'sim_test' },
    global: { stubs: { SafeMarkdown: true } },
  })
  await flushPromises()
  wrapper.vm.chatInput = 'Question about report A'
  const sending = wrapper.vm.sendMessage()
  await wrapper.setProps({ reportId: 'report_b' })

  if (outcome === 'reply') {
    resolveReply({ success: true, data: { response: 'Answer about report A' } })
  } else {
    rejectReply(new Error('Request failed for report A'))
  }
  await sending

  expect(wrapper.vm.chatHistory).toEqual([])
  expect(wrapper.vm.chatHistoryCache.report_agent).toBeUndefined()
  expect(wrapper.vm.isSending).toBe(false)
})

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

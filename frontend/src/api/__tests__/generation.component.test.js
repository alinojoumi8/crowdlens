import { expect, it, vi } from 'vitest'
const { service } = vi.hoisted(() => {
  const service = vi.fn().mockRejectedValue(new Error('injected response loss'))
  service.post = vi.fn().mockRejectedValue(new Error('injected response loss'))
  return { service }
})
vi.mock('../index', () => ({ default: service, requestWithRetry: async operation => {
  try { return await operation() } catch { return operation() }
} }))
import { startSimulation, prepareSimulation, interviewAgents } from '../simulation'
import { generateOntology, buildGraph } from '../graph'
import { resumeReport, regenerateReportSection } from '../report'
it.each([startSimulation, prepareSimulation, interviewAgents, generateOntology, buildGraph, resumeReport, regenerateReportSection].map(operation => [operation]))(
  'does not silently repeat a generation request without an idempotency key', async operation => {
    service.mockClear(); service.post.mockClear()
    await expect(operation({ simulation_id: 'synthetic' })).rejects.toThrow('injected response loss')
    expect(service.mock.calls.length + service.post.mock.calls.length).toBe(1)
  })

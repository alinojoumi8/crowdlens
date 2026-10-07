import { beforeEach, describe, expect, it, vi } from 'vitest'
const { post } = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('../index', () => ({
  default: { post },
  requestWithRetry: async operation => {
    try { return await operation() } catch { return operation() }
  },
}))
import { generateReport } from '../report'

describe('root report request identity', () => {
  beforeEach(() => vi.clearAllMocks())
  it('reuses one nonempty key and payload after a lost response', async () => {
    post.mockRejectedValueOnce(new Error('response lost')).mockResolvedValue({ success: true })
    const input = { simulation_id: 'sim_synthetic', force_regenerate: true }
    await generateReport(input)
    const first = post.mock.calls[0][1]
    expect(first.request_key).toMatch(/^[A-Za-z0-9_.:-]{1,128}$/)
    expect(post.mock.calls[1][1]).toBe(first)
    expect(input.request_key).toBeUndefined()
  })
  it('preserves an explicit key and allocates a fresh one for a new manual invocation', async () => {
    post.mockResolvedValue({ success: true })
    await generateReport({ simulation_id: 'sim_synthetic', request_key: 'retry-owned-key' })
    expect(post.mock.calls[0][1].request_key).toBe('retry-owned-key')
    await generateReport({ simulation_id: 'sim_synthetic' })
    await generateReport({ simulation_id: 'sim_synthetic' })
    expect(post.mock.calls[1][1].request_key).toBeTruthy()
    expect(post.mock.calls[2][1].request_key).not.toBe(post.mock.calls[1][1].request_key)
  })
})

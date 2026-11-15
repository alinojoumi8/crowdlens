import { expect, it, vi } from 'vitest'
import { requestWithRetry } from '../index'
import * as graph from '../graph'

// No request may leave the test: the HTTP client is a local fake.
vi.mock('axios', () => {
  const service = vi.fn().mockResolvedValue({ success: true })
  service.interceptors = { request: { use: vi.fn() }, response: { use: vi.fn() } }
  return { default: { create: () => service } }
})

const failure = status => Object.assign(new Error('failed'), { response: { status } })

it('does not repeat a request the server refused', async () => {
  const request = vi.fn().mockRejectedValue(failure(400))
  await expect(requestWithRetry(request, 3, 0)).rejects.toThrow('failed')
  expect(request).toHaveBeenCalledOnce()
})

it.each([undefined, 429, 503])('repeats a transient failure (status %s)', async status => {
  const request = vi.fn().mockRejectedValueOnce(status ? failure(status) : new Error('Network Error')).mockResolvedValue('ok')
  await expect(requestWithRetry(request, 3, 0)).resolves.toBe('ok')
  expect(request).toHaveBeenCalledTimes(2)
})

it('addDocumentsToCase can run (its retry helper is imported)', async () => {
  await expect(graph.addDocumentsToCase('case_1', new FormData())).resolves.toEqual({ success: true })
})

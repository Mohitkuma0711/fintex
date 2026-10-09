import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, clearApiResponseCache, setApiAccessTokenProvider } from './api'

describe('API session cache', () => {
  beforeEach(() => {
    clearApiResponseCache()
    setApiAccessTokenProvider(async () => null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('uses a successful GET response after a network failure and announces stale data', async () => {
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockRejectedValueOnce(new TypeError('offline')))

    await expect(apiRequest<{ status: string }>('/health')).resolves.toEqual({ status: 'ok' })
    await expect(apiRequest<{ status: string }>('/health')).resolves.toEqual({ status: 'ok' })
    expect(dispatchSpy).toHaveBeenCalledWith(expect.objectContaining({
      type: 'fintax:offline-fallback',
    }))
  })

  it('does not replay a cached GET result across a successful mutation', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: 'before' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockRejectedValueOnce(new TypeError('offline'))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/profile')
    await apiRequest('/profile', { method: 'PUT', body: '{}' })
    await expect(apiRequest('/profile')).rejects.toMatchObject({ status: 0 })
  })
})

import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiFetch, ApiError } from './client'

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response)
}

afterEach(() => { vi.restoreAllMocks() })

describe('apiFetch', () => {
  it('returns parsed JSON on 200', async () => {
    vi.stubGlobal('fetch', mockFetch(200, { id: 1, name: 'Ana' }))
    const data = await apiFetch<{ id: number }>('/api/patients/1')
    expect(data.id).toBe(1)
  })

  it('sends credentials and JSON body on writes', async () => {
    const f = mockFetch(201, { ok: true })
    vi.stubGlobal('fetch', f)
    await apiFetch('/api/patients', { method: 'POST', body: { name: 'Ana' } })
    expect(f).toHaveBeenCalledWith('/api/patients', expect.objectContaining({
      method: 'POST',
      credentials: 'include',
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ name: 'Ana' }),
    }))
  })

  it('throws ApiError with status and body on non-2xx', async () => {
    vi.stubGlobal('fetch', mockFetch(401, { detail: 'Not authenticated' }))
    await expect(apiFetch('/api/patients', { method: 'POST', body: {} }))
      .rejects.toMatchObject({ status: 401 })
  })

  it('maps 422 validation errors to field errors', async () => {
    const body = { detail: [{ loc: ['body', 'name'], msg: 'must not be blank', type: 'value_error' }] }
    vi.stubGlobal('fetch', mockFetch(422, body))
    try {
      await apiFetch('/api/patients', { method: 'POST', body: {} })
      throw new Error('should have thrown')
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError)
      expect((e as ApiError).fieldErrors()).toEqual({ name: 'must not be blank' })
    }
  })
})

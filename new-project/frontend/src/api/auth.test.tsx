import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useMe } from './auth'

afterEach(() => { vi.restoreAllMocks() })

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe('useMe', () => {
  it('fetches /api/me', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ is_admin: true }),
    } as Response))
    const { result } = renderHook(() => useMe(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({ is_admin: true })
    expect(fetch).toHaveBeenCalledWith('/api/me', expect.objectContaining({ credentials: 'include' }))
  })
})

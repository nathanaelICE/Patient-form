import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePatients } from './patients'

afterEach(() => { vi.restoreAllMocks() })

function wrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

describe('usePatients', () => {
  it('fetches the patient list', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => [{ id: 1, name: 'Ana' }],
    } as Response))
    const { result } = renderHook(() => usePatients(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toHaveLength(1)
    expect(fetch).toHaveBeenCalledWith('/api/patients', expect.objectContaining({ credentials: 'include' }))
  })
})

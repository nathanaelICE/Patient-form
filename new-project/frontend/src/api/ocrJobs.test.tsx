import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'
import { useOcrJobs } from './ocrJobs'

afterEach(() => vi.restoreAllMocks())

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useOcrJobs', () => {
  it('fetches the job list', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => [{ id: 1, filename: 'a.png', status: 'processing', error_message: null, extracted_fields: null, created_at: '2026-07-03T00:00:00' }],
    } as Response))
    const { result } = renderHook(() => useOcrJobs(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.data?.[0].filename).toBe('a.png'))
  })
})

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch, ApiError } from './client'
import type { OcrJob } from './types'

function isActive(jobs: OcrJob[] | undefined): boolean {
  return !!jobs?.some((j) => j.status === 'pending' || j.status === 'processing')
}

export function useOcrJobs(enabled = true) {
  return useQuery({
    queryKey: ['ocrJobs'],
    queryFn: () => apiFetch<OcrJob[]>('/api/ocr/jobs'),
    enabled,
    refetchInterval: (query) => (isActive(query.state.data as OcrJob[] | undefined) ? 2000 : false),
  })
}

export function useUploadOcrJobs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (files: File[]) => {
      const form = new FormData()
      for (const f of files) form.append('files', f)
      const res = await fetch('/api/ocr/jobs', { method: 'POST', credentials: 'include', body: form })
      let parsed: unknown = null
      try { parsed = await res.json() } catch { parsed = null }
      if (!res.ok) throw new ApiError(res.status, parsed)
      return parsed as OcrJob[]
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ocrJobs'] }),
  })
}

export function useRetryOcrJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<OcrJob>(`/api/ocr/jobs/${id}/retry`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ocrJobs'] }),
  })
}

export function useDismissOcrJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/ocr/jobs/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ocrJobs'] })
      qc.invalidateQueries({ queryKey: ['patients'] })
    },
  })
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { Me } from './types'

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: () => apiFetch<Me>('/api/me') })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { username: string; password: string }) =>
      apiFetch<{ ok: boolean }>('/api/login', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<{ ok: boolean }>('/api/logout', { method: 'POST', body: {} }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

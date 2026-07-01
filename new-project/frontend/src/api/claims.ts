import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { Claim, ClaimCreate, ClaimUpdate } from './types'

export function useClaims(patientId: number) {
  return useQuery({
    queryKey: ['claims', patientId],
    queryFn: () => apiFetch<Claim[]>(`/api/patients/${patientId}/claims`),
    enabled: Number.isFinite(patientId),
  })
}

export function useCreateClaim(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ClaimCreate) =>
      apiFetch<Claim>(`/api/patients/${patientId}/claims`, { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}

export function useUpdateClaim(patientId: number, claimId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ClaimUpdate) =>
      apiFetch<Claim>(`/api/patients/${patientId}/claims/${claimId}`, { method: 'PUT', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}

export function useDeleteClaim(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (claimId: number) =>
      apiFetch<void>(`/api/patients/${patientId}/claims/${claimId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['claims', patientId] }),
  })
}

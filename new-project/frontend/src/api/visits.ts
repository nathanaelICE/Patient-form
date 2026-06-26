import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { Visit, VisitCreate, VisitUpdate } from './types'

export function useVisits(patientId: number) {
  return useQuery({
    queryKey: ['visits', patientId],
    queryFn: () => apiFetch<Visit[]>(`/api/patients/${patientId}/visits`),
    enabled: Number.isFinite(patientId),
  })
}

export function useCreateVisit(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: VisitCreate) =>
      apiFetch<Visit>(`/api/patients/${patientId}/visits`, { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['visits', patientId] }),
  })
}

export function useUpdateVisit(patientId: number, visitId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: VisitUpdate) =>
      apiFetch<Visit>(`/api/patients/${patientId}/visits/${visitId}`, { method: 'PUT', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['visits', patientId] }),
  })
}

export function useDeleteVisit(patientId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (visitId: number) =>
      apiFetch<void>(`/api/patients/${patientId}/visits/${visitId}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['visits', patientId] }),
  })
}

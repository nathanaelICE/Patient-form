import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { Patient, PatientCreate, PatientUpdate } from './types'

export function usePatients() {
  return useQuery({ queryKey: ['patients'], queryFn: () => apiFetch<Patient[]>('/api/patients') })
}

export function usePatient(id: number) {
  return useQuery({
    queryKey: ['patient', id],
    queryFn: () => apiFetch<Patient>(`/api/patients/${id}`),
    enabled: Number.isFinite(id),
  })
}

export function useCreatePatient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PatientCreate) => apiFetch<Patient>('/api/patients', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['patients'] }),
  })
}

export function useUpdatePatient(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PatientUpdate) => apiFetch<Patient>(`/api/patients/${id}`, { method: 'PUT', body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['patients'] })
      qc.invalidateQueries({ queryKey: ['patient', id] })
    },
  })
}

export function useDeletePatient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<void>(`/api/patients/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['patients'] }),
  })
}

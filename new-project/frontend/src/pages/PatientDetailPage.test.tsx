import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders } from '../test-utils'
import PatientDetailPage from './PatientDetailPage'
import { AuthContext } from '../auth/AuthContext'

afterEach(() => { vi.restoreAllMocks() })

describe('PatientDetailPage', () => {
  it('shows patient name and visits', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url === '/api/patients/1') return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 1, name: 'Ana', date_of_birth: '1990-01-01', gender: 'female', phone: null, created_at: 'x' }) } as Response)
      if (url === '/api/patients/1/visits') return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 5, patient_id: 1, date: '2026-01-02', chief_complaint: 'Cough', diagnosis: null, notes: null, created_at: 'x' }] } as Response)
      if (url === '/api/patients/1/claims') return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      return Promise.reject(new Error('unexpected url ' + url))
    }))
    renderWithProviders(
      <AuthContext.Provider value={{ isAdmin: false, isLoading: false }}>
        <Routes><Route path="/patients/:id" element={<PatientDetailPage />} /></Routes>
      </AuthContext.Provider>,
      { route: '/patients/1' },
    )
    await waitFor(() => expect(screen.getByText('Ana')).toBeInTheDocument())
    expect(screen.getByText('Cough')).toBeInTheDocument()
  })

  it('shows claims section with claim data', async () => {
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url === '/api/patients/1') return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 1, name: 'Ana', date_of_birth: '1990-01-01', gender: 'female', phone: null, created_at: 'x' }) } as Response)
      if (url === '/api/patients/1/visits') return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url === '/api/patients/1/claims') return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 10, patient_id: 1, claim_date: '2026-03-15', claim_type: 'outpatient', claim_amount: 250.00, claim_status: 'pending', claim_submission_method: 'online', created_at: 'x' }] } as Response)
      return Promise.reject(new Error('unexpected url ' + url))
    }))
    renderWithProviders(
      <AuthContext.Provider value={{ isAdmin: false, isLoading: false }}>
        <Routes><Route path="/patients/:id" element={<PatientDetailPage />} /></Routes>
      </AuthContext.Provider>,
      { route: '/patients/1' },
    )
    expect(await screen.findByRole('heading', { name: /claims/i })).toBeInTheDocument()
    const matches = await screen.findAllByText(/outpatient/i)
    expect(matches.length).toBeGreaterThan(0)
  })
})

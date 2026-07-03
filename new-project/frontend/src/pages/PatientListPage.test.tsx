import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test-utils'
import PatientListPage from './PatientListPage'
import { AuthContext } from '../auth/AuthContext'

afterEach(() => { vi.restoreAllMocks() })

describe('PatientListPage', () => {
  it('renders fetched patients', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => [{ id: 1, name: 'Ana', date_of_birth: '1990-01-01', gender: 'female', phone: null, created_at: '2026-01-01T00:00:00' }],
    } as Response))
    renderWithProviders(
      <AuthContext.Provider value={{ isAdmin: false, isLoading: false }}>
        <PatientListPage />
      </AuthContext.Provider>,
      { route: '/patients' },
    )
    await waitFor(() => expect(screen.getByText('Ana')).toBeInTheDocument())
  })

  it('renders processing rows at top and error rows at bottom', async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url.includes('/api/ocr/status')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ available: true }) } as Response)
      if (url.includes('/api/ocr/jobs')) return Promise.resolve({ ok: true, status: 200, json: async () => [
        { id: 10, filename: 'scan1.png', status: 'processing', error_message: null, extracted_fields: null, created_at: '2026-07-03T00:00:00' },
        { id: 11, filename: 'scan2.png', status: 'error', error_message: 'could not read document', extracted_fields: null, created_at: '2026-07-03T00:00:01' },
      ] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [
        { id: 1, name: 'Ana', date_of_birth: '1990-01-01', gender: 'female', phone: null, created_at: '2026-01-01T00:00:00' },
      ] } as Response)
    })
    vi.stubGlobal('fetch', fetchMock)

    renderWithProviders(
      <AuthContext.Provider value={{ isAdmin: true, isLoading: false }}>
        <PatientListPage />
      </AuthContext.Provider>,
      { route: '/patients' },
    )

    await waitFor(() => expect(screen.getByText('scan1.png')).toBeInTheDocument())
    expect(screen.getByText(/Processing/i)).toBeInTheDocument()
    expect(screen.getByText('ERROR')).toBeInTheDocument()

    const rows = screen.getAllByRole('row').map((r) => r.textContent || '')
    const processingIdx = rows.findIndex((t) => t.includes('scan1.png'))
    const patientIdx = rows.findIndex((t) => t.includes('Ana'))
    const errorIdx = rows.findIndex((t) => t.includes('scan2.png'))
    expect(processingIdx).toBeLessThan(patientIdx)
    expect(patientIdx).toBeLessThan(errorIdx)
  })
})

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
})

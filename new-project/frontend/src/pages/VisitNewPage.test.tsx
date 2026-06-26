import { describe, it, expect, vi, afterEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Routes, Route } from 'react-router-dom'
import { renderWithProviders } from '../test-utils'
import VisitNewPage from './VisitNewPage'

afterEach(() => { vi.restoreAllMocks() })

describe('VisitNewPage', () => {
  it('renders validation errors from a 422', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 422,
      json: async () => ({ detail: [{ loc: ['body', 'chief_complaint'], msg: 'must not be blank', type: 'value_error' }] }),
    } as Response))
    renderWithProviders(
      <Routes><Route path="/patients/:id/visits/new" element={<VisitNewPage />} /></Routes>,
      { route: '/patients/1/visits/new' },
    )
    await userEvent.click(screen.getByRole('button', { name: /create/i }))
    await waitFor(() => expect(screen.getByText('must not be blank')).toBeInTheDocument())
  })
})

import { describe, it, expect } from 'vitest'
import { Routes, Route } from 'react-router-dom'
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../test-utils'
import ProtectedRoute from './ProtectedRoute'
import { AuthContext } from './AuthContext'

function renderAt(route: string, isAdmin: boolean) {
  return renderWithProviders(
    <AuthContext.Provider value={{ isAdmin, isLoading: false }}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/secret" element={<div>secret content</div>} />
        </Route>
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </AuthContext.Provider>,
    { route },
  )
}

describe('ProtectedRoute', () => {
  it('renders child when admin', () => {
    renderAt('/secret', true)
    expect(screen.getByText('secret content')).toBeInTheDocument()
  })
  it('redirects to login when not admin', () => {
    renderAt('/secret', false)
    expect(screen.getByText('login page')).toBeInTheDocument()
  })
})

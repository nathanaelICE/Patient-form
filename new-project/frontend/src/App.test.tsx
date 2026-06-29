import { describe, it, expect } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithProviders } from './test-utils'
import App from './App'
import { AuthContext } from './auth/AuthContext'

function renderAppAt(route: string, isAdmin: boolean) {
  return renderWithProviders(
    <AuthContext.Provider value={{ isAdmin, isLoading: false }}>
      <App />
    </AuthContext.Provider>,
    { route },
  )
}

describe('App route protection', () => {
  it('redirects unauthenticated visitors away from the patient list', () => {
    renderAppAt('/patients', false)
    expect(screen.getByText('Admin Login')).toBeInTheDocument()
  })

  it('redirects unauthenticated visitors away from a patient detail page', () => {
    renderAppAt('/patients/1', false)
    expect(screen.getByText('Admin Login')).toBeInTheDocument()
  })
})

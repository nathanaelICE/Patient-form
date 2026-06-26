import { screen } from '@testing-library/react'
import { renderWithProviders } from './test-utils'
import App from './App'

test('renders brand link', () => {
  renderWithProviders(<App />, { route: '/login' })
  expect(screen.getByText('Patient Registration')).toBeInTheDocument()
})

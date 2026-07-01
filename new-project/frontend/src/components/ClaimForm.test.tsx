import { describe, it, expect, vi } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { renderWithProviders } from '../test-utils'
import ClaimForm from './ClaimForm'

describe('ClaimForm', () => {
  it('submits entered claim values', () => {
    const onSubmit = vi.fn()
    renderWithProviders(<ClaimForm onSubmit={onSubmit} pending={false} />)

    fireEvent.change(screen.getByLabelText(/claim date/i), { target: { value: '2026-06-01' } })
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: '1200.5' } })
    fireEvent.change(screen.getByLabelText(/claim type/i), { target: { value: 'outpatient' } })
    fireEvent.change(screen.getByLabelText(/submission method/i), { target: { value: 'online' } })
    fireEvent.click(screen.getByRole('button', { name: /save|add|create/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        claim_date: '2026-06-01',
        claim_amount: 1200.5,
        claim_type: 'outpatient',
        claim_submission_method: 'online',
      })
    )
  })
})

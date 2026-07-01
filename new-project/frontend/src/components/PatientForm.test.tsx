import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import PatientForm from './PatientForm'

function renderForm(props = {}) {
  const onSubmit = vi.fn()
  render(
    <MemoryRouter>
      <PatientForm
        title="Register Patient"
        submitLabel="Create"
        pending={false}
        fieldErrors={{}}
        cancelTo="/patients"
        onSubmit={onSubmit}
        {...props}
      />
    </MemoryRouter>,
  )
  return { onSubmit }
}

describe('PatientForm new fields', () => {
  it('renders the OCR fields', () => {
    renderForm()
    expect(screen.getByLabelText(/National ID/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Blood Type/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Occupation/i)).toBeInTheDocument()
  })

  it('seeds fields from initial and submits them', async () => {
    const user = userEvent.setup()
    const { onSubmit } = renderForm({
      initial: {
        name: 'Budi',
        date_of_birth: '1990-05-15',
        gender: 'male',
        national_id: '3201234567890001',
        occupation: 'Teacher',
      },
    })
    await user.click(screen.getByRole('button', { name: 'Create' }))
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'Budi',
        national_id: '3201234567890001',
        occupation: 'Teacher',
      }),
    )
  })

  it('marks low-confidence fields', () => {
    renderForm({
      initial: { name: 'Budi', date_of_birth: '1990-05-15', gender: 'male', occupation: 'Teacher' },
      lowConfidence: { occupation: 0.3 },
    })
    expect(screen.getByLabelText(/Occupation/i).closest('.form-group')).toHaveClass('field-low-confidence')
  })
})

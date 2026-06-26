import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConfirmDialog from './ConfirmDialog'

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    const { container } = render(
      <ConfirmDialog open={false} title="Delete" message="Sure?" onConfirm={() => {}} onCancel={() => {}} />,
    )
    expect(container).toBeEmptyDOMElement()
  })
  it('calls onConfirm when confirmed', async () => {
    const onConfirm = vi.fn()
    render(<ConfirmDialog open title="Delete" message="Sure?" onConfirm={onConfirm} onCancel={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /confirm|delete/i }))
    expect(onConfirm).toHaveBeenCalled()
  })
})

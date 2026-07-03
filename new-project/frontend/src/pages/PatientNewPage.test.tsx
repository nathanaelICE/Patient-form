import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import PatientNewPage from './PatientNewPage'

const mockFetch = vi.fn()

beforeEach(() => {
  mockFetch.mockReset()
  vi.stubGlobal('fetch', mockFetch)
})

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PatientNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return Promise.resolve({ ok, status, json: () => Promise.resolve(body) } as Response)
}

afterEach(() => { vi.restoreAllMocks() })

it('prefills the form from router state', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ available: false }) } as Response))
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[{ pathname: '/patients/new', state: { prefill: { name: 'Budi Santoso' }, jobId: 5 } }]}>
        <PatientNewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  await waitFor(() => expect((screen.getByLabelText(/name/i) as HTMLInputElement).value).toBe('Budi Santoso'))
})

describe('PatientNewPage OCR', () => {
  it('shows the upload control when OCR is available', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: true })
      return jsonResponse({})
    })
    renderPage()
    expect(await screen.findByLabelText(/Upload form/i)).toBeInTheDocument()
  })

  it('hides the upload control when OCR is unavailable', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: false })
      return jsonResponse({})
    })
    renderPage()
    // status resolves, then the control is absent
    await waitFor(() => expect(mockFetch).toHaveBeenCalled())
    expect(screen.queryByLabelText(/Upload form/i)).not.toBeInTheDocument()
  })

  it('pre-fills the form from an extracted result', async () => {
    const user = userEvent.setup()
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/api/ocr/status')) return jsonResponse({ available: true })
      if (url.includes('/api/ocr/extract')) {
        return jsonResponse({
          fields: { name: 'Budi Santoso', occupation: 'Teacher' },
          confidence: { name: 0.95, occupation: 0.3 },
        })
      }
      return jsonResponse({})
    })
    renderPage()
    const input = await screen.findByLabelText(/Upload form/i)
    const file = new File([new Uint8Array([1, 2, 3])], 'form.png', { type: 'image/png' })
    await user.upload(input, file)
    await waitFor(() =>
      expect((screen.getByLabelText(/^Name/i) as HTMLInputElement).value).toBe('Budi Santoso'),
    )
    expect((screen.getByLabelText(/Occupation/i) as HTMLInputElement).value).toBe('Teacher')
  })
})

import { ApiError } from './client'
import type { PatientCreate } from './types'

export interface OcrResult {
  fields: Partial<PatientCreate>
  confidence: Record<string, number>
}

export async function getOcrStatus(): Promise<boolean> {
  const res = await fetch('/api/ocr/status', { credentials: 'include' })
  if (!res.ok) return false
  const body = await res.json()
  return Boolean(body.available)
}

export async function extractPatientForm(file: File): Promise<OcrResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/ocr/extract', {
    method: 'POST',
    credentials: 'include',
    body: form, // do NOT set Content-Type; the browser sets the multipart boundary
  })
  let parsed: unknown = null
  try {
    parsed = await res.json()
  } catch {
    parsed = null
  }
  if (!res.ok) throw new ApiError(res.status, parsed)
  return parsed as OcrResult
}

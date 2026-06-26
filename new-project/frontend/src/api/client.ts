import type { FieldError } from './types'

export class ApiError extends Error {
  status: number
  body: unknown
  constructor(status: number, body: unknown) {
    const detail = (body as { detail?: unknown })?.detail
    const msg = typeof detail === 'string' ? detail : `Request failed (${status})`
    super(msg)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
  /** Maps FastAPI 422 `detail` arrays to { fieldName: message }. */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {}
    const detail = (this.body as { detail?: unknown })?.detail
    if (Array.isArray(detail)) {
      for (const err of detail as FieldError[]) {
        const field = err.loc[err.loc.length - 1]
        if (typeof field === 'string') out[field] = err.msg
      }
    }
    return out
  }
}

export async function apiFetch<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const init: RequestInit = {
    method: options.method ?? 'GET',
    credentials: 'include',
  }
  if (options.body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(options.body)
  }
  const res = await fetch(path, init)
  if (res.status === 204) return undefined as T
  let parsed: unknown = null
  try {
    parsed = await res.json()
  } catch {
    parsed = null
  }
  if (!res.ok) throw new ApiError(res.status, parsed)
  return parsed as T
}

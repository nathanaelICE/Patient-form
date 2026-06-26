import { ApiError } from '../api/client'
export default function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null
  const msg = error instanceof ApiError ? error.message : 'Something went wrong'
  return <p className="form-error" role="alert" style={{ marginBottom: '1rem' }}>{msg}</p>
}

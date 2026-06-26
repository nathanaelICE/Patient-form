import { ApiError } from '../api/client'
export default function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null
  const msg = error instanceof ApiError ? error.message : 'Something went wrong'
  return <p className="error-banner" role="alert">{msg}</p>
}

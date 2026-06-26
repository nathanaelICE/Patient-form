import { FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useLogin } from '../api/auth'
import { ApiError } from '../api/client'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const login = useLogin()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next') ?? '/patients'

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await login.mutateAsync({ username, password })
      navigate(next.startsWith('/') ? next : '/patients', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    }
  }

  return (
    <form className="card form-card login-card" onSubmit={onSubmit}>
      <h2>Admin Login</h2>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-group">
        <label htmlFor="username">Username <span className="required">*</span></label>
        <input id="username" type="text" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
      </div>
      <div className="form-group">
        <label htmlFor="password">Password <span className="required">*</span></label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      <div className="modal-actions">
        <button type="submit" className="btn btn-primary" disabled={login.isPending}>Log In as Admin</button>
        <Link to="/patients" className="btn btn-secondary">Cancel</Link>
      </div>
    </form>
  )
}

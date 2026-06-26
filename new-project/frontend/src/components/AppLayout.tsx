import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLogout } from '../api/auth'

export default function AppLayout() {
  const { isAdmin } = useAuth()
  const logout = useLogout()
  return (
    <>
      <header className="app-header">
        <Link to="/patients" className="app-title">Patient Registration</Link>
        <div className="header-right">
          {isAdmin ? (
            <>
              <span className="admin-badge">Admin</span>
              <button className="btn btn-ghost" onClick={() => logout.mutate()}>Logout</button>
            </>
          ) : (
            <Link to="/login" className="btn btn-ghost">Login</Link>
          )}
        </div>
      </header>
      <main className="main-content">
        <Outlet />
      </main>
    </>
  )
}

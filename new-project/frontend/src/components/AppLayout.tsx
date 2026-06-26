import { Link, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useLogout } from '../api/auth'

export default function AppLayout() {
  const { isAdmin } = useAuth()
  const logout = useLogout()
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/patients" className="brand">Patient Registration</Link>
        <nav>
          {isAdmin ? (
            <button onClick={() => logout.mutate()}>Log out</button>
          ) : (
            <Link to="/login">Log in</Link>
          )}
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

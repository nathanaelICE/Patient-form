import { createContext, useContext, ReactNode } from 'react'
import { useMe } from '../api/auth'

interface AuthState { isAdmin: boolean; isLoading: boolean }

export const AuthContext = createContext<AuthState>({ isAdmin: false, isLoading: true })

export function AuthProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useMe()
  return (
    <AuthContext.Provider value={{ isAdmin: data?.is_admin ?? false, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

import { createContext, useCallback, useEffect, useMemo, useState } from 'react'
import { fetchCurrentUser, loginRequest, logoutRequest, registerRequest } from '../api/auth'
import { AUTH_EXPIRED_EVENT } from '../api/client'
import { clearToken, getToken, setToken } from '../utils/storage'

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // If a token is stored we must verify it before deciding what to render.
  const [loading, setLoading] = useState(() => Boolean(getToken()))
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    if (!getToken()) return undefined
    let cancelled = false
    fetchCurrentUser()
      .then((u) => !cancelled && setUser(u))
      .catch(() => clearToken()) // invalid/expired token: start logged out
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  // The Axios interceptor fires this when the server rejects our token mid-session.
  useEffect(() => {
    const onExpired = () => {
      setUser(null)
      setSessionExpired(true)
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired)
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired)
  }, [])

  const acceptSession = useCallback((data) => {
    setToken(data.access_token)
    setUser(data.user)
    setSessionExpired(false)
    return data.user
  }, [])

  const login = useCallback(
    async (email, password) => acceptSession(await loginRequest(email, password)),
    [acceptSession],
  )

  const register = useCallback(
    async (payload) => acceptSession(await registerRequest(payload)),
    [acceptSession],
  )

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } catch {
      /* the token is discarded locally either way */
    }
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, sessionExpired, login, register, logout }),
    [user, loading, sessionExpired, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

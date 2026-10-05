import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { homePathForRole } from '../utils/roles'

/**
 * Guards a group of routes.
 * - not logged in  -> /login (remembering where the user wanted to go)
 * - wrong role     -> redirected to their own dashboard
 * The backend enforces the same rules; this only improves the experience.
 */
export default function ProtectedRoute({ role }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return <p className="p-8 text-center text-slate-500">Loading…</p>
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (role && user.role !== role) {
    return <Navigate to={homePathForRole(user.role)} replace />
  }
  return <Outlet />
}

import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { homePathForRole } from '../utils/roles'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-6xl flex-wrap gap-y-2 items-center justify-between px-4 py-3">
        <Link to="/" className="text-lg font-semibold text-indigo-600">
          PlaceGenie AI
        </Link>
        <div className="flex items-center gap-4 text-sm">
          {user ? (
            <>
              <Link to={homePathForRole(user.role)} className="text-slate-700 hover:text-indigo-600">
                Dashboard
              </Link>
              {user.role === 'student' && (
                <>
                  <Link to="/student/recommendations" className="text-slate-700 hover:text-indigo-600">
                    Recommended
                  </Link>
                  <Link to="/student/jobs" className="text-slate-700 hover:text-indigo-600">
                    Jobs
                  </Link>
                  <Link to="/student/skill-gap" className="text-slate-700 hover:text-indigo-600">
                    Skill gap
                  </Link>
                  <Link to="/student/companies" className="text-slate-700 hover:text-indigo-600">
                    Companies
                  </Link>
                  <Link to="/student/resume" className="text-slate-700 hover:text-indigo-600">
                    Resume
                  </Link>
                  <Link to="/student/profile" className="text-slate-700 hover:text-indigo-600">
                    My profile
                  </Link>
                </>
              )}
              <span className="hidden text-slate-500 sm:inline">
                {user.full_name} <span className="text-xs">({user.role})</span>
              </span>
              <button
                onClick={handleLogout}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-100"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-slate-700 hover:text-indigo-600">
                Log in
              </Link>
              <Link
                to="/register"
                className="rounded-md bg-indigo-600 px-3 py-1.5 text-white hover:bg-indigo-700"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}

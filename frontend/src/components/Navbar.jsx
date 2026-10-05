import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// [label, path, match only this exact path?]
const STUDENT_LINKS = [
  ['Dashboard', '/student', true],
  ['Recommended', '/student/recommendations'],
  ['Jobs', '/student/jobs'],
  ['Skill gap', '/student/skill-gap'],
  ['Companies', '/student/companies'],
  ['Applications', '/student/applications'],
  ['Interviews', '/student/interviews'],
  ['Assistant', '/student/chat'],
  ['Resume', '/student/resume'],
  ['My profile', '/student/profile'],
]

const COORDINATOR_LINKS = [
  ['Dashboard', '/coordinator', true],
  ['Students', '/coordinator/students'],
  ['Companies', '/coordinator/companies'],
  ['Jobs', '/coordinator/jobs'],
  ['Applications', '/coordinator/applications'],
  ['Progress', '/coordinator/progress'],
  ['Analytics', '/coordinator/analytics'],
  ['Reports', '/coordinator/reports'],
]

const linkClass = ({ isActive }) =>
  isActive ? 'font-semibold text-indigo-700' : 'text-slate-700 hover:text-indigo-600'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  const handleLogout = async () => {
    setOpen(false)
    await logout()
    navigate('/login', { replace: true })
  }

  const links = !user ? [] : user.role === 'student' ? STUDENT_LINKS : COORDINATOR_LINKS

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3" aria-label="Main">
        <Link to="/" className="shrink-0 text-lg font-semibold text-indigo-600">
          PlaceGenie AI
        </Link>

        {user ? (
          <>
            <ul className="hidden items-center gap-4 text-sm lg:flex">
              {links.map(([label, to, end]) => (
                <li key={to}>
                  <NavLink to={to} end={end} className={linkClass}>{label}</NavLink>
                </li>
              ))}
            </ul>
            <div className="hidden items-center gap-3 text-sm lg:flex">
              <span className="max-w-40 truncate text-slate-500" title={user.full_name}>{user.full_name}</span>
              <button onClick={handleLogout} className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-100">
                Log out
              </button>
            </div>
            <button
              type="button"
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 lg:hidden"
              aria-label="Menu"
              aria-expanded={open}
              aria-controls="mobile-menu"
              onClick={() => setOpen((o) => !o)}
            >
              {open ? '✕ Close' : '☰ Menu'}
            </button>
          </>
        ) : (
          <div className="flex items-center gap-4 text-sm">
            <Link to="/login" className="text-slate-700 hover:text-indigo-600">Log in</Link>
            <Link to="/register" className="rounded-md bg-indigo-600 px-3 py-1.5 text-white hover:bg-indigo-700">Register</Link>
          </div>
        )}
      </nav>

      {user && open && (
        <div id="mobile-menu" className="border-t border-slate-200 bg-white px-4 py-3 lg:hidden">
          <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
            {links.map(([label, to, end]) => (
              <li key={to}>
                <NavLink to={to} end={end} className={(s) => `block rounded px-2 py-2 ${linkClass(s)}`} onClick={() => setOpen(false)}>
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-sm">
            <span className="truncate text-slate-500">{user.full_name}</span>
            <button onClick={handleLogout} className="rounded-md border border-slate-300 px-3 py-1.5 text-slate-700 hover:bg-slate-100">
              Log out
            </button>
          </div>
        </div>
      )}
    </header>
  )
}

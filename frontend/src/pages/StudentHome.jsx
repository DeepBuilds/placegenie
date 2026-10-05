import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'

// Placeholder: it proves the student-only API works. The real dashboard is built in Phase 12.
export default function StudentHome() {
  const [me, setMe] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client
      .get('/students/me')
      .then((r) => setMe(r.data))
      .catch(() => setError('Could not load your account.'))
  }, [])

  return (
    <section className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Student dashboard</h1>
      {error && <p className="mt-3 text-red-600">{error}</p>}
      {me && (
        <p className="mt-3 text-slate-700">
          Welcome, <strong>{me.full_name}</strong> ({me.email}).
        </p>
      )}
      <div className="mt-4 flex flex-wrap gap-3">
        <Link to="/student/profile" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
          Complete my profile
        </Link>
        <Link to="/student/recommendations" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
          Recommended jobs
        </Link>
        <Link to="/student/jobs" className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
          Browse jobs
        </Link>
      </div>
      <p className="mt-4 text-sm text-slate-500">Dashboard features arrive in later phases.</p>
    </section>
  )
}

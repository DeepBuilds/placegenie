import { useEffect, useState } from 'react'
import client from '../api/client'

// Placeholder: it proves the coordinator-only API works. The real dashboard is built in Phase 13.
export default function CoordinatorHome() {
  const [me, setMe] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    client
      .get('/coordinators/me')
      .then((r) => setMe(r.data))
      .catch(() => setError('Could not load your account.'))
  }, [])

  return (
    <section className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-slate-900">Coordinator dashboard</h1>
      {error && <p className="mt-3 text-red-600">{error}</p>}
      {me && (
        <p className="mt-3 text-slate-700">
          Welcome, <strong>{me.full_name}</strong> ({me.email}).
        </p>
      )}
      <p className="mt-4 text-sm text-slate-500">Coordinator features arrive in later phases.</p>
    </section>
  )
}

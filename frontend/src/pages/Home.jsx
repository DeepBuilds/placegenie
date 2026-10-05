import { useEffect, useState } from 'react'
import { getHealth } from '../api/health'

function StatusRow({ label, ok, detail }) {
  return (
    <li className="flex items-center justify-between py-2">
      <span className="text-slate-700">{label}</span>
      <span className={ok ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
        {ok ? 'OK' : 'Unavailable'}
        {detail ? <span className="ml-2 text-xs text-slate-500">{detail}</span> : null}
      </span>
    </li>
  )
}

export default function Home() {
  const [state, setState] = useState({ loading: true, data: null, error: null })

  useEffect(() => {
    getHealth()
      .then((data) => setState({ loading: false, data, error: null }))
      .catch((err) =>
        setState({ loading: false, data: null, error: err.message || 'Request failed' }),
      )
  }, [])

  const { loading, data, error } = state

  return (
    <section className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-3xl font-bold text-slate-900">PlaceGenie AI</h1>
      <p className="mt-2 text-slate-600">
        Intelligent Placement Assistant — project setup (Phase 1).
      </p>

      <div className="mt-8 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">System status</h2>
        {loading && <p className="mt-3 text-slate-500">Checking backend…</p>}
        {error && (
          <p className="mt-3 text-red-600">
            Cannot reach the backend ({error}). Is it running on port 8000?
          </p>
        )}
        {data && (
          <ul className="mt-3 divide-y divide-slate-100">
            <StatusRow label="Backend API" ok={data.status === 'ok'} detail={`v${data.version}`} />
            <StatusRow
              label="MySQL database"
              ok={data.database.connected}
              detail={data.database.connected ? '' : data.database.detail}
            />
          </ul>
        )}
      </div>
    </section>
  )
}

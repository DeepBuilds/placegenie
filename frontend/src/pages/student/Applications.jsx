import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyApplications } from '../../api/applications'
import { StatusBadge } from '../../components/applications/StatusParts'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { STATUS, formatDay, formatWhen } from '../../utils/applications'
import { getErrorMessage } from '../../utils/errors'
import { formatJobType } from '../../utils/jobs'

const FILTERS = ['applied', 'shortlisted', 'online_assessment', 'technical_interview', 'hr_interview', 'selected', 'rejected', 'withdrawn']

export default function Applications() {
  const { get, update, query } = useUrlFilters()
  const status = get('status')
  const [result, setResult] = useState({ key: null, data: null, error: '' })

  useEffect(() => {
    let cancelled = false
    getMyApplications(status ? { status } : {})
      .then((data) => !cancelled && setResult({ key: query, data, error: '' }))
      .catch((err) => !cancelled && setResult({ key: query, data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [status, query])

  const loading = result.key !== query
  const { data, error } = result
  const total = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My applications</h1>
          <p className="text-sm text-slate-600">
            The placement cell updates the official status. Record your own interviews on each application.
          </p>
        </div>
        <Link to="/student/interviews" className="text-sm font-medium text-indigo-600 hover:underline">Interview tracker →</Link>
      </div>

      <div className="mt-5 flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        <button type="button" onClick={() => update({ status: '' })} aria-pressed={!status}
          className={`rounded-full border px-3 py-1 text-sm ${!status ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-100'}`}>
          All{data ? ` (${total})` : ''}
        </button>
        {FILTERS.filter((s) => !data || data.counts[s] || status === s).map((s) => (
          <button key={s} type="button" onClick={() => update({ status: s })} aria-pressed={status === s}
            className={`rounded-full border px-3 py-1 text-sm ${status === s ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-100'}`}>
            {STATUS[s].label}{data?.counts[s] ? ` (${data.counts[s]})` : ''}
          </button>
        ))}
      </div>

      <div className="mt-5" aria-live="polite">
        {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading your applications…</p>}
        {data && data.items.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            {total === 0 ? (
              <>You have not applied to any job yet. <Link to="/student/jobs" className="font-medium text-indigo-600 hover:underline">Browse jobs →</Link></>
            ) : (
              'No applications with this status.'
            )}
          </div>
        )}
        {data && data.items.length > 0 && (
          <ul className="space-y-3" aria-label="Applications">
            {data.items.map((a) => (
              <li key={a.id} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="text-base font-semibold text-slate-900">
                      <Link to={`/student/applications/${a.id}`} className="hover:text-indigo-600">{a.job.title}</Link>
                    </h2>
                    <p className="text-sm text-slate-600">
                      {a.job.company}{a.job.location ? ` · ${a.job.location}` : ''} · {formatJobType(a.job.job_type)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">Applied {formatDay(a.applied_at)}</p>
                  </div>
                  <StatusBadge status={a.status} />
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="text-slate-600">
                    {a.next_interview ? (
                      <>Next interview: <strong>{formatWhen(a.next_interview)}</strong></>
                    ) : a.interview_count ? (
                      `${a.interview_count} interview${a.interview_count === 1 ? '' : 's'} recorded`
                    ) : (
                      'No interviews recorded'
                    )}
                  </span>
                  <Link to={`/student/applications/${a.id}`} className="font-medium text-indigo-600 hover:underline">View details →</Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

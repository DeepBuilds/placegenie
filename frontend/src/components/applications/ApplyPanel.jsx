import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { applyToJob, getMyApplications } from '../../api/applications'
import { checkEligibility } from '../../api/jobs'
import { getErrorMessage } from '../../utils/errors'
import { StatusBadge } from './StatusParts'

/**
 * Apply button for a job. Nobody is blocked from applying (the company and placement cell decide),
 * but a student who does not currently meet the requirements is told so first and confirms.
 */
export default function ApplyPanel({ jobId, isExpired }) {
  const [load, setLoad] = useState({ jobId: null, application: null, error: '' })
  const [phase, setPhase] = useState('idle') // idle | checking | warn | applying
  const [warning, setWarning] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getMyApplications({ job_id: jobId })
      .then((r) => !cancelled && setLoad({ jobId, application: r.items[0] ?? null, error: '' }))
      .catch((err) => !cancelled && setLoad({ jobId, application: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [jobId])

  const submit = async () => {
    setPhase('applying')
    setError('')
    try {
      const application = await applyToJob(jobId)
      setLoad({ jobId, application, error: '' })
      setWarning(null)
      setPhase('idle')
    } catch (err) {
      setError(getErrorMessage(err))
      setPhase('idle')
    }
  }

  const start = async () => {
    setPhase('checking')
    setError('')
    try {
      const result = await checkEligibility(jobId)
      if (result.eligible) return submit()
      setWarning(result)
      setPhase('warn')
    } catch (err) {
      setError(getErrorMessage(err))
      setPhase('idle')
    }
  }

  if (load.jobId !== jobId) return <p className="text-sm text-slate-500">Checking your application…</p>

  const app = load.application
  const active = app && app.status !== 'withdrawn'
  const busy = phase === 'checking' || phase === 'applying'

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="apply-title">
      <h2 id="apply-title" className="text-lg font-semibold text-slate-900">Apply</h2>

      {load.error && <p role="alert" className="mt-2 rounded-md bg-red-50 p-3 text-sm text-red-700">{load.error}</p>}

      {active ? (
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm">
          <span className="text-emerald-700">✓ You applied</span>
          <StatusBadge status={app.status} />
          <Link to={`/student/applications/${app.id}`} className="font-medium text-indigo-600 hover:underline">View application →</Link>
        </div>
      ) : (
        <div className="mt-2">
          {app && <p className="mb-2 text-sm text-slate-600">You withdrew your earlier application. You can apply again.</p>}
          {isExpired ? (
            <p className="text-sm text-red-600">The application deadline for this job has passed.</p>
          ) : phase === 'warn' && warning ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900" role="alert">
              <p className="font-medium">Based on your profile you do not currently meet all the requirements.</p>
              <ul className="mt-1 list-disc pl-5">
                {warning.reasons.map((r) => <li key={r}>{r}</li>)}
              </ul>
              <p className="mt-2">You can still apply: the company and placement cell make the final decision.</p>
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={submit} disabled={busy} className="rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60">Apply anyway</button>
                <button type="button" onClick={() => { setPhase('idle'); setWarning(null) }} className="rounded-md border border-slate-300 bg-white px-4 py-2 text-slate-700 hover:bg-slate-100">Cancel</button>
              </div>
            </div>
          ) : (
            <button type="button" onClick={start} disabled={busy}
              className="rounded-md bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60">
              {phase === 'checking' ? 'Checking eligibility…' : phase === 'applying' ? 'Applying…' : app ? 'Apply again' : 'Apply for this job'}
            </button>
          )}
          {error && <p role="alert" className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        </div>
      )}
    </section>
  )
}

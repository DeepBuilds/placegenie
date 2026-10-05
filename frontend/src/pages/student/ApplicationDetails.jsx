import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { addInterview, deleteInterview, getApplication, updateInterview, withdrawApplication } from '../../api/applications'
import InterviewForm from '../../components/applications/InterviewForm'
import { OutcomeBadge, StatusBadge, StatusTracker } from '../../components/applications/StatusParts'
import Section, { primaryButton, secondaryButton } from '../../components/profile/Section'
import { STAGES, formatDay, formatWhen } from '../../utils/applications'
import { getErrorMessage } from '../../utils/errors'
import { formatJobType } from '../../utils/jobs'

function InterviewRow({ iv, canEdit, onChange, onDelete, busy }) {
  return (
    <li className="py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-medium text-slate-900">
            <Link to={`/student/interviews/${iv.id}`} className="hover:text-indigo-600">{STAGES[iv.stage]}</Link>
          </p>
          <p className="text-sm text-slate-600">{formatWhen(iv.scheduled_at)}</p>
          {iv.notes && <p className="mt-1 whitespace-pre-line text-sm text-slate-700">{iv.notes}</p>}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <OutcomeBadge outcome={iv.outcome} />
          {iv.needs_result && <span className="text-xs font-medium text-amber-700">Add the result</span>}
          {iv.is_upcoming && <span className="text-xs font-medium text-indigo-700">Upcoming</span>}
        </div>
      </div>
      {canEdit && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <label htmlFor={`outcome-${iv.id}`} className="text-xs text-slate-500">Result</label>
          <select id={`outcome-${iv.id}`} value={iv.outcome} disabled={busy} onChange={(e) => onChange(iv.id, { outcome: e.target.value })}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm">
            <option value="pending">Result pending</option>
            <option value="passed">Passed</option>
            <option value="failed">Not cleared</option>
          </select>
          <Link to={`/student/interviews/${iv.id}`} className={secondaryButton}>Edit</Link>
          <button type="button" disabled={busy} onClick={() => onDelete(iv)} className={secondaryButton} aria-label={`Delete ${STAGES[iv.stage]}`}>Delete</button>
        </div>
      )}
    </li>
  )
}

export default function ApplicationDetails() {
  const { id } = useParams()
  const [state, setState] = useState({ id: null, app: null, error: '', notFound: false })
  const [adding, setAdding] = useState(false)
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    let cancelled = false
    getApplication(id)
      .then((app) => !cancelled && setState({ id, app, error: '', notFound: false }))
      .catch((err) => {
        if (cancelled) return
        const notFound = err.response?.status === 404
        setState({ id, app: null, notFound, error: notFound ? '' : getErrorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => load(), [load])

  const run = async (action, okMessage) => {
    setBusy(true)
    setNotice(null)
    try {
      await action()
      setState({ id, app: await getApplication(id), error: '', notFound: false })
      if (okMessage) setNotice({ type: 'success', text: okMessage })
      return true
    } catch (err) {
      setNotice({ type: 'error', text: getErrorMessage(err) })
      return false
    } finally {
      setBusy(false)
    }
  }

  if (state.id !== id) return <p className="p-8 text-center text-slate-500">Loading application…</p>
  if (state.notFound || state.error)
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p role="alert" className="text-slate-700">{state.notFound ? 'This application does not exist.' : state.error}</p>
        <Link to="/student/applications" className="mt-4 inline-block text-indigo-600 hover:underline">← Back to applications</Link>
      </div>
    )

  const { app } = state
  const withdrawn = app.status === 'withdrawn'
  const e = app.eligibility_now

  const withdraw = () => {
    if (!window.confirm('Withdraw this application? You can apply again later while the job is open.')) return
    run(() => withdrawApplication(app.id), 'Application withdrawn.')
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-8">
      <Link to="/student/applications" className="text-sm text-indigo-600 hover:underline">← Back to applications</Link>

      {notice && (
        <div role={notice.type === 'error' ? 'alert' : 'status'}
          className={`rounded-md p-3 text-sm ${notice.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'}`}>
          {notice.text}
        </div>
      )}

      <header className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{app.job.title}</h1>
            <p className="text-slate-600">
              {app.job.company}{app.job.location ? ` · ${app.job.location}` : ''} · {formatJobType(app.job.job_type)}
            </p>
            <p className="mt-1 text-xs text-slate-500">Applied {formatDay(app.applied_at)} · last updated {formatDay(app.updated_at)}</p>
          </div>
          <StatusBadge status={app.status} />
        </div>
        <div className="mt-4"><StatusTracker status={app.status} /></div>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          <Link to={`/student/jobs/${app.job.id}`} className="font-medium text-indigo-600 hover:underline">View job →</Link>
          <Link to={`/student/skill-gap?job_id=${app.job.id}`} className="font-medium text-indigo-600 hover:underline">Skill gap →</Link>
          {app.can_withdraw && (
            <button type="button" onClick={withdraw} disabled={busy} className="ml-auto rounded-md border border-red-300 px-3 py-1.5 text-red-700 hover:bg-red-50">
              Withdraw application
            </button>
          )}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          The official status is set by the placement cell. It changes when the company or placement officers update it, not when you record an interview.
        </p>
      </header>

      <Section title="Eligibility today" subtitle="Based on your current profile; it can change if you update your profile.">
        <p className={`text-sm font-medium ${e.eligible ? 'text-emerald-700' : e.result === 'INCOMPLETE_PROFILE' ? 'text-amber-700' : 'text-red-700'}`}>
          {e.eligible ? '✓ ' : e.result === 'INCOMPLETE_PROFILE' ? '? ' : '✗ '}{e.summary}
        </p>
        {e.failed_requirements.length > 0 && (
          <p className="mt-1 text-sm text-slate-600">Not met: {e.failed_requirements.join(', ')}.</p>
        )}
      </Section>

      <Section title="Interviews and tests" subtitle="Record each round, its date and your notes.">
        {app.interviews.length === 0 ? (
          <p className="text-sm text-slate-500">No interviews recorded yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100" aria-label="Interviews">
            {app.interviews.map((iv) => (
              <InterviewRow key={iv.id} iv={iv} canEdit={!withdrawn} busy={busy}
                onChange={(ivId, changes) => run(() => updateInterview(ivId, changes), 'Interview updated.')}
                onDelete={(row) => window.confirm('Delete this interview?') && run(() => deleteInterview(row.id), 'Interview deleted.')} />
            ))}
          </ul>
        )}

        {withdrawn ? (
          <p className="mt-3 text-sm text-slate-500">Interviews cannot be added to a withdrawn application.</p>
        ) : adding ? (
          <div className="mt-4">
            <InterviewForm idPrefix="new" submitLabel="Add interview" onCancel={() => setAdding(false)}
              onSubmit={async (payload) => {
                const body = { ...payload }
                delete body.application_id // this form is already inside one application
                if (await run(() => addInterview(app.id, body), 'Interview added.')) setAdding(false)
              }} />
          </div>
        ) : (
          <button type="button" onClick={() => setAdding(true)} className={`${primaryButton} mt-4`}>+ Add interview</button>
        )}
      </Section>
    </div>
  )
}

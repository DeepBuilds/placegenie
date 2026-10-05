import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { addInterview, getMyApplications, getMyInterviews } from '../../api/applications'
import InterviewForm from '../../components/applications/InterviewForm'
import { OutcomeBadge, StatusBadge } from '../../components/applications/StatusParts'
import { primaryButton } from '../../components/profile/Section'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { STAGES, formatWhen } from '../../utils/applications'
import { getErrorMessage } from '../../utils/errors'

const TABS = [
  ['upcoming', 'Upcoming'],
  ['past', 'Past'],
  ['unscheduled', 'No date yet'],
]

function InterviewCard({ iv }) {
  return (
    <li className={`rounded-lg border bg-white p-4 shadow-sm ${iv.needs_result ? 'border-amber-300' : 'border-slate-200'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900">
            <Link to={`/student/interviews/${iv.id}`} className="hover:text-indigo-600">{STAGES[iv.stage]}</Link>
            <span className="font-normal text-slate-600"> · {iv.application.job.title}</span>
          </h3>
          <p className="text-sm text-slate-600">{iv.application.job.company}</p>
          <p className="mt-1 text-sm font-medium text-slate-800">{formatWhen(iv.scheduled_at)}</p>
          {iv.notes && <p className="mt-1 line-clamp-2 text-sm text-slate-600">{iv.notes}</p>}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <OutcomeBadge outcome={iv.outcome} />
          <StatusBadge status={iv.application.status} />
          {iv.needs_result && <span className="text-xs font-medium text-amber-700">Add the result</span>}
        </div>
      </div>
      <div className="mt-2 text-right">
        <Link to={`/student/interviews/${iv.id}`} className="text-sm font-medium text-indigo-600 hover:underline">Details →</Link>
      </div>
    </li>
  )
}

export default function Interviews() {
  const { get, update } = useUrlFilters()
  const tab = TABS.some(([key]) => key === get('tab')) ? get('tab') : 'upcoming'
  const [state, setState] = useState({ data: null, error: '', version: 0 })
  const [apps, setApps] = useState([])
  const [recording, setRecording] = useState(false)
  const [formError, setFormError] = useState('')
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let cancelled = false
    getMyInterviews('all')
      .then((data) => !cancelled && setState({ data, error: '' }))
      .catch((err) => !cancelled && setState({ data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [reload])

  useEffect(() => {
    getMyApplications()
      .then((r) => setApps(r.items.filter((a) => a.status !== 'withdrawn')))
      .catch(() => setApps([]))
  }, [])

  const { data, error } = state
  const shown = data ? data.items.filter((iv) => (tab === 'upcoming' ? iv.is_upcoming : tab === 'past' ? iv.scheduled_at && !iv.is_upcoming : !iv.scheduled_at)) : []
  const count = (key) => data?.counts[key] ?? 0

  const record = async ({ application_id, ...body }) => {
    setFormError('')
    try {
      await addInterview(application_id, body)
      setRecording(false)
      setReload((n) => n + 1)
      update({ tab: body.scheduled_at ? 'upcoming' : 'unscheduled' })
    } catch (err) {
      setFormError(getErrorMessage(err))
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Interview tracker</h1>
          <p className="text-sm text-slate-600">Every interview and test across your applications, with dates, notes and results.</p>
        </div>
        {!recording && apps.length > 0 && (
          <button type="button" onClick={() => setRecording(true)} className={primaryButton}>+ Record interview</button>
        )}
      </div>

      {recording && (
        <div className="mt-4">
          {formError && <p role="alert" className="mb-2 rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</p>}
          <InterviewForm idPrefix="rec" applications={apps} submitLabel="Add interview" onSubmit={record} onCancel={() => setRecording(false)} />
        </div>
      )}
      {apps.length === 0 && state.data && (
        <p className="mt-4 text-sm text-slate-600">
          You need an application before you can record an interview.{' '}
          <Link to="/student/jobs" className="font-medium text-indigo-600 hover:underline">Browse jobs →</Link>
        </p>
      )}

      {data?.counts.needs_result > 0 && (
        <p role="status" className="mt-4 rounded-md bg-amber-50 p-3 text-sm text-amber-900">
          {data.counts.needs_result} past interview{data.counts.needs_result === 1 ? ' has' : 's have'} no result yet. Open the{' '}
          <button type="button" onClick={() => update({ tab: 'past' })} className="font-medium underline">Past</button> tab to update them.
        </p>
      )}

      <div className="mt-5 flex gap-2 border-b border-slate-200" role="tablist" aria-label="Interview time">
        {TABS.map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => update({ tab: key })}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${tab === key ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-600 hover:text-slate-900'}`}>
            {label} ({count(key)})
          </button>
        ))}
      </div>

      <div className="mt-4" aria-live="polite">
        {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {!data && !error && <p className="py-10 text-center text-slate-500">Loading your interviews…</p>}
        {data && shown.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            {tab === 'upcoming' && 'No upcoming interviews.'}
            {tab === 'past' && 'No past interviews.'}
            {tab === 'unscheduled' && 'No interviews without a date.'}
          </div>
        )}
        {data && shown.length > 0 && (
          <ul className="space-y-3" aria-label={`${tab} interviews`}>
            {shown.map((iv) => <InterviewCard key={iv.id} iv={iv} />)}
          </ul>
        )}
      </div>
    </div>
  )
}

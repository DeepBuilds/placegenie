import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteInterview, getInterview, updateInterview } from '../../api/applications'
import InterviewForm from '../../components/applications/InterviewForm'
import { OutcomeBadge, StatusBadge } from '../../components/applications/StatusParts'
import Section, { primaryButton, secondaryButton } from '../../components/profile/Section'
import { STAGES, formatWhen } from '../../utils/applications'
import { getErrorMessage } from '../../utils/errors'

export default function InterviewDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState({ id: null, iv: null, error: '', notFound: false })
  const [editing, setEditing] = useState(false)
  const [notice, setNotice] = useState(null)

  useEffect(() => {
    let cancelled = false
    getInterview(id)
      .then((iv) => !cancelled && setState({ id, iv, error: '', notFound: false }))
      .catch((err) => {
        if (cancelled) return
        const notFound = err.response?.status === 404
        setState({ id, iv: null, notFound, error: notFound ? '' : getErrorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (state.id !== id) return <p className="p-8 text-center text-slate-500">Loading interview…</p>
  if (state.notFound || state.error)
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p role="alert" className="text-slate-700">{state.notFound ? 'This interview does not exist.' : state.error}</p>
        <Link to="/student/interviews" className="mt-4 inline-block text-indigo-600 hover:underline">← Back to the tracker</Link>
      </div>
    )

  const { iv } = state
  const withdrawn = iv.application.status === 'withdrawn'

  const save = async ({ stage, scheduled_at, outcome, notes }) => {
    try {
      await updateInterview(iv.id, { stage, scheduled_at, outcome, notes })
      setState({ id, iv: await getInterview(id), error: '', notFound: false })
      setEditing(false)
      setNotice({ type: 'success', text: 'Interview saved.' })
    } catch (err) {
      setNotice({ type: 'error', text: getErrorMessage(err) })
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete this interview?')) return
    try {
      await deleteInterview(iv.id)
      navigate(`/student/applications/${iv.application.id}`, { replace: true })
    } catch (err) {
      setNotice({ type: 'error', text: getErrorMessage(err) })
    }
  }

  const job = iv.application.job
  return (
    <div className="mx-auto max-w-2xl space-y-5 px-4 py-8">
      <Link to="/student/interviews" className="text-sm text-indigo-600 hover:underline">← Interview tracker</Link>

      {notice && (
        <div role={notice.type === 'error' ? 'alert' : 'status'}
          className={`rounded-md p-3 text-sm ${notice.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'}`}>
          {notice.text}
        </div>
      )}

      <header className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{STAGES[iv.stage]}</h1>
            <p className="text-slate-600">{job.title} · {job.company}</p>
            <p className="mt-2 text-lg font-medium text-slate-900">{formatWhen(iv.scheduled_at)}</p>
            {iv.is_upcoming && <p className="text-sm font-medium text-indigo-700">Upcoming</p>}
            {iv.needs_result && <p className="text-sm font-medium text-amber-700">This interview has passed: add the result.</p>}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <OutcomeBadge outcome={iv.outcome} />
            <StatusBadge status={iv.application.status} />
          </div>
        </div>
        <p className="mt-4 text-sm">
          <Link to={`/student/applications/${iv.application.id}`} className="font-medium text-indigo-600 hover:underline">View application →</Link>
        </p>
      </header>

      <Section title="Notes">
        {iv.notes ? <p className="whitespace-pre-line text-sm text-slate-700">{iv.notes}</p> : <p className="text-sm text-slate-500">No notes yet.</p>}
      </Section>

      {withdrawn ? (
        <p className="text-sm text-slate-500">This application was withdrawn, so its interviews can no longer be changed.</p>
      ) : editing ? (
        <Section title="Edit interview">
          <InterviewForm idPrefix="edit" initial={iv} submitLabel="Save changes" onSubmit={save} onCancel={() => setEditing(false)} />
        </Section>
      ) : (
        <div className="flex gap-2">
          <button type="button" onClick={() => setEditing(true)} className={primaryButton}>Edit interview</button>
          <button type="button" onClick={remove} className={secondaryButton}>Delete</button>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import { updateApplicationStatus } from '../../api/admin'
import { STATUS } from '../../utils/applications'
import { STAGE_LABEL, STAGE_STYLE } from '../../utils/coordinator'
import { getErrorMessage } from '../../utils/errors'
import { StatusBadge } from '../applications/StatusParts'
import { inputClass, secondaryButton } from '../profile/Section'


export function StageBadge({ stage }) {
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${STAGE_STYLE[stage] ?? STAGE_STYLE.not_applied}`}>{STAGE_LABEL[stage] ?? stage}</span>
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

export function ErrorNote({ children }) {
  return children ? <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{children}</p> : null
}

export function Pagination({ total, limit, offset, onChange }) {
  if (total <= limit) return null
  const page = Math.floor(offset / limit) + 1
  const pages = Math.ceil(total / limit)
  return (
    <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pages">
      <button type="button" className={secondaryButton} disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>← Previous</button>
      <span className="text-slate-600">Page {page} of {pages} · {total} in total</span>
      <button type="button" className={secondaryButton} disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>Next →</button>
    </nav>
  )
}

/** Shows an application's status and lets the coordinator change it. Withdrawn applications are locked. */
export function StatusControl({ application, onChanged }) {
  const [value, setValue] = useState(application.status)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  if (application.status === 'withdrawn') {
    return <div><StatusBadge status="withdrawn" /><p className="mt-1 text-xs text-slate-500">Withdrawn by the student</p></div>
  }
  const options = Object.keys(STATUS).filter((s) => s !== 'withdrawn')
  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await updateApplicationStatus(application.id, value)
      onChanged?.()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }
  const label = `Status for ${application.student?.full_name ?? 'student'}, ${application.job.title}`
  return (
    <div>
      <div className="flex items-center gap-2">
        <select aria-label={label} value={value} onChange={(e) => setValue(e.target.value)} className={`${inputClass} mt-0 w-auto py-1 text-sm`}>
          {options.map((s) => <option key={s} value={s}>{STATUS[s].label}</option>)}
        </select>
        <button type="button" className={secondaryButton} disabled={saving || value === application.status} onClick={save} aria-label={`Update ${label}`}>
          {saving ? 'Saving…' : 'Update'}
        </button>
      </div>
      {error && <p role="alert" className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

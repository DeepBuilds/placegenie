// The path an application normally follows. "rejected" and "withdrawn" are ways it can end.
export const PIPELINE = ['applied', 'shortlisted', 'online_assessment', 'technical_interview', 'hr_interview', 'selected']

export const STATUS = {
  applied: { label: 'Applied', cls: 'bg-sky-100 text-sky-800' },
  shortlisted: { label: 'Shortlisted', cls: 'bg-indigo-100 text-indigo-800' },
  online_assessment: { label: 'Online assessment', cls: 'bg-violet-100 text-violet-800' },
  technical_interview: { label: 'Technical interview', cls: 'bg-amber-100 text-amber-800' },
  hr_interview: { label: 'HR interview', cls: 'bg-orange-100 text-orange-800' },
  selected: { label: 'Selected', cls: 'bg-emerald-100 text-emerald-800' },
  rejected: { label: 'Rejected', cls: 'bg-red-100 text-red-800' },
  withdrawn: { label: 'Withdrawn', cls: 'bg-slate-200 text-slate-700' },
}

export const STAGES = {
  online_assessment: 'Online assessment',
  technical_interview: 'Technical interview',
  hr_interview: 'HR interview',
  other: 'Other round',
}

export const OUTCOMES = {
  pending: { label: 'Result pending', cls: 'bg-slate-100 text-slate-700' },
  passed: { label: 'Passed', cls: 'bg-emerald-100 text-emerald-800' },
  failed: { label: 'Not cleared', cls: 'bg-red-100 text-red-800' },
}

export const statusLabel = (s) => STATUS[s]?.label ?? s

export function formatWhen(iso) {
  if (!iso) return 'Date not set'
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function formatDay(iso) {
  return iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''
}

// "2026-10-20T14:30:00" <-> the value of <input type="datetime-local"> ("2026-10-20T14:30")
export const toInputValue = (iso) => (iso ? iso.slice(0, 16) : '')
export const fromInputValue = (v) => (v ? v : null)

export function validateInterview({ scheduled_at, notes }) {
  const errors = {}
  if (scheduled_at) {
    const d = new Date(scheduled_at)
    if (Number.isNaN(d.getTime())) errors.scheduled_at = 'Enter a valid date and time.'
    else if (d.getFullYear() < 2000 || d.getFullYear() > 2100) errors.scheduled_at = 'Enter a date between 2000 and 2100.'
  }
  if (notes && notes.length > 2000) errors.notes = 'Notes can be at most 2000 characters.'
  return errors
}

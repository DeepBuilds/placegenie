import { OUTCOMES, PIPELINE, STATUS, statusLabel } from '../../utils/applications'

export function StatusBadge({ status }) {
  const s = STATUS[status] ?? { label: status, cls: 'bg-slate-100 text-slate-700' }
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${s.cls}`}>{s.label}</span>
}

export function OutcomeBadge({ outcome }) {
  const o = OUTCOMES[outcome] ?? OUTCOMES.pending
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${o.cls}`}>{o.label}</span>
}

/** Where the application is on its usual path. Rejected / withdrawn applications show a banner instead. */
export function StatusTracker({ status }) {
  if (status === 'rejected' || status === 'withdrawn') {
    return (
      <p role="status" className={`rounded-md p-3 text-sm ${status === 'rejected' ? 'bg-red-50 text-red-800' : 'bg-slate-100 text-slate-700'}`}>
        {status === 'rejected'
          ? 'This application was not taken forward by the company or placement cell.'
          : 'You withdrew this application. You can apply again while the job is open.'}
      </p>
    )
  }
  const current = PIPELINE.indexOf(status)
  return (
    <ol className="flex flex-wrap gap-y-2" aria-label="Application progress">
      {PIPELINE.map((step, i) => {
        const done = i < current
        const now = i === current
        return (
          <li key={step} aria-current={now ? 'step' : undefined} className="flex items-center">
            <span
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
                now ? 'bg-indigo-600 text-white' : done ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'
              }`}
            >
              <span aria-hidden="true">{done ? '✓' : now ? '●' : '○'}</span>
              {statusLabel(step)}
              {now && <span className="sr-only"> (current)</span>}
            </span>
            {i < PIPELINE.length - 1 && <span className="mx-1 text-slate-300" aria-hidden="true">›</span>}
          </li>
        )
      })}
    </ol>
  )
}

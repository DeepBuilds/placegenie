/**
 * Small charts drawn with plain HTML, so there is no chart library to learn or ship.
 * Every bar also prints its number, so nothing depends on colour or on seeing the bar.
 */

/** One horizontal bar per row, all drawn to the same scale (`max`, or the largest value). */
export function BarList({ rows, max, label, unit = '' }) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value))
  return (
    <ul className="space-y-2.5" aria-label={label}>
      {rows.map((r) => (
        <li key={r.key ?? r.label}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-slate-800">{r.label}</span>
            <span className="shrink-0 font-medium text-slate-900">{r.value}{unit}{r.note ? <span className="ml-1.5 font-normal text-slate-500">{r.note}</span> : null}</span>
          </div>
          <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
            <div className={`h-full rounded-full ${r.cls ?? 'bg-indigo-500'}`} style={{ width: `${Math.min(100, (r.value / top) * 100)}%` }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

/**
 * A bar per row split into coloured parts that add up to the row's total.
 * series: [{ key, label, cls }]   rows: [{ label, values: { [key]: number }, note? }]
 */
export function StackedBars({ rows, series, label }) {
  const top = Math.max(1, ...rows.map((r) => series.reduce((sum, s) => sum + (r.values[s.key] ?? 0), 0)))
  return (
    <div>
      <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Legend">
        {series.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5"><span className={`inline-block h-2.5 w-2.5 rounded-sm ${s.cls}`} aria-hidden="true" />{s.label}</li>
        ))}
      </ul>
      <ul className="space-y-2.5" aria-label={label}>
        {rows.map((r) => {
          const total = series.reduce((sum, s) => sum + (r.values[s.key] ?? 0), 0)
          const detail = series.filter((s) => r.values[s.key]).map((s) => `${r.values[s.key]} ${s.label.toLowerCase()}`).join(', ')
          return (
            <li key={r.key ?? r.label}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-slate-800">{r.label}</span>
                <span className="shrink-0 font-medium text-slate-900">{total}{r.note ? <span className="ml-1.5 font-normal text-slate-500">{r.note}</span> : null}</span>
              </div>
              <div className="mt-1 flex h-2.5 overflow-hidden rounded-full bg-slate-100" aria-hidden="true" title={detail}>
                {series.map((s) => (r.values[s.key] ? <div key={s.key} className={s.cls} style={{ width: `${(r.values[s.key] / top) * 100}%` }} /> : null))}
              </div>
              <span className="sr-only">{detail || 'none'}</span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

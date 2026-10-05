import { Link } from 'react-router-dom'

/** A dashboard card. Handles its own loading skeleton, "could not load" state and header link. */
export default function Widget({ title, to, linkLabel, loading, error, onRetry, children, className = '' }) {
  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`} aria-label={title}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {to && !loading && !error && (
          <Link to={to} className="text-xs font-medium text-indigo-600 hover:underline">{linkLabel ?? 'View all →'}</Link>
        )}
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="animate-pulse space-y-2" role="status" aria-label={`Loading ${title}`}>
            <div className="h-4 w-3/4 rounded bg-slate-200" />
            <div className="h-4 w-1/2 rounded bg-slate-200" />
            <div className="h-4 w-2/3 rounded bg-slate-200" />
          </div>
        ) : error ? (
          <div role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">
            {error}{' '}
            {onRetry && <button type="button" onClick={onRetry} className="font-medium underline">Try again</button>}
          </div>
        ) : (
          children
        )}
      </div>
    </section>
  )
}

export function Empty({ children }) {
  return <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">{children}</p>
}

export function Bar({ value, label, color }) {
  const tone = color ?? (value >= 70 ? 'bg-emerald-500' : value >= 40 ? 'bg-amber-500' : 'bg-red-400')
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full transition-all ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  )
}

import { Link } from 'react-router-dom'
import { getCoordinatorDashboard } from '../../api/admin'
import { StatusBadge } from '../../components/applications/StatusParts'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import Widget, { Bar, Empty } from '../../components/dashboard/Widget'
import { useLoad } from '../../hooks/useLoad'
import { STATUS, formatDay } from '../../utils/applications'
import { deadlineText } from '../../utils/dates'

function Stat({ label, value, hint, to }) {
  const body = (
    <>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </>
  )
  const cls = 'rounded-lg border border-slate-200 bg-white p-4 shadow-sm'
  return to ? <Link to={to} className={`${cls} block hover:border-indigo-300`}>{body}</Link> : <div className={cls}>{body}</div>
}

export default function CoordinatorDashboard() {
  const { data, error, loading, reload } = useLoad(getCoordinatorDashboard, 'dashboard')

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Placement dashboard" subtitle="Live numbers from the database for the whole placement cell." />
      {error && (
        <div className="mt-4">
          <ErrorNote>{error} <button type="button" className="underline" onClick={reload}>Try again</button></ErrorNote>
        </div>
      )}
      {loading && !data && <p className="py-10 text-center text-slate-500">Loading the dashboard…</p>}
      {data && <DashboardBody d={data} />}
    </div>
  )
}

function DashboardBody({ d }) {
  const { stats: s, attention: a } = d
  const maxFunnel = Math.max(1, ...d.application_funnel.map((f) => f.count))
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
  return (
    <>
      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4" aria-label="Statistics">
        <Stat label="Total students" value={s.total_students} to="/coordinator/students" />
        <Stat label="Total companies" value={s.total_companies} to="/coordinator/companies" />
        <Stat label="Total jobs" value={s.total_jobs} hint={`${s.open_jobs} open`} to="/coordinator/jobs" />
        <Stat label="Total applications" value={s.total_applications} hint={`${plural(s.applicants, 'student')} applied`} to="/coordinator/applications" />
        <Stat label="Shortlisted students" value={s.shortlisted_students} hint="Being considered by a company" to="/coordinator/students?stage=in_process" />
        <Stat label="Selected students" value={s.selected_students} to="/coordinator/students?stage=placed" />
        <Stat label="Rejected applications" value={s.rejected_applications} to="/coordinator/applications?status=rejected" />
        <Stat label="Placement rate" value={s.placement_rate.percent === null ? '—' : `${s.placement_rate.percent}%`} hint={s.placement_rate.note} />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Widget title="Needs attention">
          <ul className="space-y-2 text-sm">
            <li><Link to="/coordinator/applications?status=applied" className="text-indigo-600 hover:underline">{plural(a.awaiting_review, 'application')} awaiting review</Link></li>
            <li>{plural(a.interviews_this_week, 'interview')} in the next 7 days</li>
            <li><Link to="/coordinator/jobs" className="text-indigo-600 hover:underline">{plural(a.open_jobs_without_applications, 'open job')} with no applicants</Link></li>
          </ul>
          <h3 className="mt-4 text-sm font-semibold text-slate-800">Closing within 7 days</h3>
          {a.closing_soon.length === 0 ? (
            <p className="mt-1 text-sm text-slate-500">No open job closes this week.</p>
          ) : (
            <ul className="mt-1 space-y-1 text-sm">
              {a.closing_soon.map((j) => (
                <li key={j.job_id}>{j.title} · {j.company} <span className="text-slate-500">({deadlineText(j.deadline)}, {j.applications} applied)</span></li>
              ))}
            </ul>
          )}
        </Widget>

        <Widget title="Application funnel">
          <ul className="space-y-2" aria-label="Applications by status">
            {d.application_funnel.map((f) => (
              <li key={f.status}>
                <div className="flex justify-between text-sm"><span>{STATUS[f.status]?.label ?? f.status}</span><span className="font-medium">{f.count}</span></div>
                <Bar value={(f.count / maxFunnel) * 100} label={STATUS[f.status]?.label ?? f.status} color="bg-indigo-500" />
              </li>
            ))}
          </ul>
        </Widget>

        <Widget title="Latest applications" to="/coordinator/applications">
          {d.recent_applications.length === 0 ? (
            <Empty>No applications yet.</Empty>
          ) : (
            <ul className="divide-y divide-slate-100 text-sm">
              {d.recent_applications.map((r) => (
                <li key={r.id} className="flex items-start justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <Link to={`/coordinator/students/${r.student_id}`} className="font-medium text-slate-900 hover:text-indigo-600">{r.student_name}</Link>
                    <p className="truncate text-slate-600">{r.job_title} · {r.company}</p>
                    <p className="text-xs text-slate-500">{formatDay(r.applied_at)}</p>
                  </div>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          )}
        </Widget>
      </div>
    </>
  )
}

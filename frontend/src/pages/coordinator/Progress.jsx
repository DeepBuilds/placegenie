import { Link } from 'react-router-dom'
import { getCohortProgress } from '../../api/admin'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import Widget, { Bar } from '../../components/dashboard/Widget'
import { useLoad } from '../../hooks/useLoad'
import { STAGE_STYLE } from '../../utils/coordinator'

const ATTENTION = {
  no_resume: ['have not uploaded a resume', '/coordinator/students?has_resume=false'],
  not_applied: ['have not applied to any job', '/coordinator/students?stage=not_applied'],
  profile_not_ready: ['have a profile under 80% complete', '/coordinator/students?profile_ready=false'],
}

export default function Progress() {
  const { data, error, loading } = useLoad(getCohortProgress, 'progress')
  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader title="Placement progress" subtitle="How far the whole cohort has got, using the same steps each student sees on their own dashboard." />
      <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>
      {loading && !data && <p className="py-10 text-center text-slate-500">Loading progress…</p>}
      {data && (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <Widget title={`Milestones reached (${data.total_students} students)`}>
            <ol className="space-y-3" aria-label="Cohort milestones">
              {data.funnel.map((s) => (
                <li key={s.key}>
                  <div className="flex justify-between text-sm"><span>{s.label}</span><span className="font-medium">{s.count} · {s.percent}%</span></div>
                  <Bar value={s.percent} label={s.label} color="bg-indigo-500" />
                </li>
              ))}
            </ol>
          </Widget>
          <div className="space-y-4">
            <Widget title="Where students are now">
              <ul className="space-y-2">
                {data.current_stage.map((s) => (
                  <li key={s.key} className="flex items-center justify-between text-sm">
                    <Link to={`/coordinator/students?stage=${s.key}`} className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STAGE_STYLE[s.key] ?? STAGE_STYLE.not_applied}`}>{s.label}</Link>
                    <span>{s.count} student{s.count === 1 ? '' : 's'} ({s.percent}%)</span>
                  </li>
                ))}
              </ul>
            </Widget>
            <Widget title="Needs attention">
              <ul className="space-y-2 text-sm">
                {Object.entries(data.needs_attention).map(([key, n]) => {
                  const [text, to] = ATTENTION[key] ?? [key.replace(/_/g, ' '), '/coordinator/students']
                  return <li key={key}><Link to={to} className="text-indigo-600 hover:underline">{n} student{n === 1 ? '' : 's'} {text}</Link></li>
                })}
              </ul>
            </Widget>
          </div>
        </div>
      )}
    </div>
  )
}

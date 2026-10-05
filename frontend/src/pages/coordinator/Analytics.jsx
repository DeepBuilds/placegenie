import { getAnalytics } from '../../api/admin'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import Widget, { Bar, Empty } from '../../components/dashboard/Widget'
import { useLoad } from '../../hooks/useLoad'

function Table({ label, head, rows, empty }) {
  if (rows.length === 0) return <Empty>{empty}</Empty>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <caption className="sr-only">{label}</caption>
        <thead className="text-xs uppercase text-slate-500">
          <tr>{head.map((h) => <th key={h} scope="col" className="py-1 pr-4">{h}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr key={r[0]}>{r.map((c, i) => <td key={i} className={`py-1.5 pr-4 ${i === 0 ? 'font-medium text-slate-900' : 'text-slate-700'}`}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const rate = (r, min) => (r === null ? `needs ${min}+ students` : `${r}%`)

export default function Analytics() {
  const { data: a, error, loading } = useLoad(getAnalytics, 'analytics')
  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Analytics" subtitle="Every figure is counted from the database. Rates are hidden for groups that are too small to mean anything." />
      <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>
      {loading && !a && <p className="py-10 text-center text-slate-500">Loading analytics…</p>}
      {a && (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <Widget title="Applications by company">
            <Table label="Applications by company" head={['Company', 'Jobs', 'Applications', 'In process', 'Selected', 'Rejected']} empty="No applications yet."
              rows={a.by_company.map((c) => [c.company, c.jobs, c.applications, c.shortlisted, c.selected, c.rejected])} />
          </Widget>
          <Widget title="Placement by branch">
            <Table label="Placement by branch" head={['Branch', 'Students', 'Applied', 'Placed', 'Rate']} empty="No students yet."
              rows={a.by_branch.map((b) => [b.branch, b.students, b.applicants, b.placed, rate(b.placement_rate, a.min_group_size)])} />
          </Widget>
          <Widget title="Placement by CGPA">
            <Table label="Placement by CGPA" head={['CGPA', 'Students', 'Placed', 'Rate']} empty="No students yet."
              rows={a.by_cgpa.map((b) => [b.band, b.students, b.placed, rate(b.placement_rate, a.min_group_size)])} />
          </Widget>
          <Widget title="Interview results">
            <p className="text-sm text-slate-700">
              {a.interview_outcomes.total} interview{a.interview_outcomes.total === 1 ? '' : 's'} recorded: {a.interview_outcomes.passed} passed, {a.interview_outcomes.not_cleared} not cleared, {a.interview_outcomes.pending} pending.
            </p>
            <p className="mt-1 text-sm font-medium text-slate-900">
              Pass rate: {a.interview_outcomes.pass_rate === null ? 'not enough results yet' : `${a.interview_outcomes.pass_rate}%`}
            </p>
          </Widget>
          <Widget title="Skills: demand against supply" className="lg:col-span-2">
            {a.skill_supply.length === 0 ? <Empty>No skill data yet.</Empty> : (
              <ul className="grid gap-x-8 gap-y-3 md:grid-cols-2" aria-label="Skill supply">
                {a.skill_supply.map((s) => (
                  <li key={s.skill}>
                    <div className="flex justify-between text-sm"><span className="font-medium">{s.skill}</span><span className="text-slate-600">{s.jobs_requiring} open jobs · {s.students_with} students ({s.students_percent}%)</span></div>
                    <Bar value={s.students_percent} label={`Students with ${s.skill}`} />
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-slate-500">A skill many jobs ask for but few students have is a good topic for a workshop.</p>
          </Widget>
        </div>
      )}
    </div>
  )
}

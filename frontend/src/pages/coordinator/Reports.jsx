import { useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadReport, getCoordinatorReport, getReports } from '../../api/admin'
import { BarList, StackedBars } from '../../components/charts/Charts'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import Widget, { Empty } from '../../components/dashboard/Widget'
import { primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { STATUS, STATUS_BAR, formatDay } from '../../utils/applications'
import { STAGE_BAR } from '../../utils/coordinator'
import { getErrorMessage } from '../../utils/errors'

const TITLES = { students: 'Students', applications: 'Applications', placements: 'Placements', companies: 'Companies', jobs: 'Jobs', skills: 'Skills' }
const OUTCOME_SERIES = [
  { key: 'in_process', label: 'In process', cls: 'bg-indigo-500' },
  { key: 'selected', label: 'Selected', cls: 'bg-emerald-500' },
  { key: 'rejected', label: 'Rejected', cls: 'bg-red-500' },
  { key: 'other', label: 'Applied or withdrawn', cls: 'bg-slate-400' },
]
const JOB_ROWS_SHOWN = 15

function Tile({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

const rateText = (rate, min) => (rate === null ? `needs ${min}+ students` : `${rate}% placed`)

export default function Reports() {
  const report = useLoad(getCoordinatorReport, 'report')
  const exports = useLoad(getReports, 'exports')
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState({ ok: '', error: '' })

  const download = async (kind) => {
    setBusy(kind)
    setMessage({ ok: '', error: '' })
    try {
      setMessage({ ok: `Downloaded ${await downloadReport(kind)}`, error: '' })
    } catch (err) {
      setMessage({ ok: '', error: getErrorMessage(err) })
    } finally {
      setBusy('')
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Placement report" subtitle={report.data ? `Counted from the database at ${new Date(report.data.generated_at).toLocaleString()}.` : 'Counted from the database each time you open this page.'}>
        <button type="button" className={`${secondaryButton} print:hidden`} onClick={() => window.print()}>Print / save as PDF</button>
      </PageHeader>
      <div className="mt-4 space-y-3" aria-live="polite">
        {report.error && <ErrorNote>{report.error} <button type="button" className="underline" onClick={report.reload}>Try again</button></ErrorNote>}
        <ErrorNote>{message.error}</ErrorNote>
        {message.ok && <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{message.ok}</p>}
        {report.loading && !report.data && <p className="py-10 text-center text-slate-500">Preparing the report…</p>}
      </div>
      {report.data && <Body r={report.data} />}

      <section className="mt-8 print:hidden" aria-label="Export">
        <h2 className="text-lg font-semibold text-slate-900">Export</h2>
        <p className="text-sm text-slate-600">CSV files open in Excel or Google Sheets and always contain the latest data.</p>
        <ErrorNote>{exports.error}</ErrorNote>
        {exports.data && (
          <ul className="mt-3 grid gap-3 md:grid-cols-2">
            {exports.data.map((e) => (
              <li key={e.kind} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div>
                  <h3 className="font-semibold text-slate-900">{TITLES[e.kind] ?? e.kind}</h3>
                  <p className="text-sm text-slate-600">{e.description}</p>
                </div>
                <button type="button" className={primaryButton} disabled={busy !== ''} onClick={() => download(e.kind)} aria-label={`Download ${TITLES[e.kind] ?? e.kind} report`}>
                  {busy === e.kind ? 'Preparing…' : 'Download CSV'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function Body({ r }) {
  const p = r.placement
  const min = r.min_group_size
  const funnelRows = r.status_distribution.filter((d) => d.count > 0).map((d) => ({ key: d.status, label: STATUS[d.status].label, value: d.count, cls: STATUS_BAR[d.status] }))
  const companiesWith = r.companies.filter((c) => c.applications > 0)
  const jobsWith = r.jobs.filter((j) => j.applications > 0)
  const interviews = r.interviews

  return (
    <div className="mt-4 space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5" aria-label="Placement statistics">
        <Tile label="Students" value={p.total_students} hint={`${p.applicants} have applied`} />
        <Tile label="Placed" value={p.placed} hint="At least one selected application" />
        <Tile label="In process" value={p.in_process} hint="Shortlisted or in a round" />
        <Tile label="Rejected" value={p.rejected} hint="Every application rejected" />
        <Tile label="Placement rate" value={p.placement_rate.percent === null ? '—' : `${p.placement_rate.percent}%`} hint={p.placement_rate.note} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Where students are now">
          {p.total_students === 0 ? <Empty>No students have registered yet.</Empty> : (
            <BarList label="Students by stage" rows={p.by_stage.map((s) => ({ key: s.key, label: s.label, value: s.count, note: `(${s.percent}%)`, cls: STAGE_BAR[s.key] }))} max={p.total_students} />
          )}
        </Widget>
        <Widget title="Application status distribution">
          {funnelRows.length === 0 ? <Empty>No applications yet.</Empty> : <BarList label="Applications by status" rows={funnelRows} />}
        </Widget>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Placement by branch">
          {p.by_branch.length === 0 ? <Empty>No students yet.</Empty> : (
            <StackedBars label="Students by branch" series={[{ key: 'placed', label: 'Placed', cls: 'bg-emerald-500' }, { key: 'not_placed', label: 'Not placed yet', cls: 'bg-slate-300' }]}
              rows={p.by_branch.map((b) => ({ key: b.branch, label: b.branch, values: { placed: b.placed, not_placed: b.students - b.placed }, note: `· ${rateText(b.placement_rate, min)}` }))} />
          )}
        </Widget>
        <Widget title="Placement by CGPA">
          {p.by_cgpa.length === 0 ? <Empty>No students yet.</Empty> : (
            <StackedBars label="Students by CGPA" series={[{ key: 'placed', label: 'Placed', cls: 'bg-emerald-500' }, { key: 'not_placed', label: 'Not placed yet', cls: 'bg-slate-300' }]}
              rows={p.by_cgpa.map((b) => ({ key: b.band, label: b.band, values: { placed: b.placed, not_placed: b.students - b.placed }, note: `· ${rateText(b.placement_rate, min)}` }))} />
          )}
        </Widget>
      </div>

      <Widget title="Company-wise applications">
        {companiesWith.length === 0 ? <Empty>No applications yet, so there is nothing to compare between companies.</Empty> : (
          <>
            <StackedBars label="Applications by company" series={OUTCOME_SERIES}
              rows={companiesWith.slice(0, 10).map((c) => ({
                key: c.company, label: c.company, values: { in_process: c.shortlisted, selected: c.selected, rejected: c.rejected, other: c.applications - c.shortlisted - c.selected - c.rejected },
              }))} />
            <p className="mt-3 text-xs text-slate-500">{r.companies.length - companiesWith.length} of {r.companies.length} companies have no applications yet.</p>
          </>
        )}
      </Widget>

      <Widget title="Job-wise applications">
        {jobsWith.length === 0 ? <Empty>No applications yet.</Empty> : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <caption className="sr-only">Applications by job</caption>
                <thead className="text-xs uppercase text-slate-500">
                  <tr>{['Job', 'Company', 'Applications', 'Awaiting', 'In process', 'Selected', 'Rejected', 'Withdrawn'].map((h) => <th key={h} scope="col" className="py-1 pr-4">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {jobsWith.slice(0, JOB_ROWS_SHOWN).map((j) => (
                    <tr key={j.job_id}>
                      <td className="py-1.5 pr-4 font-medium text-slate-900">{j.title}{j.status === 'closed' ? <span className="ml-1 text-xs font-normal text-slate-500">(closed)</span> : null}</td>
                      <td className="py-1.5 pr-4">{j.company}</td>
                      <td className="py-1.5 pr-4 font-medium">{j.applications}</td>
                      <td className="py-1.5 pr-4">{j.awaiting_review}</td>
                      <td className="py-1.5 pr-4">{j.in_process}</td>
                      <td className="py-1.5 pr-4">{j.selected}</td>
                      <td className="py-1.5 pr-4">{j.rejected}</td>
                      <td className="py-1.5 pr-4">{j.withdrawn}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              {jobsWith.length > JOB_ROWS_SHOWN ? `Showing the ${JOB_ROWS_SHOWN} busiest of ${jobsWith.length} jobs with applications. ` : ''}
              {r.jobs.length - jobsWith.length} of {r.jobs.length} jobs have no applications yet. The full list is in the Jobs export below.
            </p>
          </>
        )}
      </Widget>

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Selected students" to="/coordinator/students?stage=placed">
          {r.selected_students.length === 0 ? <Empty>No student has been selected yet.</Empty> : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <caption className="sr-only">Selected students</caption>
                <thead className="text-xs uppercase text-slate-500"><tr>{['Student', 'Company', 'Job', 'Selected'].map((h) => <th key={h} scope="col" className="py-1 pr-4">{h}</th>)}</tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {r.selected_students.map((s) => (
                    <tr key={`${s.student_id}-${s.company}-${s.job_title}`}>
                      <td className="py-1.5 pr-4"><Link to={`/coordinator/students/${s.student_id}`} className="font-medium text-indigo-700 hover:underline">{s.name}</Link><span className="block text-xs text-slate-500">{s.branch ?? 'Branch not set'}{s.cgpa != null ? ` · CGPA ${s.cgpa}` : ''}</span></td>
                      <td className="py-1.5 pr-4">{s.company}</td>
                      <td className="py-1.5 pr-4">{s.job_title}</td>
                      <td className="py-1.5 pr-4">{formatDay(s.selected_on)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Widget>

        <Widget title="Common skill gaps">
          {r.skill_gaps.length === 0 ? <Empty>No gaps to show: either there are no students yet, or every student has the skills open jobs ask for.</Empty> : (
            <>
              <p className="mb-3 text-sm text-slate-600">Skills that open jobs ask for, with the number of students who do not have them.</p>
              <BarList label="Students lacking each skill" max={p.total_students}
                rows={r.skill_gaps.map((g) => ({ key: g.skill, label: g.skill, value: g.students_lacking, note: `of ${p.total_students} · ${g.jobs_requiring} open jobs`, cls: 'bg-amber-500' }))} />
            </>
          )}
        </Widget>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Placement progress" to="/coordinator/progress">
          <BarList label="Students reaching each milestone" max={Math.max(1, r.progress.total_students)} rows={r.progress.funnel.map((s) => ({ key: s.key, label: s.label, value: s.count, note: `(${s.percent}%)` }))} />
        </Widget>
        <Widget title="Interview results">
          {interviews.total === 0 ? <Empty>No interviews recorded yet.</Empty> : (
            <>
              <StackedBars label="Interview results" series={[{ key: 'passed', label: 'Passed', cls: 'bg-emerald-500' }, { key: 'not_cleared', label: 'Not cleared', cls: 'bg-red-500' }, { key: 'pending', label: 'Result pending', cls: 'bg-slate-400' }]}
                rows={[{ label: 'All interviews', values: { passed: interviews.passed, not_cleared: interviews.not_cleared, pending: interviews.pending } }]} />
              <p className="mt-3 text-sm text-slate-700">Pass rate: {interviews.pass_rate === null ? 'not enough results yet' : `${interviews.pass_rate}%`}</p>
            </>
          )}
        </Widget>
      </div>
    </div>
  )
}

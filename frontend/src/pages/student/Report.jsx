import { useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadMyReport, getMyReport } from '../../api/reports'
import { StatusBadge } from '../../components/applications/StatusParts'
import { BarList, StackedBars } from '../../components/charts/Charts'
import { ErrorNote } from '../../components/coordinator/Parts'
import Widget, { Bar, Empty } from '../../components/dashboard/Widget'
import { primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { STATUS, STATUS_BAR, formatDay, formatWhen, STAGES } from '../../utils/applications'
import { STAGE_STYLE } from '../../utils/coordinator'
import { getErrorMessage } from '../../utils/errors'

function Tile({ label, value, hint }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export default function StudentReport() {
  const { data, error, loading, reload } = useLoad(getMyReport, 'report')
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')

  const download = async () => {
    setDownloading(true)
    setDownloadError('')
    try {
      await downloadMyReport()
    } catch (err) {
      setDownloadError(getErrorMessage(err))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My placement report</h1>
          <p className="text-sm text-slate-600">
            {data ? `${data.student.name}${data.student.branch ? ` · ${data.student.branch}` : ''} · ` : ''}
            Counted from your records when you open this page.
          </p>
        </div>
        <div className="flex gap-2 print:hidden">
          <button type="button" className={secondaryButton} onClick={() => window.print()}>Print / save as PDF</button>
          <button type="button" className={primaryButton} onClick={download} disabled={downloading || !data}>{downloading ? 'Preparing…' : 'Download CSV'}</button>
        </div>
      </div>

      <div className="mt-4 space-y-3" aria-live="polite">
        {error && <ErrorNote>{error} <button type="button" className="underline" onClick={reload}>Try again</button></ErrorNote>}
        <ErrorNote>{downloadError}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Preparing your report…</p>}
      </div>
      {data && <Body r={data} />}
    </div>
  )
}

function Body({ r }) {
  const s = r.summary
  const i = r.interviews
  const failedSection = (name) => r.errors?.[name]
  const statusRows = r.status_distribution.filter((d) => d.count > 0).map((d) => ({ key: d.status, label: STATUS[d.status].label, value: d.count, cls: STATUS_BAR[d.status] }))

  return (
    <div className="mt-2 space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-600">Where you stand:</span>
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${STAGE_STYLE[s.outcome] ?? STAGE_STYLE.not_applied}`}>{s.outcome_label}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5" aria-label="Summary">
        <Tile label="Applications" value={s.total} hint={s.withdrawn ? `${s.active} active, ${s.withdrawn} withdrawn` : `${s.active} active`} />
        <Tile label="In process" value={s.in_process} hint="Shortlisted or in a round" />
        <Tile label="Selected" value={s.selected} />
        <Tile label="Rejected" value={s.rejected} />
        <Tile label="Interviews" value={i.total} hint={i.pass_rate === null ? 'No results recorded yet' : `${i.pass_rate}% passed`} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Application status">
          {statusRows.length === 0 ? (
            <Empty>You have not applied to any job yet. <Link to="/student/recommendations" className="font-medium text-indigo-600 hover:underline">See recommended jobs →</Link></Empty>
          ) : (
            <BarList rows={statusRows} label="Applications by status" />
          )}
        </Widget>

        <Widget title="Interview results">
          {i.total === 0 ? (
            <Empty>No interviews recorded. Add them on each application to keep every round in one place.</Empty>
          ) : (
            <>
              <StackedBars label="Interview results" series={[
                { key: 'passed', label: 'Passed', cls: 'bg-emerald-500' }, { key: 'not_cleared', label: 'Not cleared', cls: 'bg-red-500' }, { key: 'pending', label: 'Result pending', cls: 'bg-slate-400' },
              ]} rows={[{ label: 'All interviews', values: { passed: i.passed, not_cleared: i.not_cleared, pending: i.pending } }]} />
              <p className="mt-3 text-sm text-slate-700">
                {i.upcoming} upcoming · pass rate {i.pass_rate === null ? 'not known yet (no results recorded)' : `${i.pass_rate}% of interviews with a result`}
              </p>
            </>
          )}
        </Widget>
      </div>

      <Widget title="My applications" to="/student/applications">
        {r.applications.length === 0 ? <Empty>No applications yet.</Empty> : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <caption className="sr-only">My applications</caption>
              <thead className="text-xs uppercase text-slate-500">
                <tr>{['Job', 'Company', 'Status', 'Applied', 'Interviews'].map((h) => <th key={h} scope="col" className="py-1 pr-4">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {r.applications.map((a) => (
                  <tr key={a.id}>
                    <td className="py-2 pr-4 font-medium text-slate-900"><Link to={`/student/applications/${a.id}`} className="hover:text-indigo-600">{a.job_title}</Link></td>
                    <td className="py-2 pr-4">{a.company}</td>
                    <td className="py-2 pr-4"><StatusBadge status={a.status} /></td>
                    <td className="py-2 pr-4">{formatDay(a.applied_at)}</td>
                    <td className="py-2 pr-4">{a.interviews}{a.next_interview ? <span className="block text-xs text-slate-500">next: {formatWhen(a.next_interview)}</span> : null}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Widget>

      {i.items.length > 0 && (
        <Widget title="Interviews" to="/student/interviews">
          <ul className="divide-y divide-slate-100 text-sm">
            {i.items.map((x) => (
              <li key={x.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{STAGES[x.stage] ?? x.stage} · {x.job_title} · {x.company} · {formatWhen(x.scheduled_at)}</span>
                <span className="font-medium">{x.outcome === 'passed' ? 'Passed' : x.outcome === 'failed' ? 'Not cleared' : 'Result pending'}</span>
              </li>
            ))}
          </ul>
        </Widget>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <Widget title="Recommended jobs" to="/student/recommendations" error={failedSection('recommendations')}>
          {r.recommended && (r.recommended.top.length === 0 ? <Empty>No open jobs to recommend right now.</Empty> : (
            <>
              <p className="mb-3 text-sm text-slate-600">{r.recommended.eligible} of {r.recommended.open_jobs} open jobs match your eligibility.</p>
              <ul className="divide-y divide-slate-100">
                {r.recommended.top.map((j) => (
                  <li key={j.job_id} className="py-2">
                    <div className="flex items-baseline justify-between gap-3 text-sm">
                      <Link to={`/student/jobs/${j.job_id}`} className="min-w-0 truncate font-medium text-slate-900 hover:text-indigo-600">{j.title} · {j.company}</Link>
                      <span className="shrink-0 text-slate-600">{j.match_score}% match</span>
                    </div>
                    <Bar value={j.match_score} label={`Match with ${j.title}`} />
                    <p className="mt-1 text-xs text-slate-500">{j.eligibility === 'ELIGIBLE' ? 'You are eligible' : j.eligibility === 'INCOMPLETE_PROFILE' ? 'Complete your profile to check eligibility' : 'Not eligible yet'}{j.already_applied ? ' · applied' : ''}</p>
                  </li>
                ))}
              </ul>
            </>
          ))}
        </Widget>

        <Widget title="Skill gaps" to="/student/skill-gap" error={failedSection('skill_gaps')}>
          {r.skill_gaps && (!r.skill_gaps.student_has_skills ? (
            <Empty>Add your skills to your profile to see which ones jobs ask for that you do not have yet.</Empty>
          ) : r.skill_gaps.top_missing.length === 0 ? (
            <Empty>No skills missing for the jobs that suit you best. Well done.</Empty>
          ) : (
            <>
              <p className="mb-3 text-sm text-slate-600">Skills missing from the {r.skill_gaps.based_on_jobs} jobs that suit you best:</p>
              <BarList label="Missing skills" unit=" jobs" rows={r.skill_gaps.top_missing.map((m) => ({ label: m.name, value: m.jobs_needing, cls: 'bg-amber-500' }))} />
            </>
          ))}
        </Widget>
      </div>

      <Widget title="Placement progress" error={failedSection('progress')}>
        {r.progress && (
          <>
            <div className="flex items-baseline justify-between text-sm"><span>{r.progress.done} of {r.progress.total} steps done</span><span className="font-medium">{r.progress.percent}%</span></div>
            <div className="mt-1"><Bar value={r.progress.percent} label="Placement progress" /></div>
            <ol className="mt-4 space-y-1.5 text-sm">
              {r.progress.milestones.map((m) => (
                <li key={m.key} className={m.done ? 'text-emerald-700' : 'text-slate-600'}>
                  {m.done ? '✓' : '○'} {m.label} <span className="text-xs text-slate-500">— {m.detail}</span>
                </li>
              ))}
            </ol>
            {r.progress.next_step && <p className="mt-3 text-sm text-slate-700">Next: <Link to={r.progress.next_step.link} className="font-medium text-indigo-600 hover:underline">{r.progress.next_step.label}</Link></p>}
          </>
        )}
      </Widget>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { StatusBadge } from '../applications/StatusParts'
import { STAGES, STATUS, formatWhen } from '../../utils/applications'
import { deadlineText } from '../../utils/dates'
import Widget, { Bar, Empty } from './Widget'

const ELIGIBILITY = {
  ELIGIBLE: { text: '✓ Eligible', cls: 'bg-emerald-100 text-emerald-800' },
  NOT_ELIGIBLE: { text: '✗ Not eligible', cls: 'bg-red-100 text-red-800' },
  INCOMPLETE_PROFILE: { text: '? Incomplete profile', cls: 'bg-amber-100 text-amber-800' },
}

function ScorePill({ score }) {
  const cls = score >= 70 ? 'bg-emerald-100 text-emerald-800' : score >= 40 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
  return <span className={`rounded-full px-2 py-0.5 text-xs font-bold ${cls}`} aria-label={`${score} percent match`}>{score}%</span>
}

function JobRow({ job, showEligibility = true, extra }) {
  return (
    <li className="flex items-start justify-between gap-3 py-2.5">
      <div className="min-w-0">
        <Link to={`/student/jobs/${job.job_id}`} className="block truncate text-sm font-medium text-slate-900 hover:text-indigo-600">{job.title}</Link>
        <p className="truncate text-xs text-slate-500">
          {job.company}{job.location ? ` · ${job.location}` : ''}{extra ? ` · ${extra}` : ''}
        </p>
        <div className="mt-1 flex flex-wrap gap-1.5 text-xs">
          {showEligibility && <span className={`rounded-full px-2 py-0.5 font-medium ${ELIGIBILITY[job.eligibility].cls}`}>{ELIGIBILITY[job.eligibility].text}</span>}
          {job.already_applied && <span className="rounded-full bg-sky-100 px-2 py-0.5 font-medium text-sky-800">Applied</span>}
        </div>
      </div>
      <ScorePill score={job.match_score} />
    </li>
  )
}

// ---------------------------------------------------------------- KPI cards
export function KpiCards({ d, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" role="status" aria-label="Loading summary">
        {[0, 1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded-lg bg-slate-200" />)}
      </div>
    )
  }
  const apps = d.applications
  const movedForward = apps ? Object.entries(apps.by_status).filter(([s]) => !['applied', 'rejected', 'withdrawn'].includes(s)).reduce((n, [, c]) => n + c, 0) : 0
  const cards = [
    { key: 'profile', to: '/student/profile', label: 'Profile completion', value: d.profile ? `${d.profile.score}%` : '–', note: d.profile ? (d.profile.missing.length ? `${d.profile.missing.length} item${d.profile.missing.length === 1 ? '' : 's'} left` : 'Complete') : 'Unavailable', bar: d.profile?.score },
    { key: 'eligible', to: '/student/recommendations', label: 'Eligible jobs', value: d.recommendations ? d.recommendations.eligible : '–', note: d.recommendations ? `of ${d.recommendations.open_jobs} open jobs` : 'Unavailable' },
    { key: 'apps', to: '/student/applications', label: 'Active applications', value: apps ? apps.active : '–', note: apps ? (movedForward ? `${movedForward} moved forward` : 'None shortlisted yet') : 'Unavailable' },
    { key: 'interviews', to: '/student/interviews', label: 'Upcoming interviews', value: d.interviews ? d.interviews.upcoming_count : '–', note: d.interviews ? (d.interviews.upcoming[0] ? `Next: ${formatWhen(d.interviews.upcoming[0].scheduled_at)}` : 'Nothing scheduled') : 'Unavailable' },
  ]
  return (
    <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Summary">
      {cards.map((c) => (
        <li key={c.key}>
          <Link to={c.to} className="block h-full rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-indigo-300 hover:shadow">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{c.label}</p>
            <p className="mt-1 text-3xl font-bold text-slate-900">{c.value}</p>
            {c.bar !== undefined && <div className="mt-1.5"><Bar value={c.bar} label="Profile completion" /></div>}
            <p className="mt-1 truncate text-xs text-slate-500">{c.note}</p>
          </Link>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------- progress
export function ProgressCard({ d, loading, error, onRetry }) {
  const p = d?.progress
  return (
    <Widget title="Your placement progress" loading={loading} error={error} onRetry={onRetry}>
      {p && (
        <>
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-600">{p.done} of {p.total} milestones</span>
            <span className="font-bold text-indigo-600">{p.percent}%</span>
          </div>
          <div className="mt-1.5"><Bar value={p.percent} label="Placement progress" color="bg-indigo-600" /></div>
          <ol className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3" aria-label="Milestones">
            {p.milestones.map((m) => (
              <li key={m.key}>
                <Link to={m.link} className={`flex items-start gap-2 rounded-md border p-2.5 text-sm ${m.done ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-white hover:bg-slate-50'}`}>
                  <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${m.done ? 'bg-emerald-500 text-white' : 'border border-slate-300 text-slate-400'}`} aria-hidden="true">{m.done ? '✓' : ''}</span>
                  <span className="min-w-0">
                    <span className="block font-medium text-slate-900">{m.label}{m.done && <span className="sr-only"> (done)</span>}</span>
                    <span className="block truncate text-xs text-slate-500">{m.detail}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </>
      )}
    </Widget>
  )
}

// ---------------------------------------------------------------- recommended jobs
export function RecommendedJobs({ d, loading, error, onRetry }) {
  const r = d?.recommendations
  return (
    <Widget title="Recommended for you" to="/student/recommendations" linkLabel="See all recommendations →" loading={loading} error={error} onRetry={onRetry}>
      {r && (r.open_jobs === 0 ? (
        <Empty>There are no open jobs right now. Check back soon.</Empty>
      ) : (
        <>
          <ul className="divide-y divide-slate-100" aria-label="Recommended jobs">
            {r.top.map((j) => <JobRow key={j.job_id} job={j} />)}
          </ul>
          {r.hints.length > 0 && (
            <div className="mt-3 rounded-md bg-amber-50 p-3 text-xs text-amber-900">
              <p className="font-medium">Improve these matches:</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">{r.hints.slice(0, 2).map((h) => <li key={h}>{h}</li>)}</ul>
              <Link to="/student/profile" className="mt-1 inline-block font-medium underline">Update my profile →</Link>
            </div>
          )}
        </>
      ))}
    </Widget>
  )
}

// ---------------------------------------------------------------- eligible opportunities
export function Opportunities({ d, loading, error, onRetry }) {
  const o = d?.opportunities
  return (
    <Widget title="Eligible opportunities" to="/student/recommendations?eligible_only=true" linkLabel="See all →" loading={loading} error={error} onRetry={onRetry}>
      {o && (
        <>
          <p className="text-sm text-slate-600">
            You meet the requirements for <strong className="text-slate-900">{o.eligible_count}</strong> open job{o.eligible_count === 1 ? '' : 's'} ({o.eligible_percent}%).
          </p>
          {o.items.length === 0 ? (
            <div className="mt-2">
              <Empty>
                {o.eligible_count === 0
                  ? 'No eligible jobs yet. Add your CGPA, branch and skills to your profile so eligibility can be checked.'
                  : 'You have already applied to all the jobs you are eligible for.'}
              </Empty>
            </div>
          ) : (
            <ul className="mt-1 divide-y divide-slate-100" aria-label="Eligible jobs">
              {o.items.map((j) => <JobRow key={j.job_id} job={j} showEligibility={false} extra={deadlineText(j.deadline)} />)}
            </ul>
          )}
          {o.closing_soon.length > 0 && (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-900">Closing soon</h3>
              <ul className="mt-1 divide-y divide-amber-100" aria-label="Closing soon">
                {o.closing_soon.map((j) => (
                  <li key={j.job_id} className="flex items-center justify-between gap-2 py-1.5 text-sm">
                    <Link to={`/student/jobs/${j.job_id}`} className="truncate font-medium text-slate-900 hover:text-indigo-600">{j.title} · {j.company}</Link>
                    <span className="shrink-0 text-xs font-medium text-amber-800">{deadlineText(j.deadline)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </Widget>
  )
}

// ---------------------------------------------------------------- applications
export function ApplicationsCard({ d, loading, error, onRetry }) {
  const a = d?.applications
  const funnel = d?.statistics?.application_funnel
  const max = funnel ? Math.max(1, ...funnel.map((f) => f.count)) : 1
  return (
    <Widget title="Applications" to="/student/applications" loading={loading} error={error} onRetry={onRetry}>
      {a && (a.total === 0 ? (
        <Empty>You have not applied to any job yet. <Link to="/student/jobs" className="font-medium text-indigo-600 hover:underline">Find jobs →</Link></Empty>
      ) : (
        <>
          {funnel && (
            <ul className="space-y-1.5" aria-label="Applications by status">
              {funnel.filter((f) => f.count > 0).map((f) => (
                <li key={f.status} className="flex items-center gap-2 text-xs">
                  <span className="w-28 shrink-0 text-slate-600">{STATUS[f.status].label}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className="h-full bg-indigo-500" style={{ width: `${(f.count / max) * 100}%` }} /></div>
                  <span className="w-5 text-right font-semibold text-slate-800">{f.count}</span>
                </li>
              ))}
            </ul>
          )}
          <ul className="mt-3 divide-y divide-slate-100" aria-label="Recent applications">
            {a.recent.map((x) => (
              <li key={x.id} className="flex items-center justify-between gap-2 py-2">
                <Link to={`/student/applications/${x.id}`} className="min-w-0 truncate text-sm text-slate-900 hover:text-indigo-600">{x.job_title} <span className="text-slate-500">· {x.company}</span></Link>
                <StatusBadge status={x.status} />
              </li>
            ))}
          </ul>
        </>
      ))}
    </Widget>
  )
}

// ---------------------------------------------------------------- interviews
export function InterviewsCard({ d, loading, error, onRetry }) {
  const i = d?.interviews
  return (
    <Widget title="Interviews" to="/student/interviews" linkLabel="Interview tracker →" loading={loading} error={error} onRetry={onRetry}>
      {i && (
        <>
          {i.needs_result > 0 && (
            <p role="status" className="mb-2 rounded-md bg-amber-50 p-2.5 text-xs text-amber-900">
              {i.needs_result} past interview{i.needs_result === 1 ? ' has' : 's have'} no result yet. <Link to="/student/interviews?tab=past" className="font-medium underline">Update</Link>
            </p>
          )}
          {i.upcoming.length === 0 ? (
            <Empty>
              No upcoming interviews. <Link to="/student/chat?ask=How%20should%20I%20prepare%20for%20a%20technical%20interview%3F" className="font-medium text-indigo-600 hover:underline">Prepare for one →</Link>
            </Empty>
          ) : (
            <ul className="divide-y divide-slate-100" aria-label="Upcoming interviews">
              {i.upcoming.map((x) => (
                <li key={x.id} className="py-2">
                  <Link to={`/student/interviews/${x.id}`} className="block text-sm font-medium text-slate-900 hover:text-indigo-600">{formatWhen(x.scheduled_at)}</Link>
                  <p className="text-xs text-slate-500">{STAGES[x.stage]} · {x.job_title} at {x.company}</p>
                </li>
              ))}
            </ul>
          )}
          {i.total > 0 && (
            <p className="mt-2 text-xs text-slate-500">
              Recorded: {i.total} · passed {i.passed} · not cleared {i.not_cleared} · result pending {i.pending}
            </p>
          )}
        </>
      )}
    </Widget>
  )
}

// ---------------------------------------------------------------- resume
export function ResumeCard({ d, loading, error, onRetry }) {
  const r = d?.resume
  return (
    <Widget title="Resume" to="/student/resume/analysis" linkLabel={r?.uploaded ? 'Full analysis →' : undefined} loading={loading} error={error} onRetry={onRetry}>
      {r && (r.uploaded ? (
        <>
          <p className="truncate text-sm font-medium text-slate-900">{r.filename}</p>
          <p className="text-xs text-slate-500">Uploaded {r.uploaded_at ? new Date(r.uploaded_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''}</p>
          {r.completeness_score !== null && (
            <div className="mt-2">
              <div className="flex justify-between text-xs text-slate-600"><span>Completeness</span><span className="font-semibold">{r.completeness_score}/100</span></div>
              <div className="mt-1"><Bar value={r.completeness_score} label="Resume completeness" /></div>
              <p className="mt-1 text-xs text-slate-500">{r.skills_detected} skills recognised</p>
            </div>
          )}
          {r.top_suggestions.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-700" aria-label="Resume suggestions">
              {r.top_suggestions.map((s) => <li key={s}>{s}</li>)}
            </ul>
          )}
        </>
      ) : (
        <Empty>
          No resume uploaded. A resume unlocks skill detection, a completeness review and better job matching.{' '}
          <Link to="/student/resume" className="font-medium text-indigo-600 hover:underline">Upload one →</Link>
        </Empty>
      ))}
    </Widget>
  )
}

// ---------------------------------------------------------------- skill gaps
export function SkillGapsCard({ d, loading, error, onRetry }) {
  const g = d?.skill_gaps
  return (
    <Widget title="Skill gaps" to="/student/skill-gap" linkLabel="Skill gap page →" loading={loading} error={error} onRetry={onRetry}>
      {g && (!g.student_has_skills ? (
        <Empty>Add your skills to your profile to see which skills your best-matching jobs ask for that you lack. <Link to="/student/profile" className="font-medium text-indigo-600 hover:underline">Add skills →</Link></Empty>
      ) : g.top_missing.length === 0 ? (
        <Empty>No required skills are missing across your {g.based_on_jobs} best-matching jobs.</Empty>
      ) : (
        <>
          <p className="text-xs text-slate-500">Skills asked for by your {g.based_on_jobs} best-matching jobs that you do not have:</p>
          <ul className="mt-2 space-y-1.5" aria-label="Skills to learn">
            {g.top_missing.map((m) => (
              <li key={m.name} className="flex items-center justify-between gap-2 text-sm">
                <span className="font-medium text-slate-900">{m.name}</span>
                <span className="truncate text-xs text-slate-500" title={m.example_jobs.join(', ')}>needed by {m.jobs_needing} job{m.jobs_needing === 1 ? '' : 's'}</span>
              </li>
            ))}
          </ul>
          {g.closest_job && (
            <Link to={`/student/skill-gap?job_id=${g.closest_job.job_id}`} className="mt-3 block rounded-md border border-indigo-200 bg-indigo-50 p-3 text-sm hover:bg-indigo-100">
              <span className="font-medium text-indigo-900">Closest opportunity: {g.closest_job.title} at {g.closest_job.company}</span>
              <span className="block text-xs text-indigo-800">{g.closest_job.missing_skills.length === 1 ? 'Only one skill stands' : `Only ${g.closest_job.missing_skills.length} skills stand`} in the way: {g.closest_job.missing_skills.join(', ')}</span>
            </Link>
          )}
        </>
      ))}
    </Widget>
  )
}

// ---------------------------------------------------------------- statistics
export function StatisticsCard({ d, loading, error, onRetry }) {
  const s = d?.statistics
  const max = s ? Math.max(1, ...s.in_demand_skills.map((x) => x.jobs)) : 1
  return (
    <Widget title="Placement statistics" loading={loading} error={error} onRetry={onRetry}>
      {s && (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ['Open jobs', s.open_jobs], ['Companies hiring', s.companies_hiring],
              ['Closing this week', s.closing_this_week], ['You are eligible for', `${s.eligible_percent}%`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-md bg-slate-50 p-3">
                <dt className="text-xs text-slate-500">{label}</dt>
                <dd className="text-xl font-bold text-slate-900">{value}</dd>
              </div>
            ))}
          </dl>
          <h3 className="mt-4 text-sm font-semibold text-slate-900">Skills in demand right now</h3>
          {s.in_demand_skills.length === 0 ? (
            <div className="mt-1"><Empty>No open jobs to analyse.</Empty></div>
          ) : (
            <ul className="mt-2 space-y-1.5" aria-label="Skills in demand">
              {s.in_demand_skills.map((x) => (
                <li key={x.name} className="flex items-center gap-2 text-xs">
                  <span className="w-28 shrink-0 truncate text-slate-700">{x.name}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100"><div className={`h-full ${x.you_have ? 'bg-emerald-500' : 'bg-slate-400'}`} style={{ width: `${(x.jobs / max) * 100}%` }} /></div>
                  <span className="w-16 shrink-0 text-right text-slate-600">{x.jobs} jobs</span>
                  <span className={`w-14 shrink-0 text-right font-medium ${x.you_have ? 'text-emerald-700' : 'text-slate-400'}`}>{x.you_have ? '✓ you have' : 'missing'}</span>
                </li>
              ))}
            </ul>
          )}
          {s.interview_pass_rate !== null && (
            <p className="mt-3 text-xs text-slate-600">Interviews with a recorded result: you cleared <strong>{s.interview_pass_rate}%</strong>.</p>
          )}
        </>
      )}
    </Widget>
  )
}

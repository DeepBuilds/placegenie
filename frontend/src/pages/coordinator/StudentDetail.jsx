import { Link, useParams } from 'react-router-dom'
import { getStudentDetail } from '../../api/admin'
import { OutcomeBadge } from '../../components/applications/StatusParts'
import { ErrorNote, PageHeader, StageBadge, StatusControl } from '../../components/coordinator/Parts'
import { Bar } from '../../components/dashboard/Widget'
import Section from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { STAGES, formatDay, formatWhen } from '../../utils/applications'

function Fact({ label, children }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-900">{children ?? '—'}</dd>
    </div>
  )
}

export default function StudentDetail() {
  const { id } = useParams()
  const { data, error, loading, reload } = useLoad(() => getStudentDetail(id), id, { notFound: 'This student does not exist.' })

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <Link to="/coordinator/students" className="text-sm font-medium text-indigo-600 hover:underline">← All students</Link>
      <div className="mt-2">
        <ErrorNote>{error}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading the placement profile…</p>}
      </div>
      {data && <Body d={data} reload={reload} />}
    </div>
  )
}

function Body({ d, reload }) {
  const p = d.profile
  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
  return (
    <div className="space-y-5">
      <PageHeader title={p.full_name} subtitle={`${p.email}${p.college ? ` · ${p.college}` : ''}`}>
        <StageBadge stage={d.stage} />
      </PageHeader>
      {Object.keys(d.errors).length > 0 && <ErrorNote>Some sections could not be loaded: {Object.keys(d.errors).join(', ')}.</ErrorNote>}

      <Section title="Profile" subtitle={`${p.completeness.score}% complete`}>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Fact label="Branch">{p.branch?.name}</Fact>
          <Fact label="Year / semester">{p.year ? `Year ${p.year}, semester ${p.semester ?? '—'}` : null}</Fact>
          <Fact label="CGPA">{p.cgpa}</Fact>
          <Fact label="Backlogs">{p.backlogs}</Fact>
        </dl>
        <div className="mt-3"><Bar value={p.completeness.score} label="Profile completeness" /></div>
        {p.completeness.missing.length > 0 && <p className="mt-2 text-sm text-slate-600">Missing: {p.completeness.missing.join(', ')}</p>}
        <h3 className="mt-4 text-sm font-semibold text-slate-800">Skills</h3>
        <p className="text-sm text-slate-700">{p.skills.length ? p.skills.map((s) => s.name).join(', ') : 'No skills added.'}</p>
        <h3 className="mt-3 text-sm font-semibold text-slate-800">Projects, experience and certifications</h3>
        <p className="text-sm text-slate-700">
          {plural(p.projects.length, 'project')} · {plural(p.experiences.length, 'experience')} · {plural(p.certifications.length, 'certification')}
        </p>
      </Section>

      <div className="grid gap-5 md:grid-cols-2">
        <Section title="Resume">
          {d.resume?.uploaded ? (
            <p className="text-sm text-slate-700">{d.resume.filename} · score {d.resume.completeness_score ?? '—'}/100 · {d.resume.skills_detected ?? 0} skills detected</p>
          ) : (
            <p className="text-sm text-slate-600">No resume uploaded.</p>
          )}
        </Section>
        <Section title="Placement progress" subtitle={d.progress ? `${d.progress.done} of ${d.progress.total} steps done` : undefined}>
          {d.progress && (
            <>
              <Bar value={d.progress.percent} label="Placement progress" />
              <ol className="mt-3 space-y-1 text-sm">
                {d.progress.milestones.map((m) => (
                  <li key={m.key} className={m.done ? 'text-emerald-700' : 'text-slate-600'}>
                    {m.done ? '✓' : '○'} {m.label} <span className="text-xs text-slate-500">— {m.detail}</span>
                  </li>
                ))}
              </ol>
            </>
          )}
        </Section>
      </div>

      {d.skill_gaps?.top_missing.length > 0 && (
        <Section title="Skill gaps" subtitle={`Based on ${d.skill_gaps.based_on_jobs} jobs that suit the student best`}>
          <p className="text-sm text-slate-700">{d.skill_gaps.top_missing.map((s) => `${s.name} (${s.jobs_needing} jobs)`).join(', ')}</p>
        </Section>
      )}

      <Section title="Applications" subtitle="Change an application's official status here.">
        {d.applications.items.length === 0 ? (
          <p className="text-sm text-slate-600">This student has not applied to any job.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {d.applications.items.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-medium text-slate-900">{a.job.title}</p>
                  <p className="text-sm text-slate-600">{a.job.company} · applied {formatDay(a.applied_at)}</p>
                </div>
                <StatusControl application={a} onChanged={reload} />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Interviews">
        {d.interviews.items.length === 0 ? (
          <p className="text-sm text-slate-600">No interviews recorded.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {d.interviews.items.map((i) => (
              <li key={i.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>{STAGES[i.stage] ?? i.stage} · {i.application.job.title} · {formatWhen(i.scheduled_at)}</span>
                <OutcomeBadge outcome={i.outcome} />
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}

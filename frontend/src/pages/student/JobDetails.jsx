import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCompany, getJob } from '../../api/jobs'
import SkillChips from '../../components/jobs/SkillChips'
import { getErrorMessage } from '../../utils/errors'
import {
  formatBacklogs,
  formatCgpa,
  formatDeadline,
  formatExperience,
  formatJobType,
} from '../../utils/jobs'

function Card({ title, children }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  )
}

function Requirement({ label, children }) {
  return (
    <div className="flex justify-between gap-4 py-2 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-900">{children}</dd>
    </div>
  )
}

export default function JobDetails() {
  const { id } = useParams()
  const [state, setState] = useState({ id: null, job: null, company: null, error: '', notFound: false })

  useEffect(() => {
    let cancelled = false
    getJob(id)
      .then(async (job) => {
        // Company info is a nice-to-have: the page still works if this call fails.
        const company = await getCompany(job.company.id).catch(() => null)
        if (!cancelled) setState({ id, job, company, error: '', notFound: false })
      })
      .catch((err) => {
        if (cancelled) return
        const notFound = err.response?.status === 404
        setState({ id, job: null, company: null, notFound, error: notFound ? '' : getErrorMessage(err) })
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (state.id !== id) return <p className="p-8 text-center text-slate-500">Loading job…</p>

  if (state.notFound || state.error)
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p role="alert" className="text-slate-700">
          {state.notFound ? 'This job does not exist or is no longer open.' : state.error}
        </p>
        <Link to="/student/jobs" className="mt-4 inline-block text-indigo-600 hover:underline">
          ← Back to jobs
        </Link>
      </div>
    )

  const { job, company } = state
  const required = job.skills.filter((s) => s.importance === 'required')
  const preferred = job.skills.filter((s) => s.importance === 'preferred')

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-4 py-8">
      <Link to="/student/jobs" className="text-sm text-indigo-600 hover:underline">
        ← Back to jobs
      </Link>

      <header className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{job.title}</h1>
            <p className="mt-1 text-slate-600">
              {job.company.name}
              {job.location ? ` · ${job.location}` : ''}
            </p>
          </div>
          <div className="flex gap-2 text-xs font-medium">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">{formatJobType(job.job_type)}</span>
            {job.role && <span className="rounded-full bg-indigo-100 px-3 py-1 text-indigo-800">{job.role.name}</span>}
          </div>
        </div>
        <p className={`mt-3 text-sm ${job.is_expired ? 'font-medium text-red-600' : 'text-slate-600'}`}>
          {formatDeadline(job.deadline, job.is_expired)}
        </p>
      </header>

      {job.description && (
        <Card title="About the role">
          <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{job.description}</p>
        </Card>
      )}

      <div className="grid gap-5 md:grid-cols-2">
        <Card title="Eligibility requirements">
          <dl className="divide-y divide-slate-100">
            <Requirement label="Minimum CGPA">{formatCgpa(job.min_cgpa)}</Requirement>
            <Requirement label="Backlogs">{formatBacklogs(job.max_backlogs)}</Requirement>
            <Requirement label="Experience">{formatExperience(job.min_experience_months)}</Requirement>
            <Requirement label="Allowed branches">
              {job.allowed_branches.length === 0 ? (
                'All branches'
              ) : (
                <ul className="space-y-0.5">
                  {job.allowed_branches.map((b) => (
                    <li key={b.id}>{b.name}</li>
                  ))}
                </ul>
              )}
            </Requirement>
            <Requirement label="Required certifications">
              {job.required_certifications.length === 0 ? (
                'None'
              ) : (
                <ul className="space-y-0.5">
                  {job.required_certifications.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
            </Requirement>
          </dl>
        </Card>

        <Card title="Skills">
          {job.skills.length === 0 ? (
            <p className="text-sm text-slate-500">No specific skills listed.</p>
          ) : (
            <div className="space-y-4">
              {required.length > 0 && (
                <div>
                  <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Required</h3>
                  <SkillChips skills={required} />
                </div>
              )}
              {preferred.length > 0 && (
                <div>
                  <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Nice to have</h3>
                  <SkillChips skills={preferred} />
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card title={`About ${job.company.name}`}>
        <p className="text-sm text-slate-500">
          {[company?.industry ?? job.company.industry, company?.location ?? job.company.location]
            .filter(Boolean)
            .join(' · ')}
        </p>
        {company?.description && <p className="mt-2 text-sm leading-relaxed text-slate-700">{company.description}</p>}
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          {company?.website && (
            <a href={company.website} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
              Company website
            </a>
          )}
          <Link to={`/student/jobs?company_id=${job.company.id}`} className="text-indigo-600 hover:underline">
            See all jobs at {job.company.name}
            {company ? ` (${company.open_jobs})` : ''}
          </Link>
        </div>
      </Card>

      <p className="text-xs text-slate-500">
        PlaceGenie is an assistance tool. Hiring decisions are made only by the company and your placement officers.
      </p>
    </div>
  )
}

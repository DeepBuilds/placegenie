import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getJobs } from '../../api/jobs'
import SkillGapPanel from '../../components/jobs/SkillGapPanel'
import { inputClass } from '../../components/profile/Section'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { getErrorMessage } from '../../utils/errors'

export default function SkillGap() {
  const { get, update } = useUrlFilters()
  const jobId = get('job_id')
  const [jobs, setJobs] = useState({ status: 'loading', items: [], error: '' })

  useEffect(() => {
    let cancelled = false
    getJobs({ limit: 100, sort: 'title' })
      .then((page) => !cancelled && setJobs({ status: 'ready', items: page.items, error: '' }))
      .catch((err) => !cancelled && setJobs({ status: 'error', items: [], error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [])

  const selected = jobs.items.find((j) => String(j.id) === jobId)

  return (
    <div className="mx-auto max-w-4xl space-y-5 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Skill gap</h1>
        <p className="text-sm text-slate-600">
          Pick a job to see which of its skills you already have, which you are missing, and which to work on first.
        </p>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="gap-job" className="block text-xs font-medium text-slate-600">Job</label>
        <select id="gap-job" className={inputClass} value={jobId} disabled={jobs.status !== 'ready'}
          onChange={(e) => update({ job_id: e.target.value })}>
          <option value="">{jobs.status === 'loading' ? 'Loading jobs…' : 'Choose a job…'}</option>
          {jobs.items.map((j) => (
            <option key={j.id} value={j.id}>{j.title} · {j.company.name}</option>
          ))}
        </select>
        {jobs.status === 'error' && <p role="alert" className="mt-2 text-sm text-red-700">{jobs.error}</p>}
      </div>

      {jobId ? (
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" aria-label="Skill gap result">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-lg font-semibold text-slate-900">
              {selected ? `${selected.title} at ${selected.company.name}` : 'Selected job'}
            </h2>
            <Link to={`/student/jobs/${jobId}`} className="text-sm font-medium text-indigo-600 hover:underline">
              View job details →
            </Link>
          </div>
          <SkillGapPanel key={jobId} jobId={jobId} />
        </section>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          Choose a job above to compare it with your skills.
        </div>
      )}
    </div>
  )
}

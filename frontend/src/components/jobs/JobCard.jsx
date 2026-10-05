import { Link } from 'react-router-dom'
import { formatBacklogs, formatCgpa, formatDeadline, formatJobType } from '../../utils/jobs'
import SkillChips from './SkillChips'

export default function JobCard({ job }) {
  return (
    <article className="flex flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-slate-900">
            <Link to={`/student/jobs/${job.id}`} className="hover:text-indigo-600">
              {job.title}
            </Link>
          </h3>
          <p className="text-sm text-slate-600">
            <Link to={`/student/jobs?company_id=${job.company.id}`} className="hover:underline">
              {job.company.name}
            </Link>
            {job.location ? ` · ${job.location}` : ''}
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
          {formatJobType(job.job_type)}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-slate-600">
        <div>
          <dt className="inline text-slate-500">Min CGPA: </dt>
          <dd className="inline font-medium">{formatCgpa(job.min_cgpa)}</dd>
        </div>
        <div>
          <dt className="inline text-slate-500">Backlogs: </dt>
          <dd className="inline font-medium">{formatBacklogs(job.max_backlogs)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="inline text-slate-500">Branches: </dt>
          <dd className="inline font-medium">
            {job.allowed_branches.length === 0 ? 'All branches' : `${job.allowed_branches.length} eligible`}
          </dd>
        </div>
      </dl>

      <div className="mt-3">
        <SkillChips skills={job.skills} limit={5} />
      </div>

      <div className="mt-4 flex items-center justify-between pt-1 text-xs">
        <span className={job.is_expired ? 'font-medium text-red-600' : 'text-slate-500'}>
          {formatDeadline(job.deadline, job.is_expired)}
        </span>
        <Link to={`/student/jobs/${job.id}`} className="font-medium text-indigo-600 hover:underline">
          View details →
        </Link>
      </div>
    </article>
  )
}

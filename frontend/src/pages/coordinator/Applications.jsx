import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getApplications } from '../../api/admin'
import { getCompanies, getJobs } from '../../api/jobs'
import { ErrorNote, PageHeader, Pagination, StatusControl } from '../../components/coordinator/Parts'
import { inputClass, primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { STATUS, formatDay } from '../../utils/applications'

const LIMIT = 20
const chip = (on) => `rounded-full border px-3 py-1 text-sm ${on ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-100'}`

export default function Applications() {
  const { get, update, reset, query } = useUrlFilters()
  const [search, setSearch] = useState(get('q'))
  const offset = Number(get('offset')) || 0
  const status = get('status')
  const companyId = get('company_id')

  const { data, error, loading, reload } = useLoad(
    () => getApplications({ status, company_id: companyId, job_id: get('job_id'), q: get('q'), limit: LIMIT, offset }),
    query,
  )
  const { data: companies } = useLoad(() => getCompanies({ limit: 100 }), 'companies')
  const { data: jobs } = useLoad(() => getJobs({ company_id: companyId, limit: 100 }), `jobs-${companyId}`)

  const total = data ? Object.values(data.counts).reduce((a, b) => a + b, 0) : 0

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Applications" subtitle="Review applications and update their official placement status." />

      <form className="mt-5 grid gap-3 md:grid-cols-4" role="search" onSubmit={(e) => { e.preventDefault(); update({ q: search.trim() }) }}>
        <input type="search" aria-label="Search applications" placeholder="Student, job or company" value={search} maxLength={100} onChange={(e) => setSearch(e.target.value)} className={`${inputClass} mt-0`} />
        <select aria-label="Filter by company" value={companyId} onChange={(e) => update({ company_id: e.target.value, job_id: '' })} className={`${inputClass} mt-0`}>
          <option value="">All companies</option>
          {(companies?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select aria-label="Filter by job" value={get('job_id')} onChange={(e) => update({ job_id: e.target.value })} className={`${inputClass} mt-0`}>
          <option value="">All jobs</option>
          {(jobs?.items ?? []).map((j) => <option key={j.id} value={j.id}>{j.title}{companyId ? '' : ` · ${j.company.name}`}</option>)}
        </select>
        <div className="flex gap-2">
          <button type="submit" className={primaryButton}>Search</button>
          <button type="button" className={secondaryButton} onClick={() => { setSearch(''); reset() }}>Clear</button>
        </div>
      </form>

      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        <button type="button" aria-pressed={!status} onClick={() => update({ status: '' })} className={chip(!status)}>All{data ? ` (${total})` : ''}</button>
        {Object.keys(STATUS).map((s) => (
          <button key={s} type="button" aria-pressed={status === s} onClick={() => update({ status: s })} className={chip(status === s)}>
            {STATUS[s].label}{data?.counts[s] ? ` (${data.counts[s]})` : ''}
          </button>
        ))}
      </div>

      <div className="mt-4" aria-live="polite">
        <ErrorNote>{error}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading applications…</p>}
        {data && data.items.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            {total === 0 && !status && !get('q') && !companyId ? 'No applications yet.' : 'No applications match these filters.'}
          </p>
        )}
        {data && data.items.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <caption className="sr-only">Applications</caption>
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>{['Student', 'Job', 'Applied', 'Status'].map((h) => <th key={h} scope="col" className="px-4 py-2">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((a) => (
                  <tr key={a.id}>
                    <td className="px-4 py-2">
                      <Link to={`/coordinator/students/${a.student.id}`} className="font-medium text-indigo-700 hover:underline">{a.student.full_name}</Link>
                      <p className="text-xs text-slate-500">{a.student.branch?.name ?? 'Branch not set'}{a.student.cgpa != null ? ` · CGPA ${a.student.cgpa}` : ''}</p>
                    </td>
                    <td className="px-4 py-2"><p className="text-slate-900">{a.job.title}</p><p className="text-xs text-slate-500">{a.job.company}</p></td>
                    <td className="px-4 py-2">{formatDay(a.applied_at)}</td>
                    <td className="px-4 py-2"><StatusControl application={a} onChanged={reload} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pagination total={data.total} limit={data.limit} offset={data.offset} onChange={(o) => update({ offset: o || '' }, { keepOffset: true })} />}
      </div>
    </div>
  )
}

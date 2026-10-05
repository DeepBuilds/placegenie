import { useState } from 'react'
import { deleteJob } from '../../api/admin'
import { getCompanies, getJobs } from '../../api/jobs'
import { getBranches, getJobRoles, getSkills } from '../../api/profile'
import JobForm from '../../components/coordinator/JobForm'
import { ErrorNote, PageHeader, Pagination } from '../../components/coordinator/Parts'
import { inputClass, primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { getErrorMessage } from '../../utils/errors'
import { formatDeadline, formatJobType } from '../../utils/jobs'

const LIMIT = 15

export default function Jobs() {
  const { get, update, query } = useUrlFilters()
  const [search, setSearch] = useState(get('q'))
  const [editing, setEditing] = useState(null) // null | 'new' | job
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const offset = Number(get('offset')) || 0

  const { data, error, loading, reload } = useLoad(
    () => getJobs({ q: get('q'), company_id: get('company_id'), status: get('status'), limit: LIMIT, offset }),
    query,
  )
  const { data: lookups } = useLoad(
    () => Promise.all([getCompanies({ limit: 100 }), getSkills(), getBranches(), getJobRoles()]),
    'lookups',
  )
  const [companies, skills, branches, roles] = lookups ? [lookups[0].items, lookups[1], lookups[2], lookups[3]] : [[], [], [], []]

  const remove = async (job) => {
    if (!window.confirm(`Delete "${job.title}" at ${job.company.name}? This cannot be undone.`)) return
    setActionError('')
    setNotice('')
    try {
      await deleteJob(job.id)
      setNotice(`"${job.title}" was deleted.`)
      reload()
    } catch (err) {
      setActionError(getErrorMessage(err))
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Jobs" subtitle="Every job, open or closed.">
        <button type="button" className={primaryButton} disabled={!lookups} onClick={() => setEditing('new')}>Add job</button>
      </PageHeader>

      {editing && lookups && (
        <div className="mt-5">
          <JobForm key={editing === 'new' ? 'new' : editing.id} job={editing === 'new' ? null : editing} companies={companies} skills={skills} branches={branches} roles={roles}
            onCancel={() => setEditing(null)}
            onSaved={() => { setNotice(editing === 'new' ? 'Job added.' : 'Job updated.'); setEditing(null); reload() }} />
        </div>
      )}

      <form className="mt-5 grid gap-3 md:grid-cols-4" role="search" onSubmit={(e) => { e.preventDefault(); update({ q: search.trim() }) }}>
        <input type="search" aria-label="Search jobs" placeholder="Title, company or skill" value={search} maxLength={100} onChange={(e) => setSearch(e.target.value)} className={`${inputClass} mt-0 md:col-span-2`} />
        <select aria-label="Filter by company" value={get('company_id')} onChange={(e) => update({ company_id: e.target.value })} className={`${inputClass} mt-0`}>
          <option value="">All companies</option>
          {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <div className="flex gap-2">
          <select aria-label="Filter by status" value={get('status')} onChange={(e) => update({ status: e.target.value })} className={`${inputClass} mt-0`}>
            <option value="">Open and closed</option><option value="open">Open</option><option value="closed">Closed</option>
          </select>
          <button type="submit" className={primaryButton}>Search</button>
        </div>
      </form>

      <div className="mt-4 space-y-3" aria-live="polite">
        {notice && <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
        <ErrorNote>{actionError}</ErrorNote>
        <ErrorNote>{error}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading jobs…</p>}
        {data && data.items.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">No jobs match these filters.</p>}
        {data && data.items.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <caption className="sr-only">Jobs</caption>
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>{['Job', 'Type', 'Requirements', 'Deadline', 'Status', 'Actions'].map((h) => <th key={h} scope="col" className="px-4 py-2">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((j) => (
                  <tr key={j.id}>
                    <td className="px-4 py-2"><p className="font-medium text-slate-900">{j.title}</p><p className="text-xs text-slate-500">{j.company.name}{j.location ? ` · ${j.location}` : ''}</p></td>
                    <td className="px-4 py-2">{formatJobType(j.job_type)}</td>
                    <td className="px-4 py-2 text-xs text-slate-600">
                      CGPA {j.min_cgpa > 0 ? `≥ ${j.min_cgpa}` : 'any'}
                      {j.skills.length > 0 && <> · {j.skills.map((s) => s.name).join(', ')}</>}
                    </td>
                    <td className="px-4 py-2">{formatDeadline(j.deadline, j.is_expired)}</td>
                    <td className="px-4 py-2">{j.status === 'open' ? 'Open' : 'Closed'}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button type="button" className={secondaryButton} disabled={!lookups} onClick={() => setEditing(j)} aria-label={`Edit ${j.title} at ${j.company.name}`}>Edit</button>
                        <button type="button" className={`${secondaryButton} text-red-700`} onClick={() => remove(j)} aria-label={`Delete ${j.title} at ${j.company.name}`}>Delete</button>
                      </div>
                    </td>
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

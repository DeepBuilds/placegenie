import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getStudents } from '../../api/admin'
import { getBranches } from '../../api/profile'
import { ErrorNote, PageHeader, Pagination, StageBadge } from '../../components/coordinator/Parts'
import { inputClass, primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { STAGE_OPTIONS } from '../../utils/coordinator'

const LIMIT = 20
const SORTS = [
  ['name', 'Name'], ['cgpa', 'CGPA (high to low)'], ['profile', 'Profile completeness'], ['applications', 'Most applications'], ['newest', 'Newest'],
]
const chip = (on) => `rounded-full border px-3 py-1 text-sm ${on ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 text-slate-700 hover:bg-slate-100'}`

export default function Students() {
  const { get, update, reset, query } = useUrlFilters()
  const [search, setSearch] = useState(get('q'))
  const offset = Number(get('offset')) || 0
  const params = {
    q: get('q'), branch_id: get('branch_id'), year: get('year'), min_cgpa: get('min_cgpa'), stage: get('stage'),
    has_resume: get('has_resume'), profile_ready: get('profile_ready'), sort: get('sort'), limit: LIMIT, offset,
  }
  const { data, error, loading } = useLoad(() => getStudents(params), query)
  const { data: branches } = useLoad(getBranches, 'branches')

  const stage = get('stage')
  const total = data ? Object.values(data.stage_counts).reduce((a, b) => a + b, 0) : 0

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <PageHeader title="Students" subtitle="Search the cohort and open anyone's placement profile." />

      <form className="mt-5 flex gap-2" role="search" onSubmit={(e) => { e.preventDefault(); update({ q: search.trim() }) }}>
        <input type="search" aria-label="Search students" placeholder="Search by name, email or college" value={search} maxLength={100}
          onChange={(e) => setSearch(e.target.value)} className={`${inputClass} mt-0`} />
        <button type="submit" className={primaryButton}>Search</button>
      </form>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-6">
        <label className="text-sm text-slate-700">Branch
          <select value={get('branch_id')} onChange={(e) => update({ branch_id: e.target.value })} className={inputClass}>
            <option value="">All branches</option>
            {(branches ?? []).map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-700">Year
          <select value={get('year')} onChange={(e) => update({ year: e.target.value })} className={inputClass}>
            <option value="">Any year</option>
            {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-700">Minimum CGPA
          <input type="number" min="0" max="10" step="0.1" value={get('min_cgpa')} onChange={(e) => update({ min_cgpa: e.target.value })} className={inputClass} />
        </label>
        <label className="text-sm text-slate-700">Resume
          <select value={get('has_resume')} onChange={(e) => update({ has_resume: e.target.value })} className={inputClass}>
            <option value="">Any</option><option value="true">Uploaded</option><option value="false">Not uploaded</option>
          </select>
        </label>
        <label className="text-sm text-slate-700">Profile
          <select value={get('profile_ready')} onChange={(e) => update({ profile_ready: e.target.value })} className={inputClass}>
            <option value="">Any</option><option value="true">80% or more complete</option><option value="false">Under 80%</option>
          </select>
        </label>
        <label className="text-sm text-slate-700">Sort by
          <select value={get('sort') || 'name'} onChange={(e) => update({ sort: e.target.value === 'name' ? '' : e.target.value })} className={inputClass}>
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by placement stage">
        <button type="button" aria-pressed={!stage} onClick={() => update({ stage: '' })} className={chip(!stage)}>
          All{data ? ` (${total})` : ''}
        </button>
        {STAGE_OPTIONS.map(([key, label]) => (
          <button key={key} type="button" aria-pressed={stage === key} onClick={() => update({ stage: key })} className={chip(stage === key)}>
            {label}{data ? ` (${data.stage_counts[key] ?? 0})` : ''}
          </button>
        ))}
        <button type="button" className={`${secondaryButton} ml-auto`} onClick={() => { setSearch(''); reset() }}>Clear filters</button>
      </div>

      <div className="mt-4" aria-live="polite">
        <ErrorNote>{error}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading students…</p>}
        {data && data.items.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            {total === 0 ? 'No students have registered yet.' : 'No students match these filters.'}
          </div>
        )}
        {data && data.items.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <caption className="sr-only">Students</caption>
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  {['Student', 'Branch', 'CGPA', 'Profile', 'Resume', 'Applications', 'Stage'].map((h) => (
                    <th key={h} scope="col" className="px-4 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-2">
                      <Link to={`/coordinator/students/${s.id}`} className="font-medium text-indigo-700 hover:underline">{s.full_name}</Link>
                      <p className="text-xs text-slate-500">{s.email}</p>
                    </td>
                    <td className="px-4 py-2">{s.branch?.name ?? '—'}{s.year ? <span className="text-slate-500"> · Year {s.year}</span> : null}</td>
                    <td className="px-4 py-2">{s.cgpa ?? '—'}{s.backlogs > 0 && <span className="ml-1 text-xs text-amber-700">({s.backlogs} backlog{s.backlogs > 1 ? 's' : ''})</span>}</td>
                    <td className="px-4 py-2">{s.profile_percent}%</td>
                    <td className="px-4 py-2">{s.has_resume ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-2">{s.applications}</td>
                    <td className="px-4 py-2"><StageBadge stage={s.stage} /></td>
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

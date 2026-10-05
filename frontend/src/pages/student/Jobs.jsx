import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getCompanies, getJobs } from '../../api/jobs'
import { getBranches, getJobRoles, getSkills } from '../../api/profile'
import JobCard from '../../components/jobs/JobCard'
import { inputClass, secondaryButton } from '../../components/profile/Section'
import { getErrorMessage } from '../../utils/errors'

const PAGE_SIZE = 12
const FILTER_KEYS = ['company_id', 'job_type', 'role_id', 'skill_id', 'branch_id', 'location', 'max_min_cgpa']

function Select({ id, label, value, onChange, options, placeholder }) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-slate-600">
        {label}
      </label>
      <select id={id} className={inputClass} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

export default function Jobs() {
  const [params, setParams] = useSearchParams()
  const [lookups, setLookups] = useState({ companies: [], branches: [], skills: [], roles: [] })
  const [result, setResult] = useState({ key: null, data: null, error: '' })

  const latestParams = useRef(params)
  useEffect(() => {
    latestParams.current = params
  }, [params])

  const get = (k) => params.get(k) ?? ''
  const offset = Number(params.get('offset')) || 0
  const query = params.toString()

  // The search box is typed into freely and written to the URL after a short pause.
  const [text, setText] = useState(get('q'))
  const debounce = useRef(null)

  const update = (changes, { keepOffset = false } = {}) => {
    // Build on the latest parameters (kept in a ref), not on the ones from the last render:
    // react-router does not queue updates, so two changes in one tick would otherwise collide.
    const next = new URLSearchParams(latestParams.current)
    for (const [k, v] of Object.entries(changes)) {
      if (v === '' || v === null || v === false) next.delete(k)
      else next.set(k, String(v))
    }
    if (!keepOffset) next.delete('offset')
    latestParams.current = next
    setParams(next, { replace: true })
  }

  const onSearchChange = (value) => {
    setText(value)
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => update({ q: value.trim() }), 350)
  }

  useEffect(() => () => clearTimeout(debounce.current), [])

  useEffect(() => {
    Promise.all([getCompanies({ limit: 100 }), getBranches(), getSkills(), getJobRoles()])
      .then(([companies, branches, skills, roles]) =>
        setLookups({ companies: companies.items, branches, skills, roles }),
      )
      .catch(() => {
        /* filters simply stay empty; the job list reports its own errors */
      })
  }, [])

  // Fetch whenever the URL parameters change. Stale responses are ignored.
  useEffect(() => {
    let cancelled = false
    const apiParams = Object.fromEntries(new URLSearchParams(query))
    getJobs({ ...apiParams, limit: PAGE_SIZE, offset: apiParams.offset ?? 0 })
      .then((data) => !cancelled && setResult({ key: query, data, error: '' }))
      .catch((err) => !cancelled && setResult({ key: query, data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [query])

  const loading = result.key !== query
  const { data, error } = result
  const activeCompany = lookups.companies.find((c) => String(c.id) === get('company_id'))
  const hasFilters = useMemo(
    () => FILTER_KEYS.some((k) => params.get(k)) || params.get('q') || params.get('hide_expired'),
    [params],
  )

  const reset = () => {
    setText('')
    latestParams.current = new URLSearchParams()
    setParams({}, { replace: true })
  }

  const toOptions = (items) => items.map((i) => ({ value: i.id, label: i.name }))

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Jobs</h1>
      <p className="text-sm text-slate-600">
        Browse open opportunities. Requirements are shown exactly as set by each company.
      </p>

      <div className="mt-5 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label htmlFor="job-search" className="block text-xs font-medium text-slate-600">
          Search
        </label>
        <input
          id="job-search"
          type="search"
          className={inputClass}
          placeholder="Job title, company, skill or keyword…"
          value={text}
          onChange={(e) => onSearchChange(e.target.value)}
        />

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Select id="f-company" label="Company" placeholder="All companies" value={get('company_id')}
            onChange={(v) => update({ company_id: v })} options={toOptions(lookups.companies)} />
          <Select id="f-role" label="Job role" placeholder="All roles" value={get('role_id')}
            onChange={(v) => update({ role_id: v })} options={toOptions(lookups.roles)} />
          <Select id="f-skill" label="Skill" placeholder="Any skill" value={get('skill_id')}
            onChange={(v) => update({ skill_id: v })} options={toOptions(lookups.skills)} />
          <Select id="f-branch" label="My branch" placeholder="Any branch" value={get('branch_id')}
            onChange={(v) => update({ branch_id: v })} options={toOptions(lookups.branches)} />
          <Select id="f-type" label="Job type" placeholder="All types" value={get('job_type')}
            onChange={(v) => update({ job_type: v })}
            options={[
              { value: 'full_time', label: 'Full time' },
              { value: 'internship', label: 'Internship' },
              { value: 'contract', label: 'Contract' },
            ]} />
          <div>
            <label htmlFor="f-location" className="block text-xs font-medium text-slate-600">Location</label>
            <input id="f-location" className={inputClass} placeholder="e.g. Pune, Remote" value={get('location')}
              onChange={(e) => update({ location: e.target.value })} />
          </div>
          <div>
            <label htmlFor="f-cgpa" className="block text-xs font-medium text-slate-600">Max CGPA required</label>
            <input id="f-cgpa" type="number" min="0" max="10" step="0.1" className={inputClass} placeholder="e.g. 7.5"
              value={get('max_min_cgpa')} onChange={(e) => update({ max_min_cgpa: e.target.value })} />
          </div>
          <Select id="f-sort" label="Sort by" placeholder="Newest" value={get('sort')}
            onChange={(v) => update({ sort: v })}
            options={[
              { value: 'deadline', label: 'Deadline (soonest)' },
              { value: 'cgpa_low', label: 'Lowest CGPA requirement' },
              { value: 'title', label: 'Title (A–Z)' },
            ]} />
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-indigo-600"
              checked={get('hide_expired') === 'true'}
              onChange={(e) => update({ hide_expired: e.target.checked ? 'true' : '' })} />
            Hide jobs past their deadline
          </label>
          {hasFilters && (
            <button type="button" className={secondaryButton} onClick={reset}>
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {activeCompany && (
        <p className="mt-4 text-sm text-slate-600">
          Showing jobs at <strong>{activeCompany.name}</strong>
          {activeCompany.industry ? ` (${activeCompany.industry})` : ''}.
        </p>
      )}

      <div className="mt-5" aria-live="polite">
        {error && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>
        )}
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading jobs…</p>}

        {data && (
          <>
            <p className="mb-3 text-sm text-slate-600">
              {data.total} job{data.total === 1 ? '' : 's'} found{loading ? ' (updating…)' : ''}
            </p>
            {data.items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
                No jobs match your search. Try removing some filters.
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.items.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            )}

            {data.total > PAGE_SIZE && (
              <nav className="mt-6 flex items-center justify-between" aria-label="Pagination">
                <button className={secondaryButton} disabled={offset === 0}
                  onClick={() => update({ offset: Math.max(0, offset - PAGE_SIZE) || '' }, { keepOffset: true })}>
                  ← Previous
                </button>
                <span className="text-sm text-slate-600">
                  Page {Math.floor(offset / PAGE_SIZE) + 1} of {Math.ceil(data.total / PAGE_SIZE)}
                </span>
                <button className={secondaryButton} disabled={offset + PAGE_SIZE >= data.total}
                  onClick={() => update({ offset: offset + PAGE_SIZE }, { keepOffset: true })}>
                  Next →
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  )
}

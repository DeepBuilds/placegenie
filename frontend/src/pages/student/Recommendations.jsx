import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getRecommendations } from '../../api/recommendations'
import { getJobRoles } from '../../api/profile'
import RecommendationCard from '../../components/jobs/RecommendationCard'
import { inputClass, secondaryButton } from '../../components/profile/Section'
import { useUrlFilters } from '../../hooks/useUrlFilters'
import { getErrorMessage } from '../../utils/errors'

const PAGE_SIZE = 10

export default function Recommendations() {
  const { query, get, update, reset } = useUrlFilters()
  const [roles, setRoles] = useState([])
  const [result, setResult] = useState({ key: null, data: null, error: '' })
  const [location, setLocation] = useState(get('location'))
  const debounce = useRef(null)

  const offset = Number(get('offset')) || 0

  const onLocationChange = (value) => {
    setLocation(value)
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => update({ location: value.trim() }), 350)
  }
  useEffect(() => () => clearTimeout(debounce.current), [])

  useEffect(() => {
    getJobRoles()
      .then(setRoles)
      .catch(() => {
        /* the role filter just stays empty */
      })
  }, [])

  useEffect(() => {
    let cancelled = false
    const params = Object.fromEntries(new URLSearchParams(query))
    getRecommendations({ ...params, limit: PAGE_SIZE })
      .then((data) => !cancelled && setResult({ key: query, data, error: '' }))
      .catch((err) => !cancelled && setResult({ key: query, data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [query])

  const loading = result.key !== query
  const { data, error } = result
  const hasFilters = ['role_id', 'location', 'eligible_only', 'sort'].some((k) => get(k))

  const clear = () => {
    setLocation('')
    reset()
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Recommended for you</h1>
      <p className="text-sm text-slate-600">
        Open jobs ranked by how well they fit your profile. The score is explained on every card and is guidance
        only: the company decides who is hired.
      </p>

      {data?.profile_hints.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-medium">Improve your recommendations</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {data.profile_hints.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
          <Link to="/student/profile" className="mt-2 inline-block font-medium text-amber-900 underline">
            Update my profile →
          </Link>
        </div>
      )}

      <div className="mt-5 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="r-role" className="block text-xs font-medium text-slate-600">Job role</label>
          <select id="r-role" className={inputClass} value={get('role_id')} onChange={(e) => update({ role_id: e.target.value })}>
            <option value="">All roles</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="r-location" className="block text-xs font-medium text-slate-600">Location</label>
          <input id="r-location" className={inputClass} placeholder="e.g. Pune, Remote" value={location}
            onChange={(e) => onLocationChange(e.target.value)} />
        </div>
        <div>
          <label htmlFor="r-sort" className="block text-xs font-medium text-slate-600">Sort by</label>
          <select id="r-sort" className={inputClass} value={get('sort')} onChange={(e) => update({ sort: e.target.value })}>
            <option value="">Best match first</option>
            <option value="score_asc">Lowest match first</option>
            <option value="deadline">Deadline (soonest)</option>
            <option value="title">Title (A–Z)</option>
          </select>
        </div>
        <div className="flex items-end justify-between gap-3">
          <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300 text-indigo-600"
              checked={get('eligible_only') === 'true'}
              onChange={(e) => update({ eligible_only: e.target.checked ? 'true' : '' })} />
            Only jobs I&apos;m eligible for
          </label>
        </div>
        {hasFilters && (
          <div className="sm:col-span-2 lg:col-span-4">
            <button type="button" className={secondaryButton} onClick={clear}>Clear all filters</button>
          </div>
        )}
      </div>

      <div className="mt-5" aria-live="polite">
        {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {loading && !data && <p className="py-10 text-center text-slate-500">Finding your best matches…</p>}

        {data && (
          <>
            <p className="mb-3 text-sm text-slate-600">
              {data.total} job{data.total === 1 ? '' : 's'} shown{loading ? ' (updating…)' : ''} ·{' '}
              <span className="text-emerald-700">{data.counts.eligible} eligible</span> ·{' '}
              <span className="text-red-700">{data.counts.not_eligible} not eligible</span>
              {data.counts.incomplete_profile > 0 && (
                <> · <span className="text-amber-700">{data.counts.incomplete_profile} need a fuller profile</span></>
              )}
            </p>

            {data.items.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
                {hasFilters
                  ? 'No jobs match these filters. Try clearing some.'
                  : 'There are no open jobs to recommend right now.'}
              </div>
            ) : (
              <div className="space-y-4">
                {data.items.map((rec) => (
                  <RecommendationCard key={rec.job.id} rec={rec} />
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

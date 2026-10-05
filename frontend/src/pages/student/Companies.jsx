import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCompanies } from '../../api/jobs'
import { inputClass } from '../../components/profile/Section'
import { getErrorMessage } from '../../utils/errors'

export default function Companies() {
  const [text, setText] = useState('')
  const [q, setQ] = useState('')
  const [result, setResult] = useState({ key: null, data: null, error: '' })
  const debounce = useRef(null)

  const onChange = (value) => {
    setText(value)
    clearTimeout(debounce.current)
    debounce.current = setTimeout(() => setQ(value.trim()), 350)
  }

  useEffect(() => () => clearTimeout(debounce.current), [])

  useEffect(() => {
    let cancelled = false
    getCompanies({ q, limit: 100 })
      .then((data) => !cancelled && setResult({ key: q, data, error: '' }))
      .catch((err) => !cancelled && setResult({ key: q, data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [q])

  const loading = result.key !== q
  const { data, error } = result

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Companies</h1>
      <p className="text-sm text-slate-600">Demo companies visiting the campus (all fictional).</p>

      <div className="mt-5 max-w-md">
        <label htmlFor="company-search" className="block text-xs font-medium text-slate-600">
          Search companies
        </label>
        <input
          id="company-search"
          type="search"
          className={inputClass}
          placeholder="Name or industry…"
          value={text}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>

      <div className="mt-5" aria-live="polite">
        {error && <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading companies…</p>}
        {data &&
          (data.items.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
              No companies match your search.
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((c) => (
                <article key={c.id} className="flex flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
                  <h2 className="text-base font-semibold text-slate-900">{c.name}</h2>
                  <p className="text-sm text-slate-500">
                    {[c.industry, c.location].filter(Boolean).join(' · ')}
                  </p>
                  {c.description && <p className="mt-2 flex-1 text-sm text-slate-700">{c.description}</p>}
                  <div className="mt-4 flex items-center justify-between text-sm">
                    <Link
                      to={`/student/jobs?company_id=${c.id}`}
                      className={c.open_jobs ? 'font-medium text-indigo-600 hover:underline' : 'text-slate-400'}
                    >
                      {c.open_jobs} open job{c.open_jobs === 1 ? '' : 's'}
                      {c.open_jobs ? ' →' : ''}
                    </Link>
                    {c.website && (
                      <a href={c.website} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:underline">
                        Website
                      </a>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ))}
      </div>
    </div>
  )
}

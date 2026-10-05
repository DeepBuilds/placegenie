import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getSkillGap } from '../../api/jobs'
import { getErrorMessage } from '../../utils/errors'

const LEVEL = {
  high: { label: 'High priority', cls: 'bg-red-100 text-red-800' },
  medium: { label: 'Medium priority', cls: 'bg-amber-100 text-amber-800' },
  low: { label: 'Low priority', cls: 'bg-slate-100 text-slate-700' },
}

function Meter({ value, label }) {
  const color = value >= 70 ? 'bg-emerald-500' : value >= 40 ? 'bg-amber-500' : 'bg-red-400'
  return (
    <div className="h-2.5 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label={label}
      aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full transition-all ${color}`} style={{ width: `${value}%` }} />
    </div>
  )
}

function MatchedList({ items }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">Matched ({items.length})</h3>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-slate-500">None of this job&apos;s skills are in your profile yet.</p>
      ) : (
        <ul className="mt-2 space-y-1" aria-label="Matched skills">
          {items.map((s) => (
            <li key={s.skill_id} className="flex flex-wrap items-center gap-2 text-sm text-emerald-800">
              <span aria-hidden="true">✓</span>
              <span className="font-medium">{s.name}</span>
              <span className="text-xs text-slate-500">
                {s.required ? 'required' : 'preferred'}
                {s.student_level ? ` · your level: ${s.student_level}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function MissingList({ items }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">Missing ({items.length})</h3>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-emerald-700">Nothing missing: you have every skill listed for this job.</p>
      ) : (
        <ul className="mt-2 space-y-2" aria-label="Missing skills">
          {items.map((s) => (
            <li key={s.skill_id} className="text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-red-700" aria-hidden="true">✗</span>
                <span className="font-medium text-slate-900">{s.name}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${LEVEL[s.priority].cls}`}>
                  {LEVEL[s.priority].label}
                </span>
                <span className="text-xs text-slate-500">{s.required ? 'required' : 'preferred'}</span>
              </div>
              <details className="ml-6 text-xs text-slate-600">
                <summary className="cursor-pointer">Why this priority?</summary>
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {s.reasons.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              </details>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Priorities({ items }) {
  if (items.length === 0) return null
  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-900">Skills to prioritise</h3>
      <p className="text-xs text-slate-500">Most important first, based on this job&apos;s requirements and how often the skill is asked for.</p>
      <ol className="mt-2 space-y-1.5" aria-label="Skills to prioritise">
        {items.map((p) => (
          <li key={p.skill_id} className="flex flex-wrap items-center gap-2 text-sm">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">{p.rank}</span>
            <span className="font-medium text-slate-900">{p.name}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${LEVEL[p.level].cls}`}>{LEVEL[p.level].label}</span>
            <span className="text-xs text-slate-500">{p.reasons.slice(1, 3).join(' · ') || p.reasons[0]}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

export default function SkillGapPanel({ jobId, showFullPageLink = false }) {
  const [state, setState] = useState({ jobId: null, data: null, error: '' })

  useEffect(() => {
    let cancelled = false
    getSkillGap(jobId)
      .then((data) => !cancelled && setState({ jobId, data, error: '' }))
      .catch((err) => !cancelled && setState({ jobId, data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [jobId])

  if (state.jobId !== jobId) return <p className="py-6 text-center text-slate-500">Comparing your skills…</p>
  if (state.error) return <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{state.error}</p>

  const d = state.data
  return (
    <div className="space-y-5">
      {!d.has_requirements ? (
        <p className="rounded-md bg-slate-50 p-4 text-sm text-slate-600">{d.summary}</p>
      ) : (
        <div>
          <div className="flex items-end justify-between gap-4">
            <p className="text-sm text-slate-700">{d.summary}</p>
            <p className="shrink-0 text-right" aria-label={`Skill match ${d.match_percentage} percent`}>
              <span className="text-3xl font-bold text-indigo-600">{d.match_percentage}%</span>
              <span className="block text-xs text-slate-500">skill match</span>
            </p>
          </div>
          <div className="mt-2"><Meter value={d.match_percentage} label="Skill match" /></div>
          {d.required_match_percentage !== null && (
            <div className="mt-3">
              <p className="text-xs text-slate-600">
                Required skills: {d.required_matched} of {d.required_total} ({d.required_match_percentage}%)
              </p>
              <div className="mt-1"><Meter value={d.required_match_percentage} label="Required skills matched" /></div>
            </div>
          )}
        </div>
      )}

      {d.notes.map((n) => (
        <p key={n} className="rounded-md bg-amber-50 p-3 text-sm text-amber-900">
          {n}{' '}
          {!d.student_has_skills && (
            <Link to="/student/profile" className="font-medium underline">Add skills to my profile →</Link>
          )}
        </p>
      ))}

      {d.has_requirements && (
        <>
          <div className="grid gap-6 md:grid-cols-2">
            <MatchedList items={d.matched_skills} />
            <MissingList items={d.missing_skills} />
          </div>
          <Priorities items={d.priority} />
        </>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-slate-500">{d.disclaimer}</p>
        {showFullPageLink && (
          <Link to={`/student/skill-gap?job_id=${d.job.id}`} className="text-sm font-medium text-indigo-600 hover:underline">
            Open full skill-gap page →
          </Link>
        )}
      </div>
    </div>
  )
}

import { Link } from 'react-router-dom'
import { formatDeadline, formatJobType } from '../../utils/jobs'

const ELIGIBILITY_BADGE = {
  ELIGIBLE: { text: '✓ Eligible', cls: 'bg-emerald-100 text-emerald-800' },
  NOT_ELIGIBLE: { text: '✗ Not eligible', cls: 'bg-red-100 text-red-800' },
  INCOMPLETE_PROFILE: { text: '? Profile incomplete', cls: 'bg-amber-100 text-amber-800' },
}

function scoreColor(score) {
  if (score >= 70) return 'text-emerald-600'
  if (score >= 40) return 'text-amber-600'
  return 'text-slate-500'
}

function Chips({ title, items, cls, label }) {
  if (items.length === 0) return null
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h4>
      <ul className="mt-1 flex flex-wrap gap-1.5" aria-label={label ?? title}>
        {items.map((s) => (
          <li key={s} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
            {s}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Breakdown({ breakdown, multiplier, score }) {
  return (
    <details className="mt-3 rounded-md bg-slate-50 p-3 text-xs">
      <summary className="cursor-pointer font-medium text-slate-700">How this score was calculated</summary>
      <table className="mt-2 w-full text-left">
        <thead className="text-slate-500">
          <tr>
            <th className="pb-1 font-medium">Factor</th>
            <th className="pb-1 font-medium">Fit</th>
            <th className="pb-1 font-medium">Weight</th>
            <th className="pb-1 text-right font-medium">Points</th>
          </tr>
        </thead>
        <tbody>
          {breakdown.map((c) => (
            <tr key={c.key} className="border-t border-slate-200 align-top">
              <td className="py-1 pr-2 text-slate-800">
                {c.label}
                <span className="block text-slate-500">{c.note}</span>
              </td>
              <td className="py-1 pr-2">{c.available ? `${Math.round(c.score * 100)}%` : '–'}</td>
              <td className="py-1 pr-2">{c.available ? `${Math.round(c.weight * 100)}%` : 'not used'}</td>
              <td className="py-1 text-right">{c.available ? c.points.toFixed(1) : '–'}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-slate-300 font-medium text-slate-800">
            <td colSpan={3} className="pt-1">
              Eligibility adjustment (×{multiplier})
            </td>
            <td className="pt-1 text-right">{score}</td>
          </tr>
        </tfoot>
      </table>
      <p className="mt-2 text-slate-500">
        Only factors you have data for are used; their weights are rescaled to add up to 100%.
      </p>
    </details>
  )
}

export default function RecommendationCard({ rec }) {
  const { job } = rec
  const badge = ELIGIBILITY_BADGE[rec.eligibility.result]

  return (
    <article className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-slate-900">
            <Link to={`/student/jobs/${job.id}`} className="hover:text-indigo-600">
              {job.title}
            </Link>
          </h3>
          <p className="text-sm text-slate-600">
            {job.company.name}
            {job.location ? ` · ${job.location}` : ''} · {formatJobType(job.job_type)}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className={`rounded-full px-2.5 py-0.5 font-semibold ${badge.cls}`}>{badge.text}</span>
            <span className={job.is_expired ? 'font-medium text-red-600' : 'text-slate-500'}>
              {formatDeadline(job.deadline, job.is_expired)}
            </span>
          </div>
        </div>
        <div className="shrink-0 text-center" aria-label={`Match ${rec.match_score} percent`}>
          <p className={`text-3xl font-bold ${scoreColor(rec.match_score)}`}>{rec.match_score}%</p>
          <p className="text-xs text-slate-500">match</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <Chips title="Matched skills" items={rec.matched_skills} cls="bg-emerald-100 text-emerald-800" />
          <Chips title="Missing required skills" items={rec.missing_skills} cls="bg-red-100 text-red-800" />
          <Chips
            title="Nice-to-have skills you lack"
            items={rec.missing_preferred_skills}
            cls="border border-slate-300 text-slate-600"
          />
          {rec.matched_skills.length === 0 && rec.missing_skills.length === 0 && (
            <p className="text-xs text-slate-500">No skill information to compare for this job.</p>
          )}
        </div>
        <div className="space-y-3 text-sm">
          {rec.reasons.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Why recommended</h4>
              <ul className="mt-1 space-y-1">
                {rec.reasons.map((r) => (
                  <li key={r} className="flex gap-1.5 text-slate-700">
                    <span className="text-emerald-600" aria-hidden="true">✓</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {rec.concerns.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">What holds it back</h4>
              <ul className="mt-1 space-y-1">
                {rec.concerns.map((c) => (
                  <li key={c} className="flex gap-1.5 text-slate-700">
                    <span className="text-red-500" aria-hidden="true">✗</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <Breakdown breakdown={rec.breakdown} multiplier={rec.eligibility.multiplier} score={rec.match_score} />

      <div className="mt-4 text-right">
        <Link to={`/student/jobs/${job.id}`} className="text-sm font-medium text-indigo-600 hover:underline">
          View details &amp; check eligibility →
        </Link>
      </div>
    </article>
  )
}

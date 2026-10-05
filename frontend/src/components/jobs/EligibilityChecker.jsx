import { useState } from 'react'
import { Link } from 'react-router-dom'
import { checkEligibility } from '../../api/jobs'
import { getErrorMessage } from '../../utils/errors'

const RESULT_STYLE = {
  ELIGIBLE: {
    box: 'border-emerald-300 bg-emerald-50',
    text: 'text-emerald-800',
    title: '✓ ELIGIBLE',
  },
  NOT_ELIGIBLE: {
    box: 'border-red-300 bg-red-50',
    text: 'text-red-800',
    title: '✗ NOT ELIGIBLE',
  },
  INCOMPLETE_PROFILE: {
    box: 'border-amber-300 bg-amber-50',
    text: 'text-amber-800',
    title: '! CANNOT FULLY CHECK',
  },
}

const STATUS_BADGE = {
  passed: { icon: '✓', label: 'Passed', cls: 'bg-emerald-100 text-emerald-800' },
  failed: { icon: '✗', label: 'Failed', cls: 'bg-red-100 text-red-800' },
  not_evaluated: { icon: '?', label: 'Not checked', cls: 'bg-amber-100 text-amber-800' },
}

function CriterionRow({ c }) {
  const badge = STATUS_BADGE[c.status]
  return (
    <li className="py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="font-medium text-slate-900">{c.label}</span>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.cls}`}>
          <span aria-hidden="true">{badge.icon} </span>
          {badge.label}
        </span>
      </div>
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 text-xs text-slate-600">
        <dt className="text-slate-500">Required</dt>
        <dd>{c.required}</dd>
        <dt className="text-slate-500">You</dt>
        <dd>{c.actual}</dd>
      </dl>
      <p className={`mt-1 text-sm ${c.status === 'passed' ? 'text-slate-600' : 'font-medium text-slate-900'}`}>
        {c.message}
      </p>
    </li>
  )
}

function Result({ data }) {
  const style = RESULT_STYLE[data.result]
  return (
    <div className="mt-4 space-y-4">
      <div className={`rounded-md border p-4 ${style.box}`}>
        <p className={`text-lg font-bold ${style.text}`}>{style.title}</p>
        <p className={`text-sm ${style.text}`}>{data.summary}</p>
      </div>

      {data.reasons.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {data.result === 'INCOMPLETE_PROFILE' ? 'What is missing' : 'Why you are not eligible'}
          </h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {data.reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      <ul className="divide-y divide-slate-100 rounded-md border border-slate-200 px-4" aria-label="Eligibility criteria">
        {data.criteria.map((c) => (
          <CriterionRow key={c.key} c={c} />
        ))}
      </ul>

      {data.missing_skills.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Required skills you are missing</h3>
          <ul className="mt-1.5 flex flex-wrap gap-1.5" aria-label="Missing required skills">
            {data.missing_skills.map((s) => (
              <li key={s} className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.missing_preferred_skills.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Nice-to-have skills you could add (not required)</h3>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {data.missing_preferred_skills.map((s) => (
              <li key={s} className="rounded-full border border-slate-300 px-2.5 py-0.5 text-xs text-slate-600">
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.incomplete_fields.length > 0 && (
        <p className="text-sm text-slate-700">
          Complete your profile ({data.incomplete_fields.join(', ')}) for a full check.{' '}
          <Link to="/student/profile" className="font-medium text-indigo-600 hover:underline">
            Update profile →
          </Link>
        </p>
      )}
      {data.result !== 'ELIGIBLE' && data.incomplete_fields.length === 0 && (
        <p className="text-sm text-slate-700">
          Changed something? <Link to="/student/profile" className="font-medium text-indigo-600 hover:underline">Update your profile</Link> and check again.
        </p>
      )}

      <p className="text-xs text-slate-500">
        This is automated guidance based on your profile and the listed requirements. The company and your
        placement officers make the final decision.
      </p>
    </div>
  )
}

export default function EligibilityChecker({ jobId }) {
  const [state, setState] = useState({ status: 'idle', data: null, error: '' })

  const run = async () => {
    setState((s) => ({ ...s, status: 'loading', error: '' }))
    try {
      const data = await checkEligibility(jobId)
      setState({ status: 'done', data, error: '' })
    } catch (err) {
      setState({ status: 'error', data: null, error: getErrorMessage(err) })
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="elig-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="elig-title" className="text-lg font-semibold text-slate-900">Am I eligible?</h2>
          <p className="text-sm text-slate-500">Compare your profile with this job&apos;s requirements.</p>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={state.status === 'loading'}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {state.status === 'loading' ? 'Checking…' : state.data ? 'Check again' : 'Check Eligibility'}
        </button>
      </div>

      <div aria-live="polite">
        {state.status === 'error' && (
          <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{state.error}</p>
        )}
        {state.data && <Result data={state.data} />}
      </div>
    </section>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboard } from '../../api/dashboard'
import {
  ApplicationsCard,
  InterviewsCard,
  KpiCards,
  Opportunities,
  ProgressCard,
  RecommendedJobs,
  ResumeCard,
  SkillGapsCard,
  StatisticsCard,
} from '../../components/dashboard/Sections'
import { getErrorMessage } from '../../utils/errors'

const ASK_INTERVIEW = '/student/chat?ask=' + encodeURIComponent('How should I prepare for a technical interview?')

const QUICK_ACTIONS = [
  { key: 'profile', label: 'Complete Profile', to: '/student/profile', icon: '👤' },
  { key: 'resume', label: 'Upload Resume', to: '/student/resume', icon: '📄' },
  { key: 'jobs', label: 'Find Jobs', to: '/student/jobs', icon: '🔎' },
  { key: 'applied', label: 'View Recommendations', to: '/student/recommendations', icon: '⭐' },
  { key: 'gaps', label: 'Check Skill Gaps', to: '/student/skill-gap', icon: '🧩' },
  { key: 'interviewed', label: 'Prepare for Interview', to: ASK_INTERVIEW, icon: '🎤' },
  { key: 'chat', label: 'Open Chatbot', to: '/student/chat', icon: '💬' },
]

function greeting(hour = new Date().getHours()) {
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

export default function Dashboard() {
  const [state, setState] = useState({ status: 'loading', data: null, error: '' })

  const load = useCallback(() => {
    let cancelled = false
    getDashboard()
      .then((data) => !cancelled && setState({ status: 'ready', data, error: '' }))
      .catch((err) => !cancelled && setState({ status: 'error', data: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  const retry = () => {
    setState((s) => ({ ...s, status: s.data ? 'ready' : 'loading', error: '' }))
    load()
  }

  const { status, data, error } = state
  const loading = status === 'loading'
  const sectionProps = (key) => ({ d: data, loading, error: data?.errors?.[key], onRetry: retry })
  const highlighted = data?.progress?.next_step?.key

  if (status === 'error') {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-xl font-bold text-slate-900">Your dashboard could not be loaded</h1>
        <p role="alert" className="mt-2 text-red-600">{error}</p>
        <button type="button" onClick={retry} className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">Try again</button>
      </div>
    )
  }

  const s = data?.student
  return (
    <div className="mx-auto max-w-7xl space-y-5 px-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">
            {loading ? 'Welcome back' : `${greeting()}, ${s.first_name}`}
          </h1>
          <p className="text-sm text-slate-600">
            {loading ? 'Loading your placement overview…' : [s.branch, s.year ? `Year ${s.year}` : null, s.cgpa !== null ? `CGPA ${s.cgpa}` : null].filter(Boolean).join(' · ') || 'Complete your profile to personalise this page.'}
          </p>
        </div>
        <button type="button" onClick={retry} disabled={loading} className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50">
          Refresh
        </button>
      </header>

      {data?.progress?.next_step && (
        <Link to={data.progress.next_step.link} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-200 bg-indigo-50 p-4 hover:bg-indigo-100" aria-label="Recommended next step">
          <span>
            <span className="block text-xs font-semibold uppercase tracking-wide text-indigo-700">Next step</span>
            <span className="block font-semibold text-indigo-950">{data.progress.next_step.label}</span>
            <span className="block text-sm text-indigo-900">{data.progress.next_step.reason}</span>
          </span>
          <span className="text-sm font-medium text-indigo-700">Go →</span>
        </Link>
      )}

      <KpiCards d={data} loading={loading} />

      <section aria-label="Quick actions">
        <h2 className="sr-only">Quick actions</h2>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
          {QUICK_ACTIONS.map((a) => (
            <li key={a.key}>
              <Link to={a.to} className={`flex h-full flex-col items-center justify-center gap-1 rounded-lg border p-3 text-center text-sm font-medium hover:bg-slate-50 ${a.key === highlighted ? 'border-indigo-400 bg-indigo-50 text-indigo-900' : 'border-slate-200 bg-white text-slate-800'}`}>
                <span aria-hidden="true" className="text-xl">{a.icon}</span>
                {a.label}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <ProgressCard {...sectionProps('progress')} />

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <RecommendedJobs {...sectionProps('recommendations')} />
          <Opportunities {...sectionProps('opportunities')} />
          <SkillGapsCard {...sectionProps('skill_gaps')} />
        </div>
        <div className="space-y-5">
          <ApplicationsCard {...sectionProps('applications')} />
          <InterviewsCard {...sectionProps('interviews')} />
          <ResumeCard {...sectionProps('resume')} />
        </div>
      </div>

      <StatisticsCard {...sectionProps('statistics')} />

      <p className="text-xs text-slate-500">
        PlaceGenie gives guidance only. Statuses are what the placement cell has recorded, and there is no live information from companies.
      </p>
    </div>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'
import { getBranches, getJobRoles, getProfile, getSkills } from '../../api/profile'
import AcademicSection from '../../components/profile/AcademicSection'
import ItemListSection from '../../components/profile/ItemListSection'
import PreferencesSection from '../../components/profile/PreferencesSection'
import SkillsSection from '../../components/profile/SkillsSection'
import { getErrorMessage } from '../../utils/errors'

const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(undefined, { month: 'short', year: 'numeric' }) : '')

const CERT_FIELDS = [
  { name: 'name', label: 'Certification name', required: true },
  { name: 'issuer', label: 'Issuer' },
  { name: 'issued_on', label: 'Issued on', type: 'date' },
]
const PROJECT_FIELDS = [
  { name: 'title', label: 'Project title', required: true },
  { name: 'tech_stack', label: 'Tech stack', placeholder: 'React, FastAPI, MySQL' },
  { name: 'url', label: 'Link (GitHub/demo)', placeholder: 'https://…', wide: true },
  { name: 'description', label: 'Description', textarea: true, wide: true },
]
const EXPERIENCE_FIELDS = [
  { name: 'organization', label: 'Organization', required: true },
  { name: 'role', label: 'Role', required: true },
  { name: 'start_date', label: 'Start date', type: 'date' },
  { name: 'end_date', label: 'End date (blank if ongoing)', type: 'date' },
  { name: 'description', label: 'What you did', textarea: true, wide: true },
]

function Completeness({ completeness }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Profile completeness</h2>
        <span className="text-lg font-bold text-indigo-600">{completeness.score}%</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={completeness.score} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full bg-indigo-600 transition-all" style={{ width: `${completeness.score}%` }} />
      </div>
      {completeness.missing.length > 0 ? (
        <p className="mt-3 text-sm text-slate-600">
          Still missing: {completeness.missing.join(', ')}. A complete profile gives accurate eligibility and recommendations.
        </p>
      ) : (
        <p className="mt-3 text-sm text-emerald-700">Your profile is complete.</p>
      )}
    </div>
  )
}

export default function Profile() {
  const [state, setState] = useState({ status: 'loading', error: '' })
  const [profile, setProfile] = useState(null)
  const [lookups, setLookups] = useState({ branches: [], skills: [], roles: [] })
  const [message, setMessage] = useState(null)
  const timer = useRef(null)

  const notify = useCallback((type, text) => {
    setMessage({ type, text })
    clearTimeout(timer.current)
    if (type === 'success') timer.current = setTimeout(() => setMessage(null), 4000)
  }, [])

  const fetchAll = useCallback(() => {
    Promise.all([getProfile(), getBranches(), getSkills(), getJobRoles()])
      .then(([p, branches, skills, roles]) => {
        setProfile(p)
        setLookups({ branches, skills, roles })
        setState({ status: 'ready', error: '' })
      })
      .catch((err) => setState({ status: 'error', error: getErrorMessage(err) }))
  }, [])

  const retry = () => {
    setState({ status: 'loading', error: '' })
    fetchAll()
  }

  useEffect(() => {
    fetchAll()
    return () => clearTimeout(timer.current)
  }, [fetchAll])

  if (state.status === 'loading') return <p className="p-8 text-center text-slate-500">Loading your profile…</p>
  if (state.status === 'error')
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p role="alert" className="text-red-600">{state.error}</p>
        <button onClick={retry} className="mt-4 rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-100">
          Try again
        </button>
      </div>
    )

  const common = { profile, onSaved: setProfile, notify }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">My profile</h1>
        <p className="text-sm text-slate-600">Keep this up to date: eligibility and job matching use it.</p>
      </div>

      {message && (
        <div
          role={message.type === 'error' ? 'alert' : 'status'}
          className={`sticky top-2 z-10 rounded-md p-3 text-sm shadow ${
            message.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'
          }`}
        >
          {message.text}
        </div>
      )}

      <Completeness completeness={profile.completeness} />

      <AcademicSection {...common} branches={lookups.branches} />
      <SkillsSection {...common} allSkills={lookups.skills} />

      <ItemListSection
        {...common}
        kind="certifications"
        title="Certifications"
        emptyText="No certifications added yet."
        addLabel="Add certification"
        fields={CERT_FIELDS}
        items={profile.certifications}
        renderItem={(c) => (
          <>
            <p className="font-medium text-slate-900">{c.name}</p>
            <p className="text-slate-500">{[c.issuer, fmtDate(c.issued_on)].filter(Boolean).join(' · ')}</p>
          </>
        )}
      />

      <ItemListSection
        {...common}
        kind="projects"
        title="Projects"
        emptyText="No projects added yet."
        addLabel="Add project"
        fields={PROJECT_FIELDS}
        items={profile.projects}
        renderItem={(p) => (
          <>
            <p className="font-medium text-slate-900">{p.title}</p>
            {p.tech_stack && <p className="text-slate-500">{p.tech_stack}</p>}
            {p.description && <p className="mt-1 text-slate-700">{p.description}</p>}
            {p.url && (
              <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">
                {p.url}
              </a>
            )}
          </>
        )}
      />

      <ItemListSection
        {...common}
        kind="experiences"
        title="Experience"
        subtitle="Internships, jobs or other work (optional)."
        emptyText="No experience added yet."
        addLabel="Add experience"
        fields={EXPERIENCE_FIELDS}
        items={profile.experiences}
        renderItem={(x) => (
          <>
            <p className="font-medium text-slate-900">
              {x.role} · {x.organization}
            </p>
            <p className="text-slate-500">
              {fmtDate(x.start_date)}
              {x.start_date ? ' – ' : ''}
              {x.start_date ? fmtDate(x.end_date) || 'Present' : ''}
            </p>
            {x.description && <p className="mt-1 text-slate-700">{x.description}</p>}
          </>
        )}
      />

      <PreferencesSection {...common} jobRoles={lookups.roles} />
    </div>
  )
}

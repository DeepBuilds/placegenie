import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchResumeFile, getAnalysis, getMyResume, reanalyze, syncSkills } from '../../api/resume'
import Section, { primaryButton, secondaryButton } from '../../components/profile/Section'
import { getErrorMessage } from '../../utils/errors'
import { formatDateTime, formatSize } from '../../utils/resume'

const SEVERITY = {
  high: { label: 'Important', cls: 'bg-red-100 text-red-800' },
  medium: { label: 'Worth fixing', cls: 'bg-amber-100 text-amber-800' },
  low: { label: 'Nice to have', cls: 'bg-slate-100 text-slate-700' },
}

function Bar({ value, label }) {
  const color = value >= 70 ? 'bg-emerald-500' : value >= 40 ? 'bg-amber-500' : 'bg-red-400'
  return (
    <div className="h-2 overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full ${color}`} style={{ width: `${value}%` }} />
    </div>
  )
}

function Chip({ children, cls, title }) {
  return (
    <li title={title} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </li>
  )
}

function Overview({ a, onReanalyze, onView, busy }) {
  const checks = [
    ['Email', a.contact.email],
    ['Phone', a.contact.phone],
    ['LinkedIn', a.contact.linkedin],
    ['GitHub', a.contact.github],
  ]
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Resume analysis</h1>
          <p className="text-sm text-slate-600">
            {a.resume.original_name} · {formatSize(a.resume.size_bytes)} · {a.page_count} page{a.page_count === 1 ? '' : 's'} · {a.word_count} words
          </p>
          <p className="text-xs text-slate-500">Uploaded {formatDateTime(a.resume.uploaded_at)}</p>
          {a.detected_name && <p className="mt-2 text-sm text-slate-700">Name found: <strong>{a.detected_name}</strong></p>}
        </div>
        <div className="text-center" aria-label={`Completeness ${a.completeness_score} out of 100`}>
          <p className="text-4xl font-bold text-indigo-600">{a.completeness_score}</p>
          <p className="text-xs text-slate-500">completeness / 100</p>
        </div>
      </div>
      <div className="mt-3"><Bar value={a.completeness_score} label="Resume completeness" /></div>

      <ul className="mt-4 flex flex-wrap gap-2 text-xs" aria-label="Contact details found">
        {checks.map(([name, ok]) => (
          <li key={name} className={`rounded-full px-2.5 py-0.5 font-medium ${ok ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'}`}>
            {ok ? '✓' : '✗'} {name}
          </li>
        ))}
      </ul>

      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onReanalyze} disabled={busy} className={secondaryButton}>Re-analyse</button>
        <button type="button" onClick={onView} className={secondaryButton}>View PDF</button>
        <Link to="/student/resume" className={secondaryButton}>Replace resume</Link>
      </div>

      <details className="mt-4 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">How the completeness score is calculated</summary>
        <table className="mt-2 w-full text-left text-xs">
          <tbody>
            {a.score_breakdown.map((p) => (
              <tr key={p.label} className="border-t border-slate-200 align-top">
                <td className="py-1 pr-2 text-slate-800">{p.label}<span className="block text-slate-500">{p.note}</span></td>
                <td className="py-1 text-right text-slate-700">{p.earned} / {p.max}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  )
}

function Suggestions({ items }) {
  return (
    <Section title="Suggestions to improve your resume" subtitle="Most important first.">
      {items.length === 0 ? (
        <p className="text-sm text-emerald-700">No suggestions: your resume covers the basics.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => (
            <li key={s.text} className="flex items-start gap-3 text-sm">
              <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${SEVERITY[s.severity].cls}`}>
                {SEVERITY[s.severity].label}
              </span>
              <span className="text-slate-700"><span className="font-medium text-slate-900">{s.category}: </span>{s.text}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

function Skills({ a, onSync, busy }) {
  const toAdd = a.profile_comparison.skills_not_in_profile.length
  return (
    <Section title="Skills detected" subtitle="Found by matching your resume text against the platform's skill list.">
      {a.skills.length === 0 ? (
        <p className="text-sm text-slate-500">No known skills were recognised. Add a Skills section listing your tools and technologies.</p>
      ) : (
        <ul className="flex flex-wrap gap-1.5" aria-label="Detected skills">
          {a.skills.map((s) => (
            <Chip key={s.skill_id} title={`Found in: ${s.evidence.join(', ') || 'text'}`}
              cls={s.in_profile ? 'bg-emerald-100 text-emerald-800' : 'bg-indigo-100 text-indigo-800'}>
              {s.in_profile ? '✓ ' : ''}{s.name}
            </Chip>
          ))}
        </ul>
      )}
      {a.skills.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">Green ✓ = already in your profile. Hover a skill to see where it was found.</p>
      )}
      {toAdd > 0 && (
        <button type="button" onClick={onSync} disabled={busy} className={`${primaryButton} mt-3`}>
          Add {toAdd} detected skill{toAdd === 1 ? '' : 's'} to my profile
        </button>
      )}

      {a.potentially_missing_skills.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-semibold text-slate-900">Potentially missing skills</h3>
          <p className="text-xs text-slate-500">
            Required by the open jobs closest to your resume, but not on your resume or profile. If you have them, add them; if not, they are worth learning.
          </p>
          <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Potentially missing skills">
            {a.potentially_missing_skills.map((m) => (
              <Chip key={m.name} cls="bg-red-100 text-red-800"
                title={`Needed by ${m.jobs_requiring} job(s), e.g. ${m.example_jobs.join(', ')}`}>
                {m.name} · {m.jobs_requiring} job{m.jobs_requiring === 1 ? '' : 's'}
              </Chip>
            ))}
          </ul>
        </div>
      )}
    </Section>
  )
}

function JobRelevance({ items }) {
  return (
    <Section title="Relevance to open jobs" subtitle="Half text similarity, half the share of each job's skills your resume shows.">
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">There are no open jobs to compare with right now.</p>
      ) : (
        <ul className="space-y-4">
          {items.map((j) => (
            <li key={j.job_id}>
              <div className="flex items-baseline justify-between gap-3">
                <Link to={`/student/jobs/${j.job_id}`} className="font-medium text-slate-900 hover:text-indigo-600">
                  {j.title} <span className="font-normal text-slate-500">· {j.company}</span>
                </Link>
                <span className="text-sm font-semibold text-slate-700">{j.relevance}%</span>
              </div>
              <div className="mt-1"><Bar value={j.relevance} label={`Relevance to ${j.title}`} /></div>
              <p className="mt-1 text-xs text-slate-600">
                {j.matched_skills.length > 0 && <>Matched: <span className="text-emerald-700">{j.matched_skills.join(', ')}</span>. </>}
                {j.missing_skills.length > 0 && <>Missing: <span className="text-red-700">{j.missing_skills.join(', ')}</span>.</>}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Section>
  )
}

function Sections({ a }) {
  return (
    <Section title="Resume sections">
      <ul className="flex flex-wrap gap-1.5" aria-label="Sections found">
        {a.sections_found.map((s) => (
          <Chip key={s.key} cls="bg-emerald-100 text-emerald-800">✓ {s.label}</Chip>
        ))}
        {a.sections_missing.map((s) => (
          <Chip key={s.key} cls={s.required ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'}>
            ✗ {s.label}{s.required ? ' (important)' : ''}
          </Chip>
        ))}
      </ul>
    </Section>
  )
}

function Extracted({ a }) {
  const empty = <p className="text-sm text-slate-500">Nothing recognised.</p>
  return (
    <Section title="What we read from your resume" subtitle="Check this is right: it shows what the analysis is based on.">
      <div className="space-y-4 text-sm">
        <div>
          <h3 className="font-semibold text-slate-900">Education</h3>
          {a.education.length === 0 ? empty : (
            <ul className="mt-1 space-y-1">
              {a.education.map((e) => (
                <li key={e.text} className="text-slate-700">
                  <strong>{e.degree}</strong>{e.institution ? ` · ${e.institution}` : ''}{e.years ? ` · ${e.years}` : ''}
                  {e.cgpa != null ? ` · CGPA ${e.cgpa}` : ''}{e.percentage != null ? ` · ${e.percentage}%` : ''}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Projects</h3>
          {a.projects.length === 0 ? empty : (
            <ul className="mt-1 space-y-2">
              {a.projects.map((p) => (
                <li key={p.title} className="text-slate-700">
                  <strong>{p.title}</strong>
                  {p.skills.length > 0 && <span className="text-slate-500"> · {p.skills.join(', ')}</span>}
                  {p.description && <p className="text-xs text-slate-500">{p.description.slice(0, 180)}{p.description.length > 180 ? '…' : ''}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Experience</h3>
          {a.experience.length === 0 ? empty : (
            <ul className="mt-1 space-y-1">
              {a.experience.map((e) => (
                <li key={e.title} className="text-slate-700"><strong>{e.title}</strong></li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Certifications</h3>
          {a.certifications.length === 0 ? empty : (
            <ul className="mt-1 list-disc pl-5 text-slate-700">
              {a.certifications.map((c) => <li key={c}>{c}</li>)}
            </ul>
          )}
        </div>
        <div>
          <h3 className="font-semibold text-slate-900">Relevant keywords</h3>
          {a.keywords.length === 0 ? empty : (
            <ul className="mt-1 flex flex-wrap gap-1.5" aria-label="Keywords">
              {a.keywords.map((k) => <Chip key={k} cls="border border-slate-300 text-slate-600">{k}</Chip>)}
            </ul>
          )}
        </div>
      </div>
    </Section>
  )
}

function ProfileComparison({ c }) {
  const rows = []
  if (c.resume_cgpa != null || c.profile_cgpa != null)
    rows.push(['CGPA', `Resume: ${c.resume_cgpa ?? 'not found'} · Profile: ${c.profile_cgpa ?? 'not entered'}`, c.cgpa_mismatch])
  return (
    <Section title="Resume vs your profile">
      <ul className="space-y-1.5 text-sm text-slate-700">
        {rows.map(([label, text, bad]) => (
          <li key={label} className={bad ? 'font-medium text-red-700' : ''}>{bad ? '✗' : '✓'} {label}: {text}</li>
        ))}
        {c.skills_not_on_resume.length > 0 && (
          <li>✗ In your profile but not on your resume: {c.skills_not_on_resume.join(', ')}</li>
        )}
        {c.skills_not_in_profile.length > 0 && (
          <li>✗ On your resume but not in your profile: {c.skills_not_in_profile.map((s) => s.name).join(', ')}</li>
        )}
        {c.skills_not_on_resume.length === 0 && c.skills_not_in_profile.length === 0 && <li>✓ Your skills match in both places.</li>}
      </ul>
      {c.missing_profile_information.length > 0 && (
        <p className="mt-3 text-sm text-slate-700">
          Missing profile information: {c.missing_profile_information.join(', ')}.{' '}
          <Link to="/student/profile" className="font-medium text-indigo-600 hover:underline">Update profile →</Link>
        </p>
      )}
    </Section>
  )
}

export default function ResumeAnalysis() {
  const [state, setState] = useState({ status: 'loading', analysis: null, error: '' })
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  const load = useCallback(() => {
    getMyResume()
      .then(async (resume) => {
        if (!resume) return setState({ status: 'none', analysis: null, error: '' })
        const analysis = await getAnalysis(resume.id)
        setState({ status: 'ready', analysis, error: '' })
      })
      .catch((err) => setState({ status: 'error', analysis: null, error: getErrorMessage(err) }))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const run = async (action, okMessage) => {
    setBusy(true)
    setNotice(null)
    try {
      const analysis = await action(state.analysis.resume.id)
      setState({ status: 'ready', analysis, error: '' })
      setNotice({ type: 'success', text: okMessage })
    } catch (err) {
      setNotice({ type: 'error', text: getErrorMessage(err) })
    } finally {
      setBusy(false)
    }
  }

  const view = async () => {
    try {
      window.open(await fetchResumeFile(state.analysis.resume.id), '_blank', 'noopener')
    } catch (err) {
      setNotice({ type: 'error', text: getErrorMessage(err) })
    }
  }

  if (state.status === 'loading') return <p className="p-8 text-center text-slate-500">Loading your analysis…</p>
  if (state.status === 'error')
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <p role="alert" className="text-red-600">{state.error}</p>
        <Link to="/student/resume" className="mt-4 inline-block text-indigo-600 hover:underline">Go to resume upload</Link>
      </div>
    )
  if (state.status === 'none')
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <h1 className="text-xl font-bold text-slate-900">No resume uploaded yet</h1>
        <p className="mt-2 text-slate-600">Upload a PDF resume to see its analysis.</p>
        <Link to="/student/resume" className={`${primaryButton} mt-4 inline-block`}>Upload resume</Link>
      </div>
    )

  const a = state.analysis
  return (
    <div className="mx-auto max-w-4xl space-y-5 px-4 py-8">
      {notice && (
        <div role={notice.type === 'error' ? 'alert' : 'status'}
          className={`rounded-md p-3 text-sm ${notice.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800'}`}>
          {notice.text}
        </div>
      )}
      <Overview a={a} busy={busy} onView={view} onReanalyze={() => run(reanalyze, 'Analysis refreshed.')} />
      <Suggestions items={a.suggestions} />
      <Skills a={a} busy={busy} onSync={() => run(syncSkills, 'Skills added to your profile.')} />
      <JobRelevance items={a.job_relevance} />
      <Sections a={a} />
      <ProfileComparison c={a.profile_comparison} />
      <Extracted a={a} />
      <p className="text-xs text-slate-500">{a.disclaimer}</p>
    </div>
  )
}

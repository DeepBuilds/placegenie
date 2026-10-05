import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { deleteResume, fetchResumeFile, getMyResume, uploadResume } from '../../api/resume'
import Section, { primaryButton, secondaryButton } from '../../components/profile/Section'
import { getErrorMessage } from '../../utils/errors'
import { MAX_RESUME_MB, formatDateTime, formatSize, validateResumeFile } from '../../utils/resume'

export default function Resume() {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [current, setCurrent] = useState({ status: 'loading', resume: null, error: '' })
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(null) // null = idle, 0-100 = uploading, 100 = analysing
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    getMyResume()
      .then((resume) => !cancelled && setCurrent({ status: 'ready', resume, error: '' }))
      .catch((err) => !cancelled && setCurrent({ status: 'error', resume: null, error: getErrorMessage(err) }))
    return () => {
      cancelled = true
    }
  }, [])

  const choose = (e) => {
    const picked = e.target.files?.[0] ?? null
    setFile(picked)
    setError(picked ? validateResumeFile(picked) : '')
  }

  const submit = async (e) => {
    e.preventDefault()
    const problem = validateResumeFile(file)
    if (problem) {
      setError(problem)
      return
    }
    setError('')
    setBusy(true)
    setProgress(0)
    try {
      await uploadResume(file, setProgress)
      navigate('/student/resume/analysis')
    } catch (err) {
      setError(getErrorMessage(err))
      setBusy(false)
      setProgress(null)
    }
  }

  const view = async () => {
    try {
      window.open(await fetchResumeFile(current.resume.id), '_blank', 'noopener')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const remove = async () => {
    if (!window.confirm('Delete your resume and its analysis? This cannot be undone.')) return
    setBusy(true)
    try {
      await deleteResume(current.resume.id)
      setCurrent({ status: 'ready', resume: null, error: '' })
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const { resume } = current

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">My resume</h1>
        <p className="text-sm text-slate-600">
          Upload your resume as a PDF to see which skills it shows, what is missing and how it matches open jobs.
        </p>
      </div>

      {current.status === 'loading' && <p className="text-slate-500">Loading…</p>}
      {current.status === 'error' && (
        <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-700">{current.error}</p>
      )}

      {resume && (
        <Section title="Current resume">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 text-sm">
              <p className="truncate font-medium text-slate-900">{resume.original_name}</p>
              <p className="text-slate-500">
                {formatSize(resume.size_bytes)}
                {resume.page_count ? ` · ${resume.page_count} page${resume.page_count === 1 ? '' : 's'}` : ''} · uploaded{' '}
                {formatDateTime(resume.uploaded_at)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to="/student/resume/analysis" className={primaryButton}>View analysis</Link>
              <button type="button" onClick={view} className={secondaryButton}>View PDF</button>
              <button type="button" onClick={remove} disabled={busy} className={secondaryButton}>Delete</button>
            </div>
          </div>
        </Section>
      )}

      <Section
        title={resume ? 'Replace your resume' : 'Upload your resume'}
        subtitle={`PDF only, up to ${MAX_RESUME_MB} MB. Scanned images are not supported: use a PDF saved from Word, Google Docs or similar.`}
      >
        <form onSubmit={submit} noValidate>
          <label htmlFor="resume-file" className="block text-sm font-medium text-slate-700">Resume (PDF)</label>
          <input
            ref={inputRef}
            id="resume-file"
            type="file"
            accept="application/pdf,.pdf"
            onChange={choose}
            disabled={busy}
            className="mt-1 block w-full text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
          />
          {file && !error && (
            <p className="mt-1 text-xs text-slate-500">{file.name} · {formatSize(file.size)}</p>
          )}
          {error && <p role="alert" className="mt-2 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

          {busy && progress !== null && (
            <div className="mt-3" role="status">
              <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {progress < 100 ? `Uploading… ${progress}%` : 'Reading and analysing your resume…'}
              </p>
            </div>
          )}

          <button type="submit" disabled={busy} className={`${primaryButton} mt-4`}>
            {busy ? 'Working…' : resume ? 'Upload and replace' : 'Upload and analyse'}
          </button>
        </form>
        {resume && (
          <p className="mt-3 text-xs text-slate-500">Uploading a new file replaces your current resume and its analysis.</p>
        )}
      </Section>
    </div>
  )
}

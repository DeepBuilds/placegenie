import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/resume'
import Resume from '../pages/student/Resume'
import ResumeAnalysis from '../pages/student/ResumeAnalysis'
import { formatSize, validateResumeFile } from '../utils/resume'

vi.mock('../api/resume')

const resume = { id: 4, original_name: 'asha_resume.pdf', size_bytes: 52000, page_count: 1, uploaded_at: '2026-10-05T10:00:00' }

const analysis = {
  resume, detected_name: 'Asha Patil', word_count: 251, page_count: 1, completeness_score: 78,
  score_breakdown: [{ label: 'Contact details', earned: 20, max: 20, note: 'email 8, phone 6, link 6' }],
  contact: { email: true, phone: true, linkedin: false, github: true },
  sections_found: [{ key: 'education', label: 'Education', required: true }, { key: 'skills', label: 'Skills', required: true }],
  sections_missing: [{ key: 'projects', label: 'Projects', required: true }, { key: 'certifications', label: 'Certifications', required: false }],
  education: [{ degree: 'B.Tech', institution: 'ABC Institute', years: '2024 - 2028', cgpa: 8.4, percentage: null, text: 'B.Tech' }],
  projects: [], experience: [{ title: 'Data Intern - Acme', dates: null, description: '', bullets: [], skills: [] }],
  certifications: ['Google Data Analytics Certificate'],
  skills: [
    { skill_id: 1, name: 'Python', category: 'Programming', evidence: ['skills', 'projects'], in_profile: true },
    { skill_id: 2, name: 'SQL', category: 'Database', evidence: ['skills'], in_profile: false },
  ],
  keywords: ['dashboards', 'analytics'],
  potentially_missing_skills: [{ name: 'Power BI', jobs_requiring: 2, example_jobs: ['Data Analyst'] }],
  job_relevance: [{ job_id: 9, title: 'Data Analyst', company: 'Aurora Analytics', relevance: 83, matched_skills: ['Python'], missing_skills: ['Power BI'] }],
  profile_comparison: {
    skills_not_in_profile: [{ skill_id: 2, name: 'SQL' }], skills_not_on_resume: ['Docker'],
    resume_cgpa: 8.4, profile_cgpa: 7.1, cgpa_mismatch: true, missing_profile_information: ['Phone number'],
  },
  suggestions: [
    { severity: 'high', category: 'Missing section', text: 'Add a Projects section.' },
    { severity: 'low', category: 'Contact', text: 'Add your LinkedIn link.' },
  ],
  disclaimer: 'This is an automated, keyword-based analysis.',
}

const pdf = (name = 'cv.pdf', type = 'application/pdf', size) => {
  const f = new File(['%PDF-1.4 test'], name, { type })
  if (size !== undefined) Object.defineProperty(f, 'size', { value: size })
  return f
}

function renderApp(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/student/resume" element={<Resume />} />
        <Route path="/student/resume/analysis" element={<ResumeAnalysis />} />
        <Route path="/student/jobs/:id" element={<p>job page</p>} />
        <Route path="/student/profile" element={<p>profile page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getMyResume.mockResolvedValue(null)
  api.getAnalysis.mockResolvedValue(analysis)
})

describe('upload validation helpers', () => {
  it('validateResumeFile accepts a PDF and rejects other files', () => {
    expect(validateResumeFile(pdf())).toBe('')
    expect(validateResumeFile(null)).toMatch(/choose/i)
    expect(validateResumeFile(pdf('cv.docx', 'application/msword'))).toMatch(/only pdf/i)
    expect(validateResumeFile(pdf('cv.pdf', 'image/png'))).toMatch(/does not look like a pdf/i)
    expect(validateResumeFile(pdf('cv.pdf', 'application/pdf', 0))).toMatch(/empty/i)
    expect(validateResumeFile(pdf('cv.pdf', 'application/pdf', 6 * 1024 * 1024))).toMatch(/too large/i)
    expect(formatSize(2048)).toBe('2 KB')
  })
})

describe('resume upload page', () => {
  it('invites the first upload when there is no resume', async () => {
    renderApp('/student/resume')
    expect(await screen.findByRole('heading', { name: 'Upload your resume' })).toBeInTheDocument()
    expect(screen.queryByText('Current resume')).not.toBeInTheDocument()
  })

  it('rejects a non-PDF file in the browser without calling the API', async () => {
    renderApp('/student/resume')
    const input = await screen.findByLabelText('Resume (PDF)')
    await userEvent.upload(input, pdf('notes.txt', 'text/plain'), { applyAccept: false })
    expect(await screen.findByRole('alert')).toHaveTextContent(/only pdf/i)
    await userEvent.click(screen.getByRole('button', { name: 'Upload and analyse' }))
    expect(api.uploadResume).not.toHaveBeenCalled()
  })

  it('rejects an oversized file and an empty selection', async () => {
    renderApp('/student/resume')
    const input = await screen.findByLabelText('Resume (PDF)')
    await userEvent.upload(input, pdf('big.pdf', 'application/pdf', 9 * 1024 * 1024))
    expect(await screen.findByRole('alert')).toHaveTextContent(/too large/i)
    expect(api.uploadResume).not.toHaveBeenCalled()
  })

  it('asks for a file when the form is submitted empty', async () => {
    renderApp('/student/resume')
    await userEvent.click(await screen.findByRole('button', { name: 'Upload and analyse' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/choose a pdf/i)
  })

  it('uploads a valid PDF and opens the analysis', async () => {
    api.uploadResume.mockResolvedValue(analysis)
    api.getMyResume.mockResolvedValueOnce(null).mockResolvedValue(resume)
    renderApp('/student/resume')
    await userEvent.upload(await screen.findByLabelText('Resume (PDF)'), pdf('asha.pdf'))
    await userEvent.click(screen.getByRole('button', { name: 'Upload and analyse' }))
    expect(api.uploadResume).toHaveBeenCalledWith(expect.objectContaining({ name: 'asha.pdf' }), expect.any(Function))
    expect(await screen.findByRole('heading', { name: 'Resume analysis' })).toBeInTheDocument()
  })

  it('shows the server error and stays on the page when the upload fails', async () => {
    api.uploadResume.mockRejectedValue({ response: { status: 422, data: { detail: 'No readable text was found in this PDF.' } } })
    renderApp('/student/resume')
    await userEvent.upload(await screen.findByLabelText('Resume (PDF)'), pdf())
    await userEvent.click(screen.getByRole('button', { name: 'Upload and analyse' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No readable text was found in this PDF.')
    expect(screen.getByRole('button', { name: 'Upload and analyse' })).toBeEnabled()
  })

  it('shows the current resume with view, replace and delete', async () => {
    api.getMyResume.mockResolvedValue(resume)
    renderApp('/student/resume')
    expect(await screen.findByText('asha_resume.pdf')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View analysis' })).toHaveAttribute('href', '/student/resume/analysis')
    expect(screen.getByRole('heading', { name: 'Replace your resume' })).toBeInTheDocument()
  })

  it('deletes the resume only after confirmation', async () => {
    api.getMyResume.mockResolvedValue(resume)
    api.deleteResume.mockResolvedValue({})
    const confirm = vi.spyOn(window, 'confirm')
    renderApp('/student/resume')
    const del = await screen.findByRole('button', { name: 'Delete' })

    confirm.mockReturnValueOnce(false) // cancel: nothing happens
    await userEvent.click(del)
    expect(confirm).toHaveBeenCalledTimes(1)
    expect(api.deleteResume).not.toHaveBeenCalled()

    confirm.mockReturnValueOnce(true) // confirm: the resume is deleted
    await userEvent.click(del)
    await waitFor(() => expect(api.deleteResume).toHaveBeenCalledWith(4))
    expect(await screen.findByRole('heading', { name: 'Upload your resume' })).toBeInTheDocument()
    confirm.mockRestore()
  })
})

describe('analysis page', () => {
  beforeEach(() => {
    api.getMyResume.mockResolvedValue(resume)
  })

  it('shows the score, detected name, contact checks and suggestions in priority order', async () => {
    renderApp('/student/resume/analysis')
    expect(await screen.findByRole('heading', { name: 'Resume analysis' })).toBeInTheDocument()
    expect(screen.getByLabelText('Completeness 78 out of 100')).toBeInTheDocument()
    expect(screen.getByText('Asha Patil')).toBeInTheDocument()
    const contacts = screen.getByRole('list', { name: 'Contact details found' })
    expect(within(contacts).getByText(/✓ Email/)).toBeInTheDocument()
    expect(within(contacts).getByText(/✗ LinkedIn/)).toBeInTheDocument()
    const texts = screen.getAllByText(/Add (a Projects section|your LinkedIn link)/).map((n) => n.textContent)
    expect(texts[0]).toMatch(/Projects/)
    expect(screen.getByText('Important')).toBeInTheDocument()
  })

  it('lists detected skills, flags those already in the profile, and shows potentially missing skills', async () => {
    renderApp('/student/resume/analysis')
    const skills = await screen.findByRole('list', { name: 'Detected skills' })
    expect(within(skills).getByText('✓ Python')).toBeInTheDocument()
    expect(within(skills).getByText('SQL')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Potentially missing skills' })).getByText(/Power BI · 2 jobs/)).toBeInTheDocument()
  })

  it('adds detected skills to the profile and shows the refreshed analysis', async () => {
    const synced = { ...analysis, skills: analysis.skills.map((s) => ({ ...s, in_profile: true })),
      profile_comparison: { ...analysis.profile_comparison, skills_not_in_profile: [] } }
    api.syncSkills.mockResolvedValue(synced)
    renderApp('/student/resume/analysis')
    await userEvent.click(await screen.findByRole('button', { name: 'Add 1 detected skill to my profile' }))
    expect(api.syncSkills).toHaveBeenCalledWith(4)
    expect(await screen.findByText('Skills added to your profile.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /detected skill/ })).not.toBeInTheDocument()
  })

  it('shows job relevance with a link to each job', async () => {
    renderApp('/student/resume/analysis')
    const link = await screen.findByRole('link', { name: /Data Analyst/ })
    expect(link).toHaveAttribute('href', '/student/jobs/9')
    expect(screen.getByText('83%')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Relevance to Data Analyst' })).toHaveAttribute('aria-valuenow', '83')
    await userEvent.click(link)
    expect(await screen.findByText('job page')).toBeInTheDocument()
  })

  it('shows found and missing sections, marking important ones', async () => {
    renderApp('/student/resume/analysis')
    const list = await screen.findByRole('list', { name: 'Sections found' })
    expect(within(list).getByText('✓ Education')).toBeInTheDocument()
    expect(within(list).getByText('✗ Projects (important)')).toBeInTheDocument()
    expect(within(list).getByText('✗ Certifications')).toBeInTheDocument()
  })

  it('compares the resume with the profile', async () => {
    renderApp('/student/resume/analysis')
    expect(await screen.findByText(/CGPA: Resume: 8.4 · Profile: 7.1/)).toBeInTheDocument()
    expect(screen.getByText(/In your profile but not on your resume: Docker/)).toBeInTheDocument()
    expect(screen.getByText(/On your resume but not in your profile: SQL/)).toBeInTheDocument()
    expect(screen.getByText(/Missing profile information: Phone number/)).toBeInTheDocument()
  })

  it('shows extracted details, keywords and the disclaimer', async () => {
    renderApp('/student/resume/analysis')
    expect(await screen.findByText(/ABC Institute/)).toBeInTheDocument()
    expect(screen.getByText('Google Data Analytics Certificate')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Keywords' })).getByText('dashboards')).toBeInTheDocument()
    expect(screen.getByText(/automated, keyword-based analysis/)).toBeInTheDocument()
  })

  it('re-analyses on request', async () => {
    api.reanalyze.mockResolvedValue({ ...analysis, completeness_score: 80 })
    renderApp('/student/resume/analysis')
    await userEvent.click(await screen.findByRole('button', { name: 'Re-analyse' }))
    expect(await screen.findByLabelText('Completeness 80 out of 100')).toBeInTheDocument()
  })

  it('invites an upload when there is no resume', async () => {
    api.getMyResume.mockResolvedValue(null)
    renderApp('/student/resume/analysis')
    expect(await screen.findByText('No resume uploaded yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Upload resume' })).toHaveAttribute('href', '/student/resume')
  })

  it('shows an error when the analysis cannot be loaded', async () => {
    api.getAnalysis.mockRejectedValue({ response: { status: 500, data: {} } })
    renderApp('/student/resume/analysis')
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })

  it('shows empty-state text for a resume with no recognised skills', async () => {
    api.getAnalysis.mockResolvedValue({ ...analysis, skills: [], potentially_missing_skills: [], job_relevance: [], suggestions: [],
      profile_comparison: { ...analysis.profile_comparison, skills_not_in_profile: [], skills_not_on_resume: [] } })
    renderApp('/student/resume/analysis')
    expect(await screen.findByText(/No known skills were recognised/)).toBeInTheDocument()
    expect(screen.getByText(/No suggestions/)).toBeInTheDocument()
    expect(screen.getByText(/no open jobs to compare/i)).toBeInTheDocument()
  })
})

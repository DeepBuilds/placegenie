import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as appsApi from '../api/applications'
import * as jobsApi from '../api/jobs'
import SkillGapPanel from '../components/jobs/SkillGapPanel'
import JobDetails from '../pages/student/JobDetails'
import SkillGap from '../pages/student/SkillGap'

vi.mock('../api/jobs')
vi.mock('../api/applications')

const matched = (id, name, required = true, level = 'intermediate') => ({ skill_id: id, name, category: null, required, essential: false, weight: 2, student_level: level })
const missing = (id, name, priority, reasons, required = true) => ({
  skill_id: id, name, category: null, required, essential: priority === 'high', weight: 3, priority, reasons, jobs_requiring: 5, demand_share: 0.3,
})

const base = {
  job: { id: 7, title: 'Data Analyst', company: 'Aurora Analytics' }, has_requirements: true, match_percentage: 50,
  required_match_percentage: 67, matched_count: 2, missing_count: 2, total_count: 4, required_total: 3, required_matched: 2,
  matched_skills: [matched(1, 'Python'), matched(2, 'SQL')],
  missing_skills: [
    missing(3, 'Docker', 'high', ['Required for this job', 'Essential: this job gives it a weight of 3 out of 5', 'Asked for in 6 of 18 open jobs (33%): frequently requested']),
    missing(4, 'Power BI', 'low', ['Preferred for this job (nice to have)'], false),
  ],
  priority: [
    { rank: 1, skill_id: 3, name: 'Docker', level: 'high', reasons: ['Required for this job', 'Essential: this job gives it a weight of 3 out of 5'] },
    { rank: 2, skill_id: 4, name: 'Power BI', level: 'low', reasons: ['Preferred for this job (nice to have)'] },
  ],
  student_has_skills: true, summary: 'You have 2 of 4 skills (50%). Required skills: 2 of 3.', notes: [],
  open_jobs_compared: 18, disclaimer: 'Priorities come from this job requirements. They are guidance only.',
}

const renderPanel = (props = { jobId: 7 }) =>
  render(
    <MemoryRouter>
      <SkillGapPanel {...props} />
    </MemoryRouter>,
  )

beforeEach(() => {
  vi.resetAllMocks()
  jobsApi.getSkillGap.mockResolvedValue(base)
  appsApi.getMyApplications.mockResolvedValue({ items: [], total: 0, counts: {} })
})

describe('skill gap panel', () => {
  it('shows match %, progress bars, matched and missing skills', async () => {
    renderPanel()
    expect(await screen.findByLabelText('Skill match 50 percent')).toBeInTheDocument()
    expect(jobsApi.getSkillGap).toHaveBeenCalledWith(7)
    expect(screen.getByText('You have 2 of 4 skills (50%). Required skills: 2 of 3.')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Skill match' })).toHaveAttribute('aria-valuenow', '50')
    expect(screen.getByRole('progressbar', { name: 'Required skills matched' })).toHaveAttribute('aria-valuenow', '67')
    const m = within(screen.getByRole('list', { name: 'Matched skills' }))
    expect(m.getByText('Python')).toBeInTheDocument()
    expect(m.getAllByText('✓')).toHaveLength(2)
    expect(m.getAllByText(/your level: intermediate/)).toHaveLength(2)
    const x = within(screen.getByRole('list', { name: 'Missing skills' }))
    expect(x.getByText('Docker')).toBeInTheDocument()
    expect(x.getAllByText('✗')).toHaveLength(2)
  })

  it('labels the priority of each missing skill and explains it', async () => {
    renderPanel()
    const list = within(await screen.findByRole('list', { name: 'Missing skills' }))
    expect(list.getByText('High priority')).toBeInTheDocument()
    expect(list.getByText('Low priority')).toBeInTheDocument()
    expect(list.getByText(/Essential: this job gives it a weight of 3 out of 5/)).toBeInTheDocument()
    expect(list.getByText(/Asked for in 6 of 18 open jobs/)).toBeInTheDocument()
  })

  it('lists skills to prioritise in rank order', async () => {
    renderPanel()
    const items = within(await screen.findByRole('list', { name: 'Skills to prioritise' })).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('1Docker')
    expect(items[1]).toHaveTextContent('2Power BI')
  })

  it('shows a complete match', async () => {
    jobsApi.getSkillGap.mockResolvedValue({ ...base, match_percentage: 100, required_match_percentage: 100, matched_count: 4, missing_count: 0,
      matched_skills: [matched(1, 'Python'), matched(2, 'SQL'), matched(3, 'Docker'), matched(4, 'Power BI', false)], missing_skills: [], priority: [],
      required_matched: 3, summary: 'You have all 4 skills this job asks for.' })
    renderPanel()
    expect(await screen.findByLabelText('Skill match 100 percent')).toBeInTheDocument()
    expect(screen.getByText(/Nothing missing/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Skills to prioritise' })).not.toBeInTheDocument()
  })

  it('shows a zero match', async () => {
    jobsApi.getSkillGap.mockResolvedValue({ ...base, match_percentage: 0, required_match_percentage: 0, matched_count: 0, matched_skills: [], required_matched: 0 })
    renderPanel()
    expect(await screen.findByLabelText('Skill match 0 percent')).toBeInTheDocument()
    expect(screen.getByText(/None of this job's skills are in your profile yet/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Matched skills' })).not.toBeInTheDocument()
  })

  it('tells a student with no skills how to fix it', async () => {
    jobsApi.getSkillGap.mockResolvedValue({ ...base, match_percentage: 0, student_has_skills: false, matched_skills: [], matched_count: 0,
      notes: ['Your profile has no skills yet. Add the skills you have so the comparison is meaningful.'] })
    renderPanel()
    expect(await screen.findByText(/Your profile has no skills yet/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Add skills to my profile/ })).toHaveAttribute('href', '/student/profile')
  })

  it('handles a job that lists no skills without showing a percentage', async () => {
    jobsApi.getSkillGap.mockResolvedValue({ ...base, has_requirements: false, match_percentage: null, required_match_percentage: null,
      matched_skills: [], missing_skills: [], priority: [], total_count: 0, summary: 'This job lists no specific skills, so there is nothing to compare.' })
    renderPanel()
    expect(await screen.findByText(/nothing to compare/)).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.queryByText(/Matched \(/)).not.toBeInTheDocument()
  })

  it('omits the required-skills bar when the job has no required skills', async () => {
    jobsApi.getSkillGap.mockResolvedValue({ ...base, required_match_percentage: null, required_total: 0, required_matched: 0,
      notes: ['This job lists only preferred skills; none are strictly required.'] })
    renderPanel()
    expect(await screen.findByLabelText('Skill match 50 percent')).toBeInTheDocument()
    expect(screen.queryByRole('progressbar', { name: 'Required skills matched' })).not.toBeInTheDocument()
    expect(screen.getByText(/only preferred skills/)).toBeInTheDocument()
  })

  it('shows an error message and the disclaimer', async () => {
    jobsApi.getSkillGap.mockRejectedValueOnce({ response: { status: 404, data: { detail: 'Job not found.' } } })
    const { unmount } = renderPanel()
    expect(await screen.findByRole('alert')).toHaveTextContent('Job not found.')
    unmount()
    renderPanel()
    expect(await screen.findByText(/guidance only/)).toBeInTheDocument()
  })

  it('reloads when the job changes', async () => {
    const view = renderPanel({ jobId: 7 })
    await screen.findByLabelText('Skill match 50 percent')
    jobsApi.getSkillGap.mockResolvedValue({ ...base, match_percentage: 80 })
    view.rerender(<MemoryRouter><SkillGapPanel jobId={8} /></MemoryRouter>)
    expect(await screen.findByLabelText('Skill match 80 percent')).toBeInTheDocument()
    expect(jobsApi.getSkillGap).toHaveBeenLastCalledWith(8)
  })
})

describe('skill gap on the job details page', () => {
  it('includes a Skill gap section with a link to the full page', async () => {
    jobsApi.getJob.mockResolvedValue({
      id: 7, title: 'Data Analyst', description: 'x', location: 'Pune', job_type: 'full_time', min_cgpa: 7, max_backlogs: 1,
      min_experience_months: 0, deadline: '2030-01-01', is_expired: false, status: 'open',
      company: { id: 1, name: 'Aurora Analytics', industry: 'Data', location: 'Pune' }, role: null, skills: [],
      allowed_branches: [], required_certifications: [], created_at: '2026-01-01T00:00:00',
    })
    jobsApi.getCompany.mockResolvedValue({ id: 1, name: 'Aurora Analytics', industry: 'Data', location: 'Pune', website: null, description: null, open_jobs: 1 })
    render(
      <MemoryRouter initialEntries={['/student/jobs/7']}>
        <Routes><Route path="/student/jobs/:id" element={<JobDetails />} /></Routes>
      </MemoryRouter>,
    )
    expect(await screen.findByRole('heading', { name: 'Skill gap' })).toBeInTheDocument()
    expect(await screen.findByLabelText('Skill match 50 percent')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open full skill-gap page/ })).toHaveAttribute('href', '/student/skill-gap?job_id=7')
  })
})

describe('dedicated skill gap page', () => {
  const jobs = {
    items: [
      { id: 7, title: 'Data Analyst', company: { id: 1, name: 'Aurora Analytics' } },
      { id: 9, title: 'Security Analyst', company: { id: 2, name: 'Helix Secure' } },
    ], total: 2, limit: 100, offset: 0,
  }
  const renderPage = (path = '/student/skill-gap') =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/student/skill-gap" element={<SkillGap />} />
          <Route path="/student/jobs/:id" element={<p>job page</p>} />
        </Routes>
      </MemoryRouter>,
    )
  beforeEach(() => {
    jobsApi.getJobs.mockResolvedValue(jobs)
  })

  it('asks the student to choose a job first', async () => {
    renderPage()
    expect(await screen.findByText(/Choose a job above/)).toBeInTheDocument()
    expect(jobsApi.getSkillGap).not.toHaveBeenCalled()
    expect(jobsApi.getJobs).toHaveBeenCalledWith(expect.objectContaining({ limit: 100, sort: 'title' }))
  })

  it('loads the comparison when a job is picked', async () => {
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Job'), 'Security Analyst · Helix Secure')
    expect(await screen.findByLabelText('Skill match 50 percent')).toBeInTheDocument()
    expect(jobsApi.getSkillGap).toHaveBeenCalledWith('9')
    expect(screen.getByRole('heading', { name: 'Security Analyst at Helix Secure' })).toBeInTheDocument()
  })

  it('opens straight to a job from the URL', async () => {
    renderPage('/student/skill-gap?job_id=7')
    expect(await screen.findByLabelText('Skill match 50 percent')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Data Analyst at Aurora Analytics' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: /View job details/ }))
    expect(await screen.findByText('job page')).toBeInTheDocument()
  })

  it('reports a failure to load the job list', async () => {
    jobsApi.getJobs.mockRejectedValue({ response: { status: 500, data: {} } })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })
})

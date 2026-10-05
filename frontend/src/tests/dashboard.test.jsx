import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/dashboard'
import Dashboard from '../pages/student/Dashboard'
import { daysLeft, deadlineText } from '../utils/dates'

vi.mock('../api/dashboard')

const card = (over = {}) => ({
  job_id: 3, title: 'Data Analyst', company: 'Aurora Analytics', location: 'Bengaluru', deadline: '2030-01-10',
  match_score: 87, eligibility: 'ELIGIBLE', missing_skills: [], already_applied: false, ...over,
})

const FULL = {
  generated_at: '2026-10-05T10:00:00',
  student: { name: 'Asha Patil', first_name: 'Asha', branch: 'Computer Science and Engineering', year: 2, semester: 3, cgpa: 8.2 },
  profile: { score: 78, missing: ['Interests', 'Preferred job roles'], skills: 5, projects: 1, certifications: 0 },
  resume: { uploaded: true, filename: 'asha_cv.pdf', uploaded_at: '2026-10-01T09:00:00', completeness_score: 91, skills_detected: 14,
    top_suggestions: ['Mention the technologies used in every project.'] },
  recommendations: { open_jobs: 18, eligible: 3, incomplete_profile: 0, not_eligible: 15, hints: [],
    top: [card(), card({ job_id: 7, title: 'Security Analyst', company: 'Helix Secure', match_score: 31, eligibility: 'NOT_ELIGIBLE', already_applied: true })] },
  opportunities: { eligible_count: 3, eligible_percent: 17,
    items: [card({ job_id: 5, title: 'Machine Learning Engineer', company: 'Aurora Analytics', match_score: 81 })],
    closing_soon: [card({ job_id: 9, title: 'QA Engineer', company: 'BrightPath', deadline: '2030-01-03' })] },
  applications: { total: 3, active: 2, by_status: { applied: 1, shortlisted: 1, withdrawn: 1 },
    recent: [{ id: 11, job_title: 'Data Analyst', company: 'Aurora Analytics', status: 'shortlisted', applied_at: '2026-10-01T10:00:00', next_interview: '2030-05-20T14:30:00' }] },
  interviews: { upcoming: [{ id: 21, application_id: 11, stage: 'technical_interview', scheduled_at: '2030-05-20T14:30:00', job_title: 'Data Analyst', company: 'Aurora Analytics' }],
    upcoming_count: 1, needs_result: 1, total: 3, passed: 1, not_cleared: 1, pending: 1 },
  skill_gaps: { student_has_skills: true, based_on_jobs: 10, top_missing: [{ name: 'Docker', jobs_needing: 4, example_jobs: ['Cloud Support Engineer'] }, { name: 'AWS', jobs_needing: 2, example_jobs: [] }],
    closest_job: { job_id: 1, title: 'Cloud Support Engineer', company: 'Nimbus Cloudworks', match_score: 52, missing_skills: ['Docker'] } },
  progress: { percent: 50, done: 3, total: 6, next_step: { key: 'interviewed', label: 'Record an interview', reason: 'Keep dates and notes for every round in one place.', link: '/student/interviews' },
    milestones: [
      { key: 'profile', label: 'Complete your profile', done: false, detail: '78% complete', link: '/student/profile' },
      { key: 'resume', label: 'Upload your resume', done: true, detail: 'Uploaded', link: '/student/resume' },
      { key: 'applied', label: 'Apply to a job', done: true, detail: '2 applications', link: '/student/recommendations' },
      { key: 'progressed', label: 'Get shortlisted', done: true, detail: '1 moved forward', link: '/student/applications' },
      { key: 'interviewed', label: 'Record an interview', done: false, detail: 'None recorded yet', link: '/student/interviews' },
      { key: 'selected', label: 'Receive an offer', done: false, detail: 'Not yet', link: '/student/applications' },
    ] },
  statistics: { open_jobs: 18, companies_hiring: 9, closing_this_week: 4, eligible_percent: 17, interview_pass_rate: 50,
    in_demand_skills: [{ name: 'Python', jobs: 6, you_have: true }, { name: 'Docker', jobs: 4, you_have: false }],
    application_funnel: [{ status: 'applied', count: 1 }, { status: 'shortlisted', count: 1 }, { status: 'online_assessment', count: 0 },
      { status: 'technical_interview', count: 0 }, { status: 'hr_interview', count: 0 }, { status: 'selected', count: 0 }, { status: 'rejected', count: 0 }] },
  errors: {},
}

const EMPTY = {
  ...FULL,
  student: { name: 'New Student', first_name: 'New', branch: null, year: null, semester: null, cgpa: null },
  profile: { score: 0, missing: ['Phone number', 'CGPA'], skills: 0, projects: 0, certifications: 0 },
  resume: { uploaded: false, filename: null, uploaded_at: null, completeness_score: null, skills_detected: null, top_suggestions: [] },
  recommendations: { open_jobs: 18, eligible: 0, incomplete_profile: 0, not_eligible: 18, hints: ['Add your skills: skill match is the biggest part of the score.'], top: [card({ match_score: 0, eligibility: 'NOT_ELIGIBLE' })] },
  opportunities: { eligible_count: 0, eligible_percent: 0, items: [], closing_soon: [] },
  applications: { total: 0, active: 0, by_status: {}, recent: [] },
  interviews: { upcoming: [], upcoming_count: 0, needs_result: 0, total: 0, passed: 0, not_cleared: 0, pending: 0 },
  skill_gaps: { student_has_skills: false, based_on_jobs: 0, top_missing: [], closest_job: null },
  progress: { ...FULL.progress, percent: 0, done: 0, next_step: { key: 'profile', label: 'Complete your profile', reason: 'Eligibility and recommendations are only as good as your profile.', link: '/student/profile' },
    milestones: FULL.progress.milestones.map((m) => ({ ...m, done: false })) },
  statistics: { ...FULL.statistics, interview_pass_rate: null, in_demand_skills: [{ name: 'Python', jobs: 6, you_have: false }], application_funnel: FULL.statistics.application_funnel.map((f) => ({ ...f, count: 0 })) },
}

function renderDashboard() {
  return render(
    <MemoryRouter initialEntries={['/student']}>
      <Routes>
        <Route path="/student" element={<Dashboard />} />
        <Route path="/student/*" element={<p>other page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

const widget = (name) => within(screen.getByRole('region', { name }))

beforeEach(() => {
  vi.resetAllMocks()
  api.getDashboard.mockResolvedValue(FULL)
})

describe('loading and errors', () => {
  it('shows skeletons while loading, then the real data', async () => {
    let resolve
    api.getDashboard.mockReturnValue(new Promise((r) => { resolve = r }))
    renderDashboard()
    expect(screen.getByRole('status', { name: 'Loading summary' })).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Loading Recommended for you' })).toBeInTheDocument()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    resolve(FULL)
    expect(await screen.findByText(/Asha/)).toBeInTheDocument()
    expect(screen.queryByRole('status', { name: /Loading/ })).not.toBeInTheDocument()
  })

  it('shows an error with a retry when the dashboard cannot be loaded at all', async () => {
    api.getDashboard.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce(FULL)
    renderDashboard()
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    expect(screen.getByRole('heading', { name: 'Your dashboard could not be loaded' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText(/Asha/)).toBeInTheDocument()
  })

  it('shows an error only in the section that failed and can retry it', async () => {
    api.getDashboard
      .mockResolvedValueOnce({ ...FULL, statistics: null, errors: { statistics: 'This section could not be loaded right now.' } })
      .mockResolvedValueOnce(FULL)
    renderDashboard()
    const stats = await screen.findByRole('region', { name: 'Placement statistics' })
    expect(within(stats).getByRole('alert')).toHaveTextContent('could not be loaded')
    expect(widget('Recommended for you').getByText('Data Analyst')).toBeInTheDocument() // the rest is fine
    await userEvent.click(within(stats).getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(api.getDashboard).toHaveBeenCalledTimes(2))
    expect(await widget('Placement statistics').findByText('Companies hiring')).toBeInTheDocument()
  })

  it('refreshes on request', async () => {
    renderDashboard()
    await userEvent.click(await screen.findByRole('button', { name: 'Refresh' }))
    await waitFor(() => expect(api.getDashboard).toHaveBeenCalledTimes(2))
  })
})

describe('with data', () => {
  it('greets the student and shows the summary cards', async () => {
    renderDashboard()
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(/Good (morning|afternoon|evening), Asha/)
    expect(screen.getByText(/Computer Science and Engineering · Year 2 · CGPA 8.2/)).toBeInTheDocument()
    const kpis = within(screen.getByRole('list', { name: 'Summary' }))
    expect(kpis.getByText('78%')).toBeInTheDocument()
    expect(kpis.getByText('of 18 open jobs')).toBeInTheDocument()
    expect(kpis.getByText('2 items left')).toBeInTheDocument()
    expect(kpis.getByText('Active applications').closest('a')).toHaveAttribute('href', '/student/applications')
    expect(kpis.getByText(/Next: /)).toBeInTheDocument()
    expect(kpis.getByText('1 moved forward')).toBeInTheDocument()
  })

  it('points to the next step', async () => {
    renderDashboard()
    const next = await screen.findByRole('link', { name: 'Recommended next step' })
    expect(next).toHaveAttribute('href', '/student/interviews')
    expect(next).toHaveTextContent('Record an interview')
    expect(next).toHaveTextContent('Keep dates and notes for every round in one place.')
  })

  it('shows placement progress with completed and open milestones', async () => {
    renderDashboard()
    const progress = widget('Your placement progress')
    expect(await progress.findByText('3 of 6 milestones')).toBeInTheDocument()
    expect(progress.getByRole('progressbar', { name: 'Placement progress' })).toHaveAttribute('aria-valuenow', '50')
    const items = progress.getAllByRole('listitem')
    expect(items).toHaveLength(6)
    expect(items[1]).toHaveTextContent('Upload your resume (done)')
    expect(items[0]).not.toHaveTextContent('(done)')
    expect(items[0]).toHaveTextContent('78% complete')
  })

  it('lists recommended jobs with score, eligibility and whether you applied', async () => {
    renderDashboard()
    const list = within(await screen.findByRole('list', { name: 'Recommended jobs' }))
    expect(list.getByRole('link', { name: 'Data Analyst' })).toHaveAttribute('href', '/student/jobs/3')
    expect(list.getByLabelText('87 percent match')).toBeInTheDocument()
    expect(list.getByText('✓ Eligible')).toBeInTheDocument()
    expect(list.getByText('✗ Not eligible')).toBeInTheDocument()
    expect(list.getByText('Applied')).toBeInTheDocument()
  })

  it('shows eligible opportunities and what closes soon', async () => {
    renderDashboard()
    const w = widget('Eligible opportunities')
    expect(await w.findByText(/You meet the requirements for/)).toHaveTextContent('3 open jobs (17%)')
    expect(w.getByRole('link', { name: 'Machine Learning Engineer' })).toBeInTheDocument()
    const closing = within(w.getByRole('list', { name: 'Closing soon' }))
    expect(closing.getByRole('link', { name: /QA Engineer · BrightPath/ })).toHaveAttribute('href', '/student/jobs/9')
    expect(closing.getByText(/Closes in|Deadline passed|Closes/)).toBeInTheDocument()
  })

  it('shows application counts by status and the recent applications', async () => {
    renderDashboard()
    const w = widget('Applications')
    const funnel = within(await w.findByRole('list', { name: 'Applications by status' }))
    expect(funnel.getAllByRole('listitem')).toHaveLength(2) // only the statuses that have applications
    expect(funnel.getByText('Shortlisted')).toBeInTheDocument()
    const recent = within(w.getByRole('list', { name: 'Recent applications' }))
    expect(recent.getByRole('link', { name: /Data Analyst/ })).toHaveAttribute('href', '/student/applications/11')
    expect(recent.getByText('Shortlisted')).toBeInTheDocument()
  })

  it('shows upcoming interviews and flags past ones with no result', async () => {
    renderDashboard()
    const w = widget('Interviews')
    const list = within(await w.findByRole('list', { name: 'Upcoming interviews' }))
    expect(list.getByText(/Technical interview · Data Analyst at Aurora Analytics/)).toBeInTheDocument()
    expect(list.getByRole('link')).toHaveAttribute('href', '/student/interviews/21')
    expect(w.getByRole('status')).toHaveTextContent('1 past interview has no result yet')
    expect(w.getByText(/Recorded: 3 · passed 1 · not cleared 1 · result pending 1/)).toBeInTheDocument()
  })

  it('shows the resume status, score and suggestions', async () => {
    renderDashboard()
    const w = widget('Resume')
    expect(await w.findByText('asha_cv.pdf')).toBeInTheDocument()
    expect(w.getByText('91/100')).toBeInTheDocument()
    expect(w.getByText('14 skills recognised')).toBeInTheDocument()
    expect(w.getByText('Mention the technologies used in every project.')).toBeInTheDocument()
  })

  it('shows skill gaps and the closest opportunity', async () => {
    renderDashboard()
    const w = widget('Skill gaps')
    const list = within(await w.findByRole('list', { name: 'Skills to learn' }))
    expect(list.getByText('Docker')).toBeInTheDocument()
    expect(list.getByText('needed by 4 jobs')).toBeInTheDocument()
    expect(list.getByText('needed by 2 jobs')).toBeInTheDocument()
    const closest = w.getByRole('link', { name: /Closest opportunity: Cloud Support Engineer at Nimbus Cloudworks/ })
    expect(closest).toHaveAttribute('href', '/student/skill-gap?job_id=1')
    expect(closest).toHaveTextContent('Only one skill stands in the way: Docker')
  })

  it('words the closest opportunity correctly for several missing skills', async () => {
    api.getDashboard.mockResolvedValue({ ...FULL, skill_gaps: { ...FULL.skill_gaps, closest_job: { ...FULL.skill_gaps.closest_job, missing_skills: ['Docker', 'AWS'] } } })
    renderDashboard()
    expect(await screen.findByRole('link', { name: /Closest opportunity/ })).toHaveTextContent('Only 2 skills stand in the way: Docker, AWS')
  })

  it('shows placement statistics computed from the data', async () => {
    renderDashboard()
    const w = widget('Placement statistics')
    expect(await w.findByText('Open jobs')).toBeInTheDocument()
    expect(w.getByText('Open jobs').nextSibling).toHaveTextContent('18')
    expect(w.getByText('Companies hiring').nextSibling).toHaveTextContent('9')
    expect(w.getByText('Closing this week').nextSibling).toHaveTextContent('4')
    const demand = within(w.getByRole('list', { name: 'Skills in demand' }))
    expect(demand.getByText('✓ you have')).toBeInTheDocument()
    expect(demand.getByText('missing')).toBeInTheDocument()
    expect(w.getByText(/you cleared/)).toHaveTextContent('50%')
  })

  it('shows different numbers for different data (nothing is hard-coded)', async () => {
    api.getDashboard.mockResolvedValue({ ...FULL, student: { ...FULL.student, first_name: 'Ravi' },
      profile: { ...FULL.profile, score: 33, missing: ['a', 'b', 'c'] },
      statistics: { ...FULL.statistics, open_jobs: 42, companies_hiring: 17 } })
    renderDashboard()
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('Ravi')
    expect(within(screen.getByRole('list', { name: 'Summary' })).getByText('33%')).toBeInTheDocument()
    expect(widget('Placement statistics').getByText('Open jobs').nextSibling).toHaveTextContent('42')
    expect(screen.queryByText('78%')).not.toBeInTheDocument()
  })
})

describe('quick actions', () => {
  it('offers every quick action with the right destination', async () => {
    renderDashboard()
    const actions = within(await screen.findByRole('region', { name: 'Quick actions' }))
    const expected = {
      'Complete Profile': '/student/profile', 'Upload Resume': '/student/resume', 'Find Jobs': '/student/jobs',
      'View Recommendations': '/student/recommendations', 'Check Skill Gaps': '/student/skill-gap', 'Open Chatbot': '/student/chat',
    }
    for (const [label, href] of Object.entries(expected)) expect(actions.getByRole('link', { name: new RegExp(label) })).toHaveAttribute('href', href)
    const prepare = actions.getByRole('link', { name: /Prepare for Interview/ }).getAttribute('href')
    expect(prepare).toBe('/student/chat?ask=How%20should%20I%20prepare%20for%20a%20technical%20interview%3F')
    expect(actions.getAllByRole('link')).toHaveLength(7)
  })

  it('highlights the action that matches the next step', async () => {
    renderDashboard()
    const actions = within(await screen.findByRole('region', { name: 'Quick actions' }))
    expect(actions.getByRole('link', { name: /Prepare for Interview/ }).className).toContain('border-indigo-400')
    expect(actions.getByRole('link', { name: /Find Jobs/ }).className).not.toContain('border-indigo-400')
  })

  it('navigates when an action is clicked', async () => {
    renderDashboard()
    await userEvent.click(await screen.findByRole('link', { name: /Find Jobs/ }))
    expect(await screen.findByText('other page')).toBeInTheDocument()
  })
})

describe('empty states for a new student', () => {
  beforeEach(() => api.getDashboard.mockResolvedValue(EMPTY))

  it('explains what to do in every widget', async () => {
    renderDashboard()
    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent('New')
    expect(screen.getByText('Complete your profile to personalise this page.')).toBeInTheDocument()
    expect(widget('Eligible opportunities').getByText(/No eligible jobs yet/)).toBeInTheDocument()
    expect(widget('Applications').getByText(/not applied to any job yet/)).toBeInTheDocument()
    expect(widget('Interviews').getByText(/No upcoming interviews/)).toBeInTheDocument()
    expect(widget('Resume').getByText(/No resume uploaded/)).toBeInTheDocument()
    expect(widget('Skill gaps').getByText(/Add your skills to your profile/)).toBeInTheDocument()
    expect(widget('Recommended for you').getByText('Improve these matches:')).toBeInTheDocument()
  })

  it('starts the progress at zero and recommends the profile first', async () => {
    renderDashboard()
    expect(await screen.findByRole('link', { name: 'Recommended next step' })).toHaveAttribute('href', '/student/profile')
    expect(widget('Your placement progress').getByText('0 of 6 milestones')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Complete Profile/ }).className).toContain('border-indigo-400')
  })

  it('has no pass-rate line and no funnel before there is anything to show', async () => {
    renderDashboard()
    await screen.findByRole('region', { name: 'Placement statistics' })
    expect(screen.queryByText(/you cleared/)).not.toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Applications by status' })).not.toBeInTheDocument()
  })

  it('handles a platform with no open jobs', async () => {
    api.getDashboard.mockResolvedValue({ ...EMPTY, recommendations: { open_jobs: 0, eligible: 0, incomplete_profile: 0, not_eligible: 0, hints: [], top: [] },
      statistics: { ...EMPTY.statistics, open_jobs: 0, companies_hiring: 0, in_demand_skills: [] } })
    renderDashboard()
    expect(await widget('Recommended for you').findByText(/no open jobs right now/)).toBeInTheDocument()
    expect(widget('Placement statistics').getByText('No open jobs to analyse.')).toBeInTheDocument()
  })

  it('says so when you have applied to every job you are eligible for', async () => {
    api.getDashboard.mockResolvedValue({ ...FULL, opportunities: { eligible_count: 2, eligible_percent: 11, items: [], closing_soon: [] } })
    renderDashboard()
    expect(await widget('Eligible opportunities').findByText(/already applied to all the jobs you are eligible for/)).toBeInTheDocument()
  })

  it('says so when no required skills are missing', async () => {
    api.getDashboard.mockResolvedValue({ ...FULL, skill_gaps: { student_has_skills: true, based_on_jobs: 10, top_missing: [], closest_job: null } })
    renderDashboard()
    expect(await widget('Skill gaps').findByText(/No required skills are missing across your 10 best-matching jobs/)).toBeInTheDocument()
  })
})

describe('date helpers', () => {
  const today = new Date(2026, 9, 5) // 5 Oct 2026
  it('counts calendar days and words deadlines', () => {
    expect(daysLeft('2026-10-05', today)).toBe(0)
    expect(daysLeft('2026-10-08', today)).toBe(3)
    expect(daysLeft('2026-10-01', today)).toBe(-4)
    expect(daysLeft(null, today)).toBeNull()
    expect(deadlineText('2026-10-05', today)).toBe('Closes today')
    expect(deadlineText('2026-10-06', today)).toBe('Closes tomorrow')
    expect(deadlineText('2026-10-12', today)).toBe('Closes in 7 days')
    expect(deadlineText('2026-10-01', today)).toBe('Deadline passed')
    expect(deadlineText(null, today)).toBe('No deadline')
  })
})

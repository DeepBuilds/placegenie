import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as jobsApi from '../api/jobs'
import * as profileApi from '../api/profile'
import Companies from '../pages/student/Companies'
import JobDetails from '../pages/student/JobDetails'
import Jobs from '../pages/student/Jobs'
import { formatBacklogs, formatCgpa, formatDeadline, formatExperience } from '../utils/jobs'

vi.mock('../api/jobs')
vi.mock('../api/profile')

const company = { id: 1, name: 'Helix Secure', industry: 'Cyber Security', location: 'Noida' }
const makeJob = (over = {}) => ({
  id: 7, title: 'Security Analyst', description: 'Monitor alerts.', location: 'Noida', job_type: 'full_time',
  min_cgpa: 7.5, max_backlogs: 0, min_experience_months: 0, deadline: '2030-01-15', is_expired: false,
  status: 'open', company, role: { id: 3, name: 'Cyber Security Analyst' },
  skills: [
    { skill_id: 1, name: 'Linux', category: 'Tools', importance: 'required', weight: 3 },
    { skill_id: 2, name: 'Python', category: 'Programming', importance: 'preferred', weight: 1 },
  ],
  allowed_branches: [{ id: 1, name: 'Computer Science and Engineering' }],
  required_certifications: ['CompTIA Security+'], created_at: '2026-01-01T00:00:00',
  ...over,
})
const page = (items, total = items.length) => ({ items, total, limit: 12, offset: 0 })

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/student/jobs" element={<Jobs />} />
        <Route path="/student/jobs/:id" element={<JobDetails />} />
        <Route path="/student/companies" element={<Companies />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  jobsApi.getJobs.mockResolvedValue(page([makeJob()]))
  jobsApi.getCompanies.mockResolvedValue({ items: [{ ...company, website: null, description: 'Security firm.', open_jobs: 2 }], total: 1, limit: 100, offset: 0 })
  jobsApi.getJob.mockResolvedValue(makeJob())
  jobsApi.getCompany.mockResolvedValue({ ...company, website: 'https://helix.example.com', description: 'We protect things.', open_jobs: 2 })
  profileApi.getBranches.mockResolvedValue([{ id: 1, name: 'Computer Science and Engineering' }])
  profileApi.getSkills.mockResolvedValue([{ id: 2, name: 'Python', category: 'Programming' }])
  profileApi.getJobRoles.mockResolvedValue([{ id: 3, name: 'Cyber Security Analyst', category: 'Security' }])
})

describe('jobs page', () => {
  it('shows job cards with company, requirements and skills', async () => {
    renderAt('/student/jobs')
    expect(await screen.findByRole('link', { name: 'Security Analyst' })).toHaveAttribute('href', '/student/jobs/7')
    expect(screen.getByText('1 job found')).toBeInTheDocument()
    expect(screen.getByText('7.50 or above')).toBeInTheDocument()
    expect(screen.getByText('No backlogs allowed')).toBeInTheDocument()
    expect(screen.getByText('Linux')).toBeInTheDocument()
  })

  it('reads filters from the URL and sends them to the API', async () => {
    renderAt('/student/jobs?company_id=1&job_type=internship')
    await screen.findByText(/job found/)
    expect(jobsApi.getJobs).toHaveBeenCalledWith(expect.objectContaining({ company_id: '1', job_type: 'internship', limit: 12 }))
    expect(await screen.findByText(/Showing jobs at/)).toHaveTextContent('Helix Secure')
  })

  it('applies a dropdown filter and can clear all filters', async () => {
    renderAt('/student/jobs')
    await screen.findByText(/job found/)
    await userEvent.selectOptions(screen.getByLabelText('Job type'), 'internship')
    await waitFor(() =>
      expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ job_type: 'internship' })),
    )
    await userEvent.click(await screen.findByRole('button', { name: 'Clear all filters' }))
    await waitFor(() => expect(jobsApi.getJobs.mock.lastCall[0].job_type).toBeUndefined())
  })

  it('searches after a short pause', async () => {
    renderAt('/student/jobs')
    await screen.findByText(/job found/)
    await userEvent.type(screen.getByLabelText('Search'), 'python')
    await waitFor(() => expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'python' })))
  })

  it('shows an empty state', async () => {
    jobsApi.getJobs.mockResolvedValue(page([], 0))
    renderAt('/student/jobs')
    expect(await screen.findByText(/No jobs match your search/)).toBeInTheDocument()
  })

  it('shows an error message when loading fails', async () => {
    jobsApi.getJobs.mockRejectedValue({ response: { status: 500, data: {} } })
    renderAt('/student/jobs')
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })

  it('paginates when there are more than one page of results', async () => {
    jobsApi.getJobs.mockResolvedValue(page([makeJob()], 30))
    renderAt('/student/jobs')
    expect(await screen.findByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Previous' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await waitFor(() => expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ offset: '12' })))
  })
})

describe('job details page', () => {
  it('shows eligibility requirements, skills and company info', async () => {
    renderAt('/student/jobs/7')
    expect(await screen.findByRole('heading', { name: 'Security Analyst' })).toBeInTheDocument()
    expect(screen.getByText('CompTIA Security+')).toBeInTheDocument()
    expect(screen.getByText('Computer Science and Engineering')).toBeInTheDocument()
    expect(screen.getByText('Required')).toBeInTheDocument()
    expect(screen.getByText('Nice to have')).toBeInTheDocument()
    expect(await screen.findByText('We protect things.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /See all jobs at Helix Secure \(2\)/ })).toBeInTheDocument()
  })

  it('says "All branches" and "None" when there are no restrictions', async () => {
    jobsApi.getJob.mockResolvedValue(makeJob({ allowed_branches: [], required_certifications: [], max_backlogs: null, min_cgpa: 0 }))
    renderAt('/student/jobs/7')
    expect(await screen.findByText('All branches')).toBeInTheDocument()
    expect(screen.getByText('None')).toBeInTheDocument()
    expect(screen.getByText('No limit')).toBeInTheDocument()
    expect(screen.getByText('No minimum')).toBeInTheDocument()
  })

  it('still renders when the company request fails', async () => {
    jobsApi.getCompany.mockRejectedValue(new Error('boom'))
    renderAt('/student/jobs/7')
    expect(await screen.findByRole('heading', { name: 'Security Analyst' })).toBeInTheDocument()
    expect(screen.getByText(/About Helix Secure/)).toBeInTheDocument()
  })

  it('shows a friendly message for a missing or closed job', async () => {
    jobsApi.getJob.mockRejectedValue({ response: { status: 404, data: { detail: 'Job not found.' } } })
    renderAt('/student/jobs/99')
    expect(await screen.findByRole('alert')).toHaveTextContent(/does not exist or is no longer open/)
    expect(screen.getByRole('link', { name: /Back to jobs/ })).toBeInTheDocument()
  })

  it('flags an expired deadline', async () => {
    jobsApi.getJob.mockResolvedValue(makeJob({ is_expired: true, deadline: '2020-01-15' }))
    renderAt('/student/jobs/7')
    expect(await screen.findByText(/Closed on/)).toBeInTheDocument()
  })
})

describe('companies page', () => {
  it('lists companies with open job counts linking to filtered jobs', async () => {
    renderAt('/student/companies')
    expect(await screen.findByRole('heading', { name: 'Helix Secure' })).toBeInTheDocument()
    expect(screen.getByText('Cyber Security · Noida')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /2 open jobs/ })).toHaveAttribute('href', '/student/jobs?company_id=1')
  })

  it('searches companies', async () => {
    renderAt('/student/companies')
    await screen.findByRole('heading', { name: 'Helix Secure' })
    await userEvent.type(screen.getByLabelText('Search companies'), 'cyber')
    await waitFor(() => expect(jobsApi.getCompanies).toHaveBeenLastCalledWith({ q: 'cyber', limit: 100 }))
  })

  it('shows an empty state', async () => {
    jobsApi.getCompanies.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    renderAt('/student/companies')
    expect(await screen.findByText(/No companies match/)).toBeInTheDocument()
  })
})

describe('format helpers', () => {
  it('formats requirements readably', () => {
    expect(formatCgpa(0)).toBe('No minimum')
    expect(formatCgpa(7)).toBe('7.00 or above')
    expect(formatBacklogs(null)).toBe('No limit')
    expect(formatBacklogs(0)).toBe('No backlogs allowed')
    expect(formatBacklogs(2)).toBe('Up to 2')
    expect(formatExperience(0)).toBe('Freshers welcome')
    expect(formatExperience(6)).toBe('6 months experience')
    expect(formatDeadline(null, false)).toBe('No deadline')
    expect(formatDeadline('2030-01-15', false)).toMatch(/^Apply by/)
    expect(formatDeadline('2020-01-15', true)).toMatch(/^Closed on/)
  })
})

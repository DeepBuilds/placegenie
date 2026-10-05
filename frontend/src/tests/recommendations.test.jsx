import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as profileApi from '../api/profile'
import * as recApi from '../api/recommendations'
import Recommendations from '../pages/student/Recommendations'

vi.mock('../api/recommendations')
vi.mock('../api/profile')

const breakdown = [
  { key: 'skills', label: 'Skill match', available: true, weight: 0.75, score: 0.8, points: 60, note: '2/3 skills matched (2/2 required)' },
  { key: 'academic', label: 'Academic fit', available: true, weight: 0.25, score: 0.9, points: 22.5, note: 'CGPA 8.50 vs minimum 7.00' },
  { key: 'role', label: 'Preferred role', available: false, weight: 0, score: 0, points: 0, note: 'Choose preferred job roles in your profile.' },
]

const makeRec = (over = {}) => ({
  job: {
    id: 3, title: 'Data Analyst', location: 'Bengaluru', job_type: 'full_time', deadline: '2030-01-15', is_expired: false,
    company: { id: 2, name: 'Aurora Analytics', industry: 'Data', location: 'Bengaluru' },
  },
  match_score: 82,
  eligibility: { result: 'ELIGIBLE', eligible: true, multiplier: 1, failed_requirements: [], incomplete_fields: [] },
  matched_skills: ['Python', 'SQL'], missing_skills: [], missing_preferred_skills: ['Power BI'],
  reasons: ['You are eligible: you meet every listed requirement.', 'Skill match: 2/3 skills matched (2/2 required): Python, SQL.'],
  concerns: [], breakdown,
  ...over,
})

const page = (items, extra = {}) => ({
  items, total: items.length, limit: 10, offset: 0,
  counts: { eligible: items.length, incomplete_profile: 0, not_eligible: 0 }, profile_hints: [], ...extra,
})

function renderAt(path = '/student/recommendations') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/student/recommendations" element={<Recommendations />} />
        <Route path="/student/jobs/:id" element={<p>job details page</p>} />
        <Route path="/student/profile" element={<p>profile page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  recApi.getRecommendations.mockResolvedValue(page([makeRec()]))
  profileApi.getJobRoles.mockResolvedValue([{ id: 5, name: 'Data Analyst', category: 'Data' }])
})

describe('recommendations page', () => {
  it('shows match %, eligibility, skills, reasons and the company', async () => {
    renderAt()
    expect(await screen.findByRole('link', { name: 'Data Analyst' })).toHaveAttribute('href', '/student/jobs/3')
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(screen.getByText('✓ Eligible')).toBeInTheDocument()
    expect(screen.getByText(/Aurora Analytics/)).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Matched skills' })).getByText('Python')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Nice-to-have skills you lack' })).getByText('Power BI')).toBeInTheDocument()
    expect(screen.getByText('Why recommended')).toBeInTheDocument()
    expect(screen.getByText(/Skill match: 2\/3 skills matched/)).toBeInTheDocument()
    expect(screen.queryByText('What holds it back')).not.toBeInTheDocument()
  })

  it('shows missing required skills and what holds a not-eligible job back', async () => {
    recApi.getRecommendations.mockResolvedValue(page([makeRec({
      match_score: 31,
      eligibility: { result: 'NOT_ELIGIBLE', eligible: false, multiplier: 0.5, failed_requirements: ['CGPA'], incomplete_fields: [] },
      matched_skills: ['Python'], missing_skills: ['Statistics'],
      concerns: ['Not eligible yet: 1 requirement(s) not met (CGPA). Score reduced by 50%.'],
    })], { counts: { eligible: 0, incomplete_profile: 0, not_eligible: 1 } }))
    renderAt()
    expect(await screen.findByText('✗ Not eligible')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Missing required skills' })).getByText('Statistics')).toBeInTheDocument()
    expect(screen.getByText('What holds it back')).toBeInTheDocument()
    expect(screen.getByText(/Score reduced by 50%/)).toBeInTheDocument()
    expect(screen.getByText('31%')).toBeInTheDocument()
  })

  it('explains how the score is calculated, including unused factors', async () => {
    renderAt()
    await screen.findByText('82%')
    const details = screen.getByText('How this score was calculated').closest('details')
    expect(within(details).getByText('Skill match')).toBeInTheDocument()
    expect(within(details).getByText('75%')).toBeInTheDocument()
    expect(within(details).getByText('not used')).toBeInTheDocument()
    expect(within(details).getByText(/Eligibility adjustment \(×1\)/)).toBeInTheDocument()
  })

  it('shows profile hints for an empty profile and links to the profile', async () => {
    recApi.getRecommendations.mockResolvedValue(page([makeRec({ match_score: 0, matched_skills: [] })], {
      profile_hints: ['Add your skills: skill match is the biggest part of the score.'],
    }))
    renderAt()
    expect(await screen.findByText('Improve your recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Add your skills/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: /Update my profile/ }))
    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })

  it('shows an empty state with and without filters', async () => {
    recApi.getRecommendations.mockResolvedValue(page([]))
    renderAt()
    expect(await screen.findByText(/no open jobs to recommend/i)).toBeInTheDocument()
    renderAt('/student/recommendations?location=Antarctica')
    expect(await screen.findByText(/No jobs match these filters/)).toBeInTheDocument()
  })

  it('shows an error message when loading fails', async () => {
    recApi.getRecommendations.mockRejectedValue({ response: { status: 500, data: {} } })
    renderAt()
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })

  it('sends the filters from the URL and from the controls to the API', async () => {
    renderAt('/student/recommendations?role_id=5')
    await screen.findByText('82%')
    expect(recApi.getRecommendations).toHaveBeenCalledWith(expect.objectContaining({ role_id: '5', limit: 10 }))

    await userEvent.click(screen.getByLabelText(/Only jobs I.m eligible for/))
    await waitFor(() =>
      expect(recApi.getRecommendations).toHaveBeenLastCalledWith(expect.objectContaining({ eligible_only: 'true', role_id: '5' })),
    )
    await userEvent.selectOptions(screen.getByLabelText('Sort by'), 'deadline')
    await waitFor(() =>
      expect(recApi.getRecommendations).toHaveBeenLastCalledWith(expect.objectContaining({ sort: 'deadline', eligible_only: 'true' })),
    )
    await userEvent.type(screen.getByLabelText('Location'), 'Pune')
    await waitFor(() => expect(recApi.getRecommendations).toHaveBeenLastCalledWith(expect.objectContaining({ location: 'Pune' })))
  })

  it('clears all filters', async () => {
    renderAt('/student/recommendations?role_id=5&eligible_only=true')
    await screen.findByText('82%')
    await userEvent.click(screen.getByRole('button', { name: 'Clear all filters' }))
    await waitFor(() => {
      const last = recApi.getRecommendations.mock.lastCall[0]
      expect(last.role_id).toBeUndefined()
      expect(last.eligible_only).toBeUndefined()
    })
  })

  it('shows eligibility counts and paginates', async () => {
    recApi.getRecommendations.mockResolvedValue(page([makeRec()], {
      total: 25, counts: { eligible: 9, incomplete_profile: 3, not_eligible: 13 },
    }))
    renderAt()
    expect(await screen.findByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByText('9 eligible')).toBeInTheDocument()
    expect(screen.getByText('13 not eligible')).toBeInTheDocument()
    expect(screen.getByText('3 need a fuller profile')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await waitFor(() => expect(recApi.getRecommendations).toHaveBeenLastCalledWith(expect.objectContaining({ offset: '10' })))
  })

  it('clicking a recommendation opens its job details', async () => {
    renderAt()
    await userEvent.click(await screen.findByRole('link', { name: /View details/ }))
    expect(await screen.findByText('job details page')).toBeInTheDocument()
  })
})

import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as jobsApi from '../api/jobs'
import EligibilityChecker from '../components/jobs/EligibilityChecker'

vi.mock('../api/jobs')

const crit = (key, label, status, required, actual, message) => ({ key, label, status, required, actual, message })

const base = {
  job: { id: 7, title: 'Security Analyst', company: 'Helix Secure' },
  failed_requirements: [], reasons: [], missing_skills: [], missing_preferred_skills: [],
  missing_certifications: [], incomplete_fields: [],
}

const eligible = {
  ...base, result: 'ELIGIBLE', eligible: true, summary: 'You meet all the listed requirements for this job.',
  criteria: [
    crit('cgpa', 'CGPA', 'passed', '7.50 or above', '8.10', 'Your CGPA (8.10) meets the minimum of 7.50.'),
    crit('branch', 'Branch', 'passed', 'CSE', 'CSE', 'Your branch (CSE) is allowed.'),
    crit('backlogs', 'Backlogs', 'passed', 'At most 2', '0', 'Your backlogs (0) are within the limit.'),
  ],
  missing_preferred_skills: ['Docker'],
}

const notEligible = {
  ...base, result: 'NOT_ELIGIBLE', eligible: false, summary: 'You are not eligible: 2 requirements not met.',
  criteria: [
    crit('cgpa', 'CGPA', 'failed', '7.50 or above', '6.90', 'Your CGPA (6.90) is below the required 7.50.'),
    crit('skills', 'Required skills', 'failed', 'All 2 required skills', '1/2 matched', 'Missing required skill(s): SQL.'),
    crit('branch', 'Branch', 'passed', 'CSE', 'CSE', 'Your branch (CSE) is allowed.'),
  ],
  failed_requirements: ['CGPA', 'Required skills'],
  reasons: ['Your CGPA (6.90) is below the required 7.50.', 'Missing required skill(s): SQL.'],
  missing_skills: ['SQL'],
}

const incomplete = {
  ...base, result: 'INCOMPLETE_PROFILE', eligible: false,
  summary: 'Eligibility could not be fully checked because your profile is incomplete.',
  criteria: [crit('cgpa', 'CGPA', 'not_evaluated', '7.50 or above', 'Not entered', 'Add your CGPA to your profile so this can be checked.')],
  reasons: ['Add your CGPA to your profile so this can be checked.'], incomplete_fields: ['CGPA'],
}

const renderChecker = () =>
  render(
    <MemoryRouter>
      <EligibilityChecker jobId={7} />
    </MemoryRouter>,
  )

beforeEach(() => vi.resetAllMocks())

describe('eligibility checker', () => {
  it('does nothing until the button is pressed', () => {
    renderChecker()
    expect(screen.getByRole('button', { name: 'Check Eligibility' })).toBeInTheDocument()
    expect(jobsApi.checkEligibility).not.toHaveBeenCalled()
  })

  it('shows ELIGIBLE with passed criteria and required vs actual values', async () => {
    jobsApi.checkEligibility.mockResolvedValue(eligible)
    renderChecker()
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByText('✓ ELIGIBLE')).toBeInTheDocument()
    expect(jobsApi.checkEligibility).toHaveBeenCalledWith(7)
    const list = screen.getByRole('list', { name: 'Eligibility criteria' })
    expect(within(list).getAllByText(/Passed/)).toHaveLength(3)
    expect(within(list).getByText('8.10')).toBeInTheDocument()
    expect(within(list).getAllByText('7.50 or above')[0]).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.queryByText(/Why you are not eligible/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Check again' })).toBeInTheDocument()
  })

  it('shows NOT ELIGIBLE with the failing reasons and missing skills', async () => {
    jobsApi.checkEligibility.mockResolvedValue(notEligible)
    renderChecker()
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByText('✗ NOT ELIGIBLE')).toBeInTheDocument()
    expect(screen.getByText('Why you are not eligible')).toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'Eligibility criteria' })
    expect(within(list).getAllByText(/Failed/)).toHaveLength(2)
    expect(within(list).getAllByText(/Passed/)).toHaveLength(1)
    expect(within(list).getByText('Your CGPA (6.90) is below the required 7.50.')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Missing required skills' })).getByText('SQL')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Update your profile' })).toHaveAttribute('href', '/student/profile')
  })

  it('explains an incomplete profile instead of claiming a result', async () => {
    jobsApi.checkEligibility.mockResolvedValue(incomplete)
    renderChecker()
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByText('! CANNOT FULLY CHECK')).toBeInTheDocument()
    expect(screen.getByText('What is missing')).toBeInTheDocument()
    expect(screen.getByText(/Not checked/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Update profile →' })).toBeInTheDocument()
    expect(screen.queryByText('✓ ELIGIBLE')).not.toBeInTheDocument()
  })

  it('shows an error and allows retrying', async () => {
    jobsApi.checkEligibility.mockRejectedValueOnce({ response: { status: 404, data: { detail: 'Job not found.' } } })
    jobsApi.checkEligibility.mockResolvedValueOnce(eligible)
    renderChecker()
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Job not found.')
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByText('✓ ELIGIBLE')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('includes the guidance disclaimer', async () => {
    jobsApi.checkEligibility.mockResolvedValue(eligible)
    renderChecker()
    await userEvent.click(screen.getByRole('button', { name: 'Check Eligibility' }))
    expect(await screen.findByText(/final decision/)).toBeInTheDocument()
  })
})

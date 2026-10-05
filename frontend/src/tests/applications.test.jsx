import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/applications'
import * as jobsApi from '../api/jobs'
import ApplyPanel from '../components/applications/ApplyPanel'
import { StatusTracker } from '../components/applications/StatusParts'
import ApplicationDetails from '../pages/student/ApplicationDetails'
import Applications from '../pages/student/Applications'
import InterviewDetails from '../pages/student/InterviewDetails'
import Interviews from '../pages/student/Interviews'
import { toInputValue, validateInterview } from '../utils/applications'

vi.mock('../api/applications')
vi.mock('../api/jobs')

const job = { id: 3, title: 'Data Analyst', company: 'Aurora Analytics', location: 'Bengaluru', job_type: 'full_time', deadline: '2030-01-01', is_expired: false }
const student = { id: 1, full_name: 'Asha Patil', email: 'asha@example.com', branch: null, cgpa: 8.1 }
const summary = (over = {}) => ({
  id: 10, status: 'applied', applied_at: '2026-10-01T10:00:00', updated_at: '2026-10-01T10:00:00', job, student,
  interview_count: 0, next_interview: null, can_withdraw: true, ...over,
})
const eligibility = { result: 'ELIGIBLE', eligible: true, summary: 'You meet all the listed requirements for this job.', failed_requirements: [], incomplete_fields: [], criteria: [] }
const interview = (over = {}) => ({
  id: 7, application_id: 10, stage: 'technical_interview', scheduled_at: '2030-05-20T14:30:00', outcome: 'pending', notes: 'Bring laptop',
  is_upcoming: true, needs_result: false, created_at: '2026-10-01T10:00:00', updated_at: '2026-10-01T10:00:00', ...over,
})
const detail = (over = {}) => ({ ...summary(), interviews: [], eligibility_now: eligibility, ...over })
const listItem = (over = {}) => ({ ...interview(), application: { id: 10, status: 'applied', job }, student, ...over })

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/student/applications" element={<Applications />} />
        <Route path="/student/applications/:id" element={<ApplicationDetails />} />
        <Route path="/student/interviews" element={<Interviews />} />
        <Route path="/student/interviews/:id" element={<InterviewDetails />} />
        <Route path="/student/jobs" element={<p>jobs page</p>} />
        <Route path="/student/profile" element={<p>profile page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  api.getMyApplications.mockResolvedValue({ items: [], total: 0, limit: 0, offset: 0, counts: {} })
  api.getMyInterviews.mockResolvedValue({ items: [], total: 0, counts: { upcoming: 0, past: 0, unscheduled: 0, needs_result: 0 } })
})

// ---------------------------------------------------------------- helpers
describe('helpers', () => {
  it('converts server times to datetime-local values and validates interview input', () => {
    expect(toInputValue('2030-05-20T14:30:00')).toBe('2030-05-20T14:30')
    expect(toInputValue(null)).toBe('')
    expect(validateInterview({ scheduled_at: '', notes: '' })).toEqual({})
    expect(validateInterview({ scheduled_at: '1850-01-01T10:00' }).scheduled_at).toMatch(/2000 and 2100/)
    expect(validateInterview({ scheduled_at: '', notes: 'x'.repeat(2001) }).notes).toMatch(/2000/)
  })
})

describe('status tracker', () => {
  it('marks completed steps and the current one', () => {
    render(<StatusTracker status="technical_interview" />)
    const steps = within(screen.getByRole('list', { name: 'Application progress' })).getAllByRole('listitem')
    expect(steps).toHaveLength(6)
    expect(steps[0]).toHaveTextContent('✓Applied')
    expect(steps[3]).toHaveAttribute('aria-current', 'step')
    expect(steps[3]).toHaveTextContent('Technical interview')
    expect(steps[5]).toHaveTextContent('○Selected')
  })

  it('shows a banner instead of steps for rejected and withdrawn applications', () => {
    const { unmount } = render(<StatusTracker status="rejected" />)
    expect(screen.getByRole('status')).toHaveTextContent(/not taken forward/)
    unmount()
    render(<StatusTracker status="withdrawn" />)
    expect(screen.getByRole('status')).toHaveTextContent(/You withdrew this application/)
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------- apply
describe('apply panel', () => {
  const renderApply = (props = {}) =>
    render(<MemoryRouter><ApplyPanel jobId={3} isExpired={false} {...props} /></MemoryRouter>)

  it('applies straight away when the student is eligible', async () => {
    jobsApi.checkEligibility.mockResolvedValue({ eligible: true, reasons: [] })
    api.applyToJob.mockResolvedValue(summary())
    renderApply()
    await userEvent.click(await screen.findByRole('button', { name: 'Apply for this job' }))
    expect(await screen.findByText('✓ You applied')).toBeInTheDocument()
    expect(api.applyToJob).toHaveBeenCalledWith(3)
    expect(screen.getByText('Applied')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View application/ })).toHaveAttribute('href', '/student/applications/10')
  })

  it('warns an ineligible student first and lets them apply anyway', async () => {
    jobsApi.checkEligibility.mockResolvedValue({ eligible: false, reasons: ['Your CGPA (6.90) is below the required 7.50.'] })
    api.applyToJob.mockResolvedValue(summary())
    renderApply()
    await userEvent.click(await screen.findByRole('button', { name: 'Apply for this job' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Your CGPA (6.90) is below the required 7.50.')
    expect(api.applyToJob).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Apply anyway' }))
    expect(await screen.findByText('✓ You applied')).toBeInTheDocument()
  })

  it('lets the student cancel after the warning', async () => {
    jobsApi.checkEligibility.mockResolvedValue({ eligible: false, reasons: ['x'] })
    renderApply()
    await userEvent.click(await screen.findByRole('button', { name: 'Apply for this job' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Cancel' }))
    expect(api.applyToJob).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Apply for this job' })).toBeInTheDocument()
  })

  it('shows the status instead of a button when already applied', async () => {
    api.getMyApplications.mockResolvedValue({ items: [summary({ status: 'shortlisted' })], total: 1, counts: {} })
    renderApply()
    expect(await screen.findByText('✓ You applied')).toBeInTheDocument()
    expect(screen.getByText('Shortlisted')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Apply/ })).not.toBeInTheDocument()
  })

  it('offers to apply again after a withdrawal', async () => {
    api.getMyApplications.mockResolvedValue({ items: [summary({ status: 'withdrawn' })], total: 1, counts: {} })
    renderApply()
    expect(await screen.findByText(/You withdrew your earlier application/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Apply again' })).toBeInTheDocument()
  })

  it('shows the server message for a duplicate or other failure', async () => {
    jobsApi.checkEligibility.mockResolvedValue({ eligible: true, reasons: [] })
    api.applyToJob.mockRejectedValue({ response: { status: 409, data: { detail: 'You have already applied to this job.' } } })
    renderApply()
    await userEvent.click(await screen.findByRole('button', { name: 'Apply for this job' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('You have already applied to this job.')
  })

  it('does not offer applying after the deadline', async () => {
    renderApply({ isExpired: true })
    expect(await screen.findByText(/deadline for this job has passed/)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------- applications list
describe('applications page', () => {
  it('lists applications with status badges, next interview and status filters with counts', async () => {
    api.getMyApplications.mockResolvedValue({
      items: [summary({ next_interview: '2030-05-20T14:30:00', interview_count: 1, status: 'technical_interview' }), summary({ id: 11, status: 'applied', job: { ...job, title: 'Security Analyst' } })],
      total: 2, counts: { technical_interview: 1, applied: 1 },
    })
    renderAt('/student/applications')
    const list = await screen.findByRole('list', { name: 'Applications' })
    expect(within(list).getByRole('link', { name: 'Data Analyst' })).toHaveAttribute('href', '/student/applications/10')
    expect(within(list).getByText('Technical interview')).toBeInTheDocument()
    expect(within(list).getByText(/Next interview:/)).toBeInTheDocument()
    expect(within(list).getByText('No interviews recorded')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'All (2)' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Applied (1)' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Rejected/ })).not.toBeInTheDocument() // no applications in that state
  })

  it('filters by status through the API', async () => {
    api.getMyApplications.mockResolvedValue({ items: [summary()], total: 1, counts: { applied: 1 } })
    renderAt('/student/applications')
    await userEvent.click(await screen.findByRole('button', { name: 'Applied (1)' }))
    await waitFor(() => expect(api.getMyApplications).toHaveBeenLastCalledWith({ status: 'applied' }))
  })

  it('invites the first application when there are none', async () => {
    renderAt('/student/applications')
    expect(await screen.findByText(/not applied to any job yet/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: /Browse jobs/ }))
    expect(await screen.findByText('jobs page')).toBeInTheDocument()
  })

  it('shows an error message when loading fails', async () => {
    api.getMyApplications.mockRejectedValue({ response: { status: 500, data: {} } })
    renderAt('/student/applications')
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })
})

// ---------------------------------------------------------------- application details
describe('application details page', () => {
  it('shows the job, progress tracker, eligibility and interviews', async () => {
    api.getApplication.mockResolvedValue(detail({ status: 'hr_interview', interviews: [interview()] }))
    renderAt('/student/applications/10')
    expect(await screen.findByRole('heading', { name: 'Data Analyst' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Application progress' })).toBeInTheDocument()
    expect(screen.getByText(/You meet all the listed requirements/)).toBeInTheDocument()
    const ivs = within(screen.getByRole('list', { name: 'Interviews' }))
    expect(ivs.getByRole('link', { name: 'Technical interview' })).toHaveAttribute('href', '/student/interviews/7')
    expect(ivs.getByText('Bring laptop')).toBeInTheDocument()
    expect(ivs.getByText('Upcoming')).toBeInTheDocument()
  })

  it('withdraws only after confirmation', async () => {
    api.getApplication.mockResolvedValueOnce(detail()).mockResolvedValue(detail({ status: 'withdrawn', can_withdraw: false }))
    api.withdrawApplication.mockResolvedValue({})
    const confirm = vi.spyOn(window, 'confirm')
    renderAt('/student/applications/10')
    const button = await screen.findByRole('button', { name: 'Withdraw application' })
    confirm.mockReturnValueOnce(false)
    await userEvent.click(button)
    expect(api.withdrawApplication).not.toHaveBeenCalled()
    confirm.mockReturnValueOnce(true)
    await userEvent.click(button)
    await waitFor(() => expect(api.withdrawApplication).toHaveBeenCalledWith(10))
    expect(await screen.findByText('Application withdrawn.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Withdraw application' })).not.toBeInTheDocument()
    expect(screen.getByText(/Interviews cannot be added to a withdrawn application/)).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('hides the withdraw button once a final decision is made', async () => {
    api.getApplication.mockResolvedValue(detail({ status: 'selected', can_withdraw: false }))
    renderAt('/student/applications/10')
    await screen.findByRole('heading', { name: 'Data Analyst' })
    expect(screen.queryByRole('button', { name: 'Withdraw application' })).not.toBeInTheDocument()
  })

  it('explains an ineligible application using the live eligibility', async () => {
    api.getApplication.mockResolvedValue(detail({ eligibility_now: { ...eligibility, result: 'NOT_ELIGIBLE', eligible: false, summary: 'You are not eligible: 1 requirement not met.', failed_requirements: ['CGPA'] } }))
    renderAt('/student/applications/10')
    expect(await screen.findByText(/You are not eligible/)).toBeInTheDocument()
    expect(screen.getByText('Not met: CGPA.')).toBeInTheDocument()
  })

  it('adds an interview from the application page', async () => {
    api.getApplication.mockResolvedValueOnce(detail()).mockResolvedValue(detail({ interview_count: 1, interviews: [interview()] }))
    api.addInterview.mockResolvedValue(interview())
    renderAt('/student/applications/10')
    await userEvent.click(await screen.findByRole('button', { name: '+ Add interview' }))
    await userEvent.selectOptions(screen.getByLabelText('Stage'), 'hr_interview')
    await userEvent.type(screen.getByLabelText('Date and time'), '2030-05-20T14:30')
    await userEvent.type(screen.getByLabelText('Notes'), 'Panel of two')
    await userEvent.click(screen.getByRole('button', { name: 'Add interview' }))
    await waitFor(() => expect(api.addInterview).toHaveBeenCalledWith(10, { stage: 'hr_interview', scheduled_at: '2030-05-20T14:30', outcome: 'pending', notes: 'Panel of two' }))
    expect(await screen.findByText('Interview added.')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Interviews' })).getByText('Technical interview')).toBeInTheDocument()
  })

  it('updates an interview result straight from the list', async () => {
    api.getApplication.mockResolvedValueOnce(detail({ interviews: [interview()] })).mockResolvedValue(detail({ interviews: [interview({ outcome: 'passed' })] }))
    api.updateInterview.mockResolvedValue({})
    renderAt('/student/applications/10')
    await userEvent.selectOptions(await screen.findByLabelText('Result'), 'passed')
    await waitFor(() => expect(api.updateInterview).toHaveBeenCalledWith(7, { outcome: 'passed' }))
    expect(await screen.findByText('Interview updated.')).toBeInTheDocument()
  })

  it('shows the server error when adding fails', async () => {
    api.getApplication.mockResolvedValue(detail())
    api.addInterview.mockRejectedValue({ response: { status: 409, data: { detail: 'This application was withdrawn, so interviews cannot be added.' } } })
    renderAt('/student/applications/10')
    await userEvent.click(await screen.findByRole('button', { name: '+ Add interview' }))
    await userEvent.click(screen.getByRole('button', { name: 'Add interview' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('interviews cannot be added')
  })

  it('shows a friendly message for an unknown application', async () => {
    api.getApplication.mockRejectedValue({ response: { status: 404, data: { detail: 'Application not found.' } } })
    renderAt('/student/applications/99')
    expect(await screen.findByRole('alert')).toHaveTextContent('This application does not exist.')
  })
})

// ---------------------------------------------------------------- interview tracker
describe('interview tracker', () => {
  const upcoming = listItem({ id: 1, stage: 'hr_interview', is_upcoming: true })
  const past = listItem({ id: 2, stage: 'online_assessment', scheduled_at: '2020-01-10T10:00:00', is_upcoming: false, needs_result: true })
  const tbd = listItem({ id: 3, stage: 'other', scheduled_at: null, is_upcoming: false })
  const all = { items: [upcoming, past, tbd], total: 3, counts: { upcoming: 1, past: 1, unscheduled: 1, needs_result: 1 } }

  it('shows upcoming interviews first, with tab counts', async () => {
    api.getMyInterviews.mockResolvedValue(all)
    renderAt('/student/interviews')
    const list = await screen.findByRole('list', { name: 'upcoming interviews' })
    expect(within(list).getByRole('link', { name: 'HR interview' })).toHaveAttribute('href', '/student/interviews/1')
    expect(within(list).getByText(/Data Analyst/)).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Upcoming (1)' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Past (1)' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'No date yet (1)' })).toBeInTheDocument()
  })

  it('switches to past interviews and flags the ones missing a result', async () => {
    api.getMyInterviews.mockResolvedValue(all)
    renderAt('/student/interviews')
    expect(await screen.findByRole('status')).toHaveTextContent('1 past interview has no result yet')
    await userEvent.click(screen.getByRole('tab', { name: 'Past (1)' }))
    const list = await screen.findByRole('list', { name: 'past interviews' })
    expect(within(list).getByText('Online assessment')).toBeInTheDocument()
    expect(within(list).getByText('Add the result')).toBeInTheDocument()
  })

  it('shows interviews that have no date yet', async () => {
    api.getMyInterviews.mockResolvedValue(all)
    renderAt('/student/interviews')
    await userEvent.click(await screen.findByRole('tab', { name: 'No date yet (1)' }))
    expect(within(await screen.findByRole('list', { name: 'unscheduled interviews' })).getByText('Other round')).toBeInTheDocument()
  })

  it('shows an empty state per tab', async () => {
    renderAt('/student/interviews?tab=past')
    expect(await screen.findByText('No past interviews.')).toBeInTheDocument()
  })

  it('records an interview for one of the applications', async () => {
    api.getMyInterviews.mockResolvedValue(all)
    api.getMyApplications.mockResolvedValue({ items: [summary()], total: 1, counts: {} })
    api.addInterview.mockResolvedValue(interview())
    renderAt('/student/interviews')
    await userEvent.click(await screen.findByRole('button', { name: '+ Record interview' }))
    await userEvent.selectOptions(screen.getByLabelText('Application'), '10')
    await userEvent.selectOptions(screen.getByLabelText('Stage'), 'online_assessment')
    await userEvent.type(screen.getByLabelText('Date and time'), '2030-06-01T09:00')
    await userEvent.click(screen.getByRole('button', { name: 'Add interview' }))
    await waitFor(() => expect(api.addInterview).toHaveBeenCalledWith(10, { stage: 'online_assessment', scheduled_at: '2030-06-01T09:00', outcome: 'pending', notes: null }))
  })

  it('needs an application before an interview can be recorded', async () => {
    renderAt('/student/interviews')
    expect(await screen.findByText(/You need an application before you can record an interview/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '+ Record interview' })).not.toBeInTheDocument()
  })

  it('shows an error when loading fails', async () => {
    api.getMyInterviews.mockRejectedValue({ response: { status: 500, data: {} } })
    renderAt('/student/interviews')
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })
})

// ---------------------------------------------------------------- interview details
describe('interview details page', () => {
  it('shows the interview with its job and application context', async () => {
    api.getInterview.mockResolvedValue(listItem())
    renderAt('/student/interviews/7')
    expect(await screen.findByRole('heading', { name: 'Technical interview' })).toBeInTheDocument()
    expect(screen.getByText(/Data Analyst · Aurora Analytics/)).toBeInTheDocument()
    expect(screen.getByText('Bring laptop')).toBeInTheDocument()
    expect(screen.getByText('Upcoming')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View application/ })).toHaveAttribute('href', '/student/applications/10')
  })

  it('prompts for a result when the interview has passed', async () => {
    api.getInterview.mockResolvedValue(listItem({ is_upcoming: false, needs_result: true, scheduled_at: '2020-01-01T10:00:00' }))
    renderAt('/student/interviews/7')
    expect(await screen.findByText(/This interview has passed: add the result/)).toBeInTheDocument()
  })

  it('edits the interview and shows the saved values', async () => {
    api.getInterview.mockResolvedValueOnce(listItem()).mockResolvedValue(listItem({ outcome: 'passed', notes: 'Went well' }))
    api.updateInterview.mockResolvedValue({})
    renderAt('/student/interviews/7')
    await userEvent.click(await screen.findByRole('button', { name: 'Edit interview' }))
    expect(screen.getByLabelText('Date and time')).toHaveValue('2030-05-20T14:30')
    await userEvent.selectOptions(screen.getByLabelText('Result'), 'passed')
    await userEvent.clear(screen.getByLabelText('Notes'))
    await userEvent.type(screen.getByLabelText('Notes'), 'Went well')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.updateInterview).toHaveBeenCalledWith(7, {
      stage: 'technical_interview', scheduled_at: '2030-05-20T14:30', outcome: 'passed', notes: 'Went well',
    }))
    expect(await screen.findByText('Interview saved.')).toBeInTheDocument()
    expect(screen.getByText('Passed')).toBeInTheDocument()
  })

  it('can clear the date when editing', async () => {
    api.getInterview.mockResolvedValue(listItem())
    api.updateInterview.mockResolvedValue({})
    renderAt('/student/interviews/7')
    await userEvent.click(await screen.findByRole('button', { name: 'Edit interview' }))
    await userEvent.clear(screen.getByLabelText('Date and time'))
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.updateInterview).toHaveBeenCalledWith(7, expect.objectContaining({ scheduled_at: null })))
  })

  it('deletes after confirmation and returns to the application', async () => {
    api.getInterview.mockResolvedValue(listItem())
    api.deleteInterview.mockResolvedValue({})
    api.getApplication.mockResolvedValue(detail())
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderAt('/student/interviews/7')
    await userEvent.click(await screen.findByRole('button', { name: 'Delete' }))
    await waitFor(() => expect(api.deleteInterview).toHaveBeenCalledWith(7))
    expect(await screen.findByRole('heading', { name: 'Data Analyst' })).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('cannot be edited once the application was withdrawn', async () => {
    api.getInterview.mockResolvedValue(listItem({ application: { id: 10, status: 'withdrawn', job } }))
    renderAt('/student/interviews/7')
    expect(await screen.findByText(/application was withdrawn/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Edit interview' })).not.toBeInTheDocument()
  })

  it('shows a friendly message for an unknown interview', async () => {
    api.getInterview.mockRejectedValue({ response: { status: 404, data: { detail: 'Interview not found.' } } })
    renderAt('/student/interviews/99')
    expect(await screen.findByRole('alert')).toHaveTextContent('This interview does not exist.')
  })
})

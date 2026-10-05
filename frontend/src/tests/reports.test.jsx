import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as admin from '../api/admin'
import * as reports from '../api/reports'
import { BarList, StackedBars } from '../components/charts/Charts'
import { AuthContext } from '../context/AuthContext'
import CoordinatorReport from '../pages/coordinator/Reports'
import StudentReport from '../pages/student/Report'
import ProtectedRoute from '../routes/ProtectedRoute'

vi.mock('../api/admin')
vi.mock('../api/reports')

const zeroStatus = ['applied', 'shortlisted', 'online_assessment', 'technical_interview', 'hr_interview', 'selected', 'rejected', 'withdrawn']
const distribution = (over = {}) => zeroStatus.map((status) => ({ status, count: over[status] ?? 0 }))

const STUDENT = {
  generated_at: '2026-10-05T10:00:00',
  student: { name: 'Bhavna Rao', first_name: 'Bhavna', branch: 'Computer Science and Engineering', year: 3, semester: 5, cgpa: 7.8 },
  summary: { total: 3, active: 2, awaiting_review: 1, in_process: 1, selected: 0, rejected: 0, withdrawn: 1, outcome: 'in_process', outcome_label: 'In the selection process' },
  status_distribution: distribution({ applied: 1, shortlisted: 1, withdrawn: 1 }),
  applications: [
    { id: 11, job_id: 3, job_title: 'Data Scientist', company: 'QuantaRetail Tech', status: 'shortlisted', applied_at: '2026-10-01T10:00:00', updated_at: '2026-10-02T10:00:00', interviews: 2, next_interview: '2030-05-20T14:30:00' },
    { id: 12, job_id: 4, job_title: 'Security Analyst', company: 'Helix Secure', status: 'applied', applied_at: '2026-10-02T10:00:00', updated_at: '2026-10-02T10:00:00', interviews: 0, next_interview: null },
  ],
  interviews: { total: 2, passed: 1, not_cleared: 0, pending: 1, upcoming: 1, pass_rate: 100,
    items: [{ id: 5, application_id: 11, job_title: 'Data Scientist', company: 'QuantaRetail Tech', stage: 'technical_interview', scheduled_at: '2030-05-20T14:30:00', outcome: 'pending' }] },
  recommended: { open_jobs: 18, eligible: 4, incomplete_profile: 0, not_eligible: 14, hints: [],
    top: [{ job_id: 7, title: 'Backend Developer', company: 'Zenith Labs', location: 'Pune', deadline: null, match_score: 82, eligibility: 'ELIGIBLE', missing_skills: [], already_applied: false }] },
  skill_gaps: { student_has_skills: true, based_on_jobs: 5, top_missing: [{ name: 'Docker', jobs_needing: 4, example_jobs: [] }, { name: 'AWS', jobs_needing: 2, example_jobs: [] }], closest_job: null },
  progress: { percent: 50, done: 3, total: 6, next_step: { key: 'interviewed', label: 'Record an interview', reason: '', link: '/student/interviews' },
    milestones: [{ key: 'profile', label: 'Complete your profile', done: true, detail: '90% complete', link: '/x' }, { key: 'selected', label: 'Receive an offer', done: false, detail: 'Not yet', link: '/y' }] },
  errors: {},
}
const EMPTY_STUDENT = {
  ...STUDENT, summary: { total: 0, active: 0, awaiting_review: 0, in_process: 0, selected: 0, rejected: 0, withdrawn: 0, outcome: 'not_applied', outcome_label: 'Not applied yet' },
  status_distribution: distribution(), applications: [], interviews: { total: 0, passed: 0, not_cleared: 0, pending: 0, upcoming: 0, pass_rate: null, items: [] },
  recommended: { ...STUDENT.recommended, top: [], eligible: 0 }, skill_gaps: { student_has_skills: false, based_on_jobs: 0, top_missing: [], closest_job: null },
  progress: { ...STUDENT.progress, percent: 0, done: 0, next_step: null },
}

const rate = (over = {}) => ({ percent: 14, placed: 1, total_students: 7, sufficient_data: true, note: '1 of 7 registered students have a selected application.', ...over })
const step = (key, label, count, percent) => ({ key, label, count, percent })
const COORD = {
  generated_at: '2026-10-05T10:00:00', min_group_size: 5,
  placement: {
    total_students: 7, applicants: 5, placed: 1, in_process: 2, rejected: 1, not_applied: 2, placement_rate: rate(),
    by_stage: [step('placed', 'Placed', 1, 14), step('in_process', 'In the selection process', 2, 29), step('applied', 'Applied, awaiting review', 1, 14), step('rejected', 'Not selected so far', 1, 14), step('not_applied', 'Not applied yet', 2, 29)],
    by_branch: [{ branch: 'Computer Science and Engineering', students: 3, applicants: 2, placed: 1, placement_rate: null }, { branch: 'Information Technology', students: 6, applicants: 4, placed: 3, placement_rate: 50 }],
    by_cgpa: [{ band: '8.0 - 8.9', students: 1, placed: 1, placement_rate: null }],
  },
  status_distribution: distribution({ applied: 2, shortlisted: 1, selected: 1, rejected: 1, withdrawn: 1 }),
  companies: [
    { company: 'Aurora Analytics', jobs: 3, applications: 2, shortlisted: 0, selected: 1, rejected: 0 },
    { company: 'Zenith Software Labs', jobs: 3, applications: 0, shortlisted: 0, selected: 0, rejected: 0 },
  ],
  jobs: [
    { job_id: 1, title: 'Data Analyst', company: 'Aurora Analytics', status: 'open', deadline: null, applications: 2, awaiting_review: 0, in_process: 0, selected: 1, rejected: 0, withdrawn: 1 },
    { job_id: 2, title: 'QA Engineer', company: 'BrightPath', status: 'closed', deadline: null, applications: 0, awaiting_review: 0, in_process: 0, selected: 0, rejected: 0, withdrawn: 0 },
  ],
  selected_students: [{ student_id: 9, name: 'Asha Patil', email: 'asha@example.com', branch: 'Computer Science and Engineering', cgpa: 8.5, company: 'Aurora Analytics', job_title: 'Data Analyst', selected_on: '2026-10-04' }],
  skill_gaps: [{ skill: 'Python', jobs_requiring: 6, students_with: 2, students_lacking: 5, percent_lacking: 71 }],
  interviews: { total: 3, passed: 1, not_cleared: 1, pending: 1, pass_rate: 50 },
  progress: { total_students: 7, funnel: [step('registered', 'Registered', 7, 100), step('applied', 'Applied to a job', 5, 71)], current_stage: [], needs_attention: {} },
}
const EMPTY_COORD = {
  ...COORD,
  placement: { total_students: 0, applicants: 0, placed: 0, in_process: 0, rejected: 0, not_applied: 0, placement_rate: rate({ percent: null, sufficient_data: false, total_students: 0, placed: 0, note: 'Needs at least 5 registered students before a rate is meaningful (there are 0).' }), by_stage: [], by_branch: [], by_cgpa: [] },
  status_distribution: distribution(), companies: [], jobs: [], selected_students: [], skill_gaps: [], interviews: { total: 0, passed: 0, not_cleared: 0, pending: 0, pass_rate: null },
  progress: { total_students: 0, funnel: [step('registered', 'Registered', 0, 0)], current_stage: [], needs_attention: {} },
}

function renderAt(path, element, user = { id: 1, role: 'student', full_name: 'Bhavna' }, role = 'student') {
  return render(
    <AuthContext.Provider value={{ user, loading: false, logout: vi.fn() }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<ProtectedRoute role={role} />}><Route path={path.split('?')[0]} element={element} /></Route>
          <Route path="/student" element={<p>student home</p>} />
          <Route path="/coordinator" element={<p>coordinator home</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}
const asStudent = () => renderAt('/student/report', <StudentReport />)
const asCoordinator = () => renderAt('/coordinator/reports', <CoordinatorReport />, { id: 2, role: 'coordinator', full_name: 'Dr. Rao' }, 'coordinator')

beforeEach(() => {
  vi.resetAllMocks()
  admin.getReports.mockResolvedValue([{ kind: 'students', description: 'All students', url: '/a' }, { kind: 'jobs', description: 'Per job', url: '/b' }])
})

describe('charts', () => {
  it('draws every bar to the same scale and prints its number', () => {
    const { container } = render(<BarList label="Demo" rows={[{ label: 'Python', value: 5 }, { label: 'SQL', value: 10, note: '(x)' }]} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Python5')
    expect(items[1]).toHaveTextContent('SQL10(x)')
    const bars = container.querySelectorAll('[aria-hidden="true"] > div')
    expect(bars[0].style.width).toBe('50%')
    expect(bars[1].style.width).toBe('100%')
  })

  it('uses a fixed maximum when given one, and never draws past 100%', () => {
    const { container } = render(<BarList label="Demo" max={20} rows={[{ label: 'A', value: 5 }, { label: 'B', value: 40 }]} />)
    const bars = container.querySelectorAll('[aria-hidden="true"] > div')
    expect(bars[0].style.width).toBe('25%')
    expect(bars[1].style.width).toBe('100%')
  })

  it('does not break when every value is zero', () => {
    const { container } = render(<BarList label="Demo" rows={[{ label: 'A', value: 0 }]} />)
    expect(container.querySelector('[aria-hidden="true"] > div').style.width).toBe('0%')
  })

  it('splits stacked bars into parts and explains them in words', () => {
    const series = [{ key: 'a', label: 'Passed', cls: 'bg-emerald-500' }, { key: 'b', label: 'Failed', cls: 'bg-red-500' }]
    const { container } = render(<StackedBars label="Results" series={series} rows={[{ label: 'Row 1', values: { a: 3, b: 1 } }, { label: 'Row 2', values: { a: 2 } }]} />)
    const rows = screen.getByRole('list', { name: 'Results' }).querySelectorAll(':scope > li')
    expect(rows[0]).toHaveTextContent('Row 14')
    expect(within(rows[0]).getByText('3 passed, 1 failed')).toHaveClass('sr-only')
    const segments = container.querySelectorAll('[title] > div')
    expect(Array.from(segments).map((d) => d.style.width)).toEqual(['75%', '25%', '50%'])
    expect(screen.getByRole('list', { name: 'Legend' })).toHaveTextContent('PassedFailed')
  })
})

describe('student report', () => {
  it('shows applications, statuses, interviews, outcome, recommended jobs, skill gaps and progress', async () => {
    reports.getMyReport.mockResolvedValue(STUDENT)
    asStudent()
    expect(await screen.findByText('In the selection process')).toBeInTheDocument()
    const summary = screen.getByLabelText('Summary')
    expect(summary).toHaveTextContent('Applications3')
    expect(summary).toHaveTextContent('2 active, 1 withdrawn')
    expect(summary).toHaveTextContent('Interviews2100% passed')

    const status = screen.getByRole('list', { name: 'Applications by status' })
    expect(within(status).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Applied1', 'Shortlisted1', 'Withdrawn1']) // zero statuses are left out

    const table = screen.getByRole('table', { name: 'My applications' })
    expect(within(table).getByRole('link', { name: 'Data Scientist' })).toHaveAttribute('href', '/student/applications/11')
    expect(within(table).getByText('Shortlisted', { selector: 'span' })).toBeInTheDocument()
    expect(screen.getByText(/1 upcoming · pass rate 100% of interviews with a result/)).toBeInTheDocument()

    expect(screen.getByText('4 of 18 open jobs match your eligibility.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Backend Developer · Zenith Labs' })).toHaveAttribute('href', '/student/jobs/7')
    expect(screen.getByText('82% match')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Missing skills' })).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Docker4 jobs', 'AWS2 jobs'])
    expect(screen.getByText('3 of 6 steps done')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Record an interview' })).toHaveAttribute('href', '/student/interviews')
  })

  it('explains empty data instead of drawing empty charts', async () => {
    reports.getMyReport.mockResolvedValue(EMPTY_STUDENT)
    asStudent()
    expect(await screen.findByText(/You have not applied to any job yet/)).toBeInTheDocument()
    expect(screen.getByText(/No interviews recorded/)).toBeInTheDocument()
    expect(screen.getByText('No applications yet.')).toBeInTheDocument()
    expect(screen.getByText(/No open jobs to recommend/)).toBeInTheDocument()
    expect(screen.getByText(/Add your skills to your profile/)).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Applications by status' })).not.toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Interview results' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Summary')).toHaveTextContent('No results recorded yet')
  })

  it('shows a failed section on its own and keeps the rest', async () => {
    reports.getMyReport.mockResolvedValue({ ...STUDENT, skill_gaps: null, errors: { skill_gaps: 'This section could not be loaded right now.' } })
    asStudent()
    expect(await screen.findByText('This section could not be loaded right now.')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'My applications' })).toBeInTheDocument()
  })

  it('downloads the CSV, and reports a failure', async () => {
    reports.getMyReport.mockResolvedValue(STUDENT)
    reports.downloadMyReport.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce('x.csv')
    asStudent()
    const button = await screen.findByRole('button', { name: 'Download CSV' })
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
    await userEvent.click(button)
    await waitFor(() => expect(reports.downloadMyReport).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('prints the page', async () => {
    reports.getMyReport.mockResolvedValue(STUDENT)
    const print = vi.spyOn(window, 'print').mockImplementation(() => {})
    asStudent()
    await userEvent.click(await screen.findByRole('button', { name: 'Print / save as PDF' }))
    expect(print).toHaveBeenCalled()
    print.mockRestore()
  })

  it('offers a retry when the report cannot be loaded', async () => {
    reports.getMyReport.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce(STUDENT)
    asStudent()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('In the selection process')).toBeInTheDocument()
  })

  it('is not available to a coordinator', async () => {
    renderAt('/student/report', <StudentReport />, { id: 2, role: 'coordinator', full_name: 'Dr. Rao' })
    expect(await screen.findByText('coordinator home')).toBeInTheDocument()
    expect(reports.getMyReport).not.toHaveBeenCalled()
  })
})

describe('coordinator report', () => {
  it('shows placement statistics and every breakdown', async () => {
    admin.getCoordinatorReport.mockResolvedValue(COORD)
    asCoordinator()
    const stats = await screen.findByLabelText('Placement statistics')
    expect(stats).toHaveTextContent('Students7')
    expect(stats).toHaveTextContent('Placed1')
    expect(stats).toHaveTextContent('Placement rate14%')

    expect(within(screen.getByRole('list', { name: 'Students by stage' })).getAllByRole('listitem')[0]).toHaveTextContent('Placed1(14%)')
    expect(within(screen.getByRole('list', { name: 'Applications by status' })).getAllByRole('listitem').map((li) => li.textContent)).toEqual(
      ['Applied2', 'Shortlisted1', 'Selected1', 'Rejected1', 'Withdrawn1'])

    const branches = within(screen.getByRole('list', { name: 'Students by branch' })).getAllByRole('listitem')
    expect(branches[0]).toHaveTextContent('Computer Science and Engineering3· needs 5+ students') // too few students for a rate
    expect(branches[1]).toHaveTextContent('Information Technology6· 50% placed')

    const company = within(screen.getByRole('list', { name: 'Applications by company' })).getAllByRole('listitem')
    expect(company).toHaveLength(1) // a company nobody applied to is not drawn as an empty bar
    expect(company[0]).toHaveTextContent('Aurora Analytics2')
    expect(screen.getByText('1 of 2 companies have no applications yet.')).toBeInTheDocument()

    const jobs = screen.getByRole('table', { name: 'Applications by job' })
    expect(within(jobs).getAllByRole('row')).toHaveLength(2) // header + the one job with applications
    expect(jobs).toHaveTextContent('Data Analyst')
    expect(screen.getByText(/1 of 2 jobs have no applications yet/)).toBeInTheDocument()

    const selected = screen.getByRole('table', { name: 'Selected students' })
    expect(within(selected).getByRole('link', { name: 'Asha Patil' })).toHaveAttribute('href', '/coordinator/students/9')
    expect(selected).toHaveTextContent('Aurora Analytics')

    expect(screen.getByRole('list', { name: 'Students lacking each skill' })).toHaveTextContent('Python5of 7 · 6 open jobs')
    expect(screen.getByRole('list', { name: 'Students reaching each milestone' })).toHaveTextContent('Applied to a job5(71%)')
    expect(screen.getByText('Pass rate: 50%')).toBeInTheDocument()
  })

  it('does not invent a placement rate when there is too little data', async () => {
    admin.getCoordinatorReport.mockResolvedValue({ ...COORD, placement: { ...COORD.placement, placement_rate: rate({ percent: null, sufficient_data: false, total_students: 3, note: 'Needs at least 5 registered students.' }) } })
    asCoordinator()
    const stats = await screen.findByLabelText('Placement statistics')
    expect(stats).toHaveTextContent('Placement rate—')
    expect(stats).toHaveTextContent('Needs at least 5 registered students.')
  })

  it('handles a platform with no students, applications or jobs', async () => {
    admin.getCoordinatorReport.mockResolvedValue(EMPTY_COORD)
    asCoordinator()
    expect(await screen.findByText('No students have registered yet.')).toBeInTheDocument()
    expect(screen.getByText('No student has been selected yet.')).toBeInTheDocument()
    expect(screen.getByText(/nothing to compare between companies/)).toBeInTheDocument()
    expect(screen.getByText('No interviews recorded yet.')).toBeInTheDocument()
    expect(screen.getByText(/No gaps to show/)).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Applications by job' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Placement statistics')).toHaveTextContent('Placement rate—')
  })

  it('limits the job table and says how many rows are hidden', async () => {
    const many = Array.from({ length: 20 }, (_, i) => ({ job_id: i, title: `Job ${i}`, company: 'X', status: 'open', deadline: null, applications: 20 - i, awaiting_review: 20 - i, in_process: 0, selected: 0, rejected: 0, withdrawn: 0 }))
    admin.getCoordinatorReport.mockResolvedValue({ ...COORD, jobs: many })
    asCoordinator()
    const table = await screen.findByRole('table', { name: 'Applications by job' })
    expect(within(table).getAllByRole('row')).toHaveLength(16)
    expect(screen.getByText(/Showing the 15 busiest of 20 jobs with applications/)).toBeInTheDocument()
  })

  it('exports each report as CSV through the API client', async () => {
    admin.getCoordinatorReport.mockResolvedValue(COORD)
    admin.downloadReport.mockResolvedValue('placegenie-jobs-2026-10-05.csv')
    asCoordinator()
    await userEvent.click(await screen.findByRole('button', { name: 'Download Jobs report' }))
    expect(admin.downloadReport).toHaveBeenCalledWith('jobs')
    expect(await screen.findByRole('status')).toHaveTextContent('Downloaded placegenie-jobs-2026-10-05.csv')
  })

  it('shows a message when an export fails', async () => {
    admin.getCoordinatorReport.mockResolvedValue(COORD)
    admin.downloadReport.mockRejectedValue({ response: { status: 403, data: { detail: 'Coordinator access required.' } } })
    asCoordinator()
    await userEvent.click(await screen.findByRole('button', { name: 'Download Students report' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Coordinator access required.')
  })

  it('is not available to a student', async () => {
    renderAt('/coordinator/reports', <CoordinatorReport />, { id: 1, role: 'student', full_name: 'Bhavna' }, 'coordinator')
    expect(await screen.findByText('student home')).toBeInTheDocument()
    expect(admin.getCoordinatorReport).not.toHaveBeenCalled()
  })
})

import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/admin'
import * as jobsApi from '../api/jobs'
import * as profileApi from '../api/profile'
import { AuthContext } from '../context/AuthContext'
import Analytics from '../pages/coordinator/Analytics'
import Applications from '../pages/coordinator/Applications'
import Companies from '../pages/coordinator/Companies'
import Dashboard from '../pages/coordinator/Dashboard'
import Jobs from '../pages/coordinator/Jobs'
import Progress from '../pages/coordinator/Progress'
import StudentDetail from '../pages/coordinator/StudentDetail'
import Students from '../pages/coordinator/Students'
import ProtectedRoute from '../routes/ProtectedRoute'
import { validateCompany } from '../utils/companyForm'
import { formToPayload, jobToForm, validateJob } from '../utils/jobForm'

vi.mock('../api/admin')
vi.mock('../api/jobs')
vi.mock('../api/profile')

const rate = (over = {}) => ({ percent: 14, placed: 1, total_students: 7, sufficient_data: true, note: '1 of 7 registered students have a selected application.', ...over })
const DASH = {
  generated_at: '2026-10-05T10:00:00',
  stats: { total_students: 7, total_companies: 10, total_jobs: 19, open_jobs: 18, total_applications: 7, withdrawn_applications: 1, applicants: 5,
    shortlisted_students: 2, selected_students: 1, rejected_applications: 1, placement_rate: rate() },
  application_funnel: [{ status: 'applied', count: 2 }, { status: 'shortlisted', count: 1 }, { status: 'selected', count: 1 }, { status: 'rejected', count: 1 }],
  recent_applications: [{ id: 5, student_id: 9, student_name: 'Gopal Iyer', job_title: 'Android Developer', company: 'Pixel Forge', status: 'applied', applied_at: '2026-10-04T10:00:00' }],
  attention: { awaiting_review: 2, closing_soon: [{ job_id: 3, title: 'Data Analyst', company: 'Aurora Analytics', deadline: '2030-01-01', applications: 1 }], open_jobs_without_applications: 12, interviews_this_week: 1 },
}
const row = (over = {}) => ({ id: 1, full_name: 'Asha Patil', email: 'asha@example.com', college: 'ABC', branch: { id: 1, name: 'Computer Science and Engineering' }, year: 2, semester: 3, cgpa: 8.5,
  backlogs: 0, profile_percent: 82, has_resume: true, applications: 2, stage: 'placed', ...over })
const PAGE = { items: [row(), row({ id: 2, full_name: 'Dev Kumar', email: 'dev@example.com', stage: 'in_process', backlogs: 2, has_resume: false })], total: 2, limit: 20, offset: 0,
  stage_counts: { placed: 1, in_process: 1, applied: 0, rejected: 0, not_applied: 0 } }
const job = { id: 3, title: 'Data Analyst', company: 'Aurora Analytics', location: 'Pune', job_type: 'full_time', deadline: '2030-01-01', is_expired: false }
const app = (over = {}) => ({ id: 10, status: 'applied', applied_at: '2026-10-01T10:00:00', updated_at: '2026-10-01T10:00:00', job,
  student: { id: 1, full_name: 'Asha Patil', email: 'asha@example.com', branch: { id: 1, name: 'CSE' }, cgpa: 8.5 }, interview_count: 0, next_interview: null, can_withdraw: true, ...over })

function renderAt(path, user = { id: 2, role: 'coordinator', full_name: 'Dr. Rao' }) {
  return render(
    <AuthContext.Provider value={{ user, loading: false, logout: vi.fn() }}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<ProtectedRoute role="coordinator" />}>
            <Route path="/coordinator" element={<Dashboard />} />
            <Route path="/coordinator/students" element={<Students />} />
            <Route path="/coordinator/students/:id" element={<StudentDetail />} />
            <Route path="/coordinator/companies" element={<Companies />} />
            <Route path="/coordinator/jobs" element={<Jobs />} />
            <Route path="/coordinator/applications" element={<Applications />} />
            <Route path="/coordinator/progress" element={<Progress />} />
            <Route path="/coordinator/analytics" element={<Analytics />} />
          </Route>
          <Route path="/student" element={<p>student home</p>} />
          <Route path="/login" element={<p>login page</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
  profileApi.getBranches.mockResolvedValue([{ id: 1, name: 'Computer Science and Engineering' }, { id: 2, name: 'Information Technology' }])
  profileApi.getSkills.mockResolvedValue([{ id: 7, name: 'Python', category: 'Programming' }, { id: 8, name: 'SQL', category: 'Data' }])
  profileApi.getJobRoles.mockResolvedValue([{ id: 4, name: 'Data Analyst' }])
  jobsApi.getCompanies.mockResolvedValue({ items: [{ id: 1, name: 'Aurora Analytics', industry: 'Analytics', location: 'Pune', website: 'https://aurora.example', description: null, open_jobs: 3 }], total: 1, limit: 100, offset: 0 })
})

describe('access control in the browser', () => {
  it('sends a student away from every coordinator page', async () => {
    for (const path of ['/coordinator', '/coordinator/students']) {
      const { unmount } = renderAt(path, { id: 1, role: 'student', full_name: 'Asha' })
      expect(await screen.findByText('student home')).toBeInTheDocument()
      unmount()
    }
    expect(api.getCoordinatorDashboard).not.toHaveBeenCalled()
    expect(api.getStudents).not.toHaveBeenCalled()
  })

  it('sends a visitor who is not logged in to the login page', async () => {
    renderAt('/coordinator/students', null)
    expect(await screen.findByText('login page')).toBeInTheDocument()
    expect(api.getStudents).not.toHaveBeenCalled()
  })
})

describe('dashboard', () => {
  it('shows every statistic', async () => {
    api.getCoordinatorDashboard.mockResolvedValue(DASH)
    renderAt('/coordinator')
    const stats = await screen.findByLabelText('Statistics')
    const text = (label) => within(stats).getByText(label).closest('a,div').textContent
    expect(text('Total students')).toContain('7')
    expect(text('Total companies')).toContain('10')
    expect(text('Total jobs')).toContain('19')
    expect(text('Total jobs')).toContain('18 open')
    expect(text('Total applications')).toContain('7')
    expect(text('Shortlisted students')).toContain('2')
    expect(text('Selected students')).toContain('1')
    expect(text('Rejected applications')).toContain('1')
    expect(text('Placement rate')).toContain('14%')
    expect(text('Placement rate')).toContain('1 of 7 registered students')
    expect(screen.getByRole('link', { name: 'Gopal Iyer' })).toHaveAttribute('href', '/coordinator/students/9')
    expect(screen.getByText(/2 applications awaiting review/)).toBeInTheDocument()
  })

  it('does not invent a placement rate when there is too little data', async () => {
    api.getCoordinatorDashboard.mockResolvedValue({ ...DASH, stats: { ...DASH.stats, placement_rate: rate({ percent: null, sufficient_data: false, note: 'Needs at least 5 students.' }) } })
    renderAt('/coordinator')
    const stats = await screen.findByLabelText('Statistics')
    const card = within(stats).getByText('Placement rate').closest('div')
    expect(card.textContent).toContain('—')
    expect(card.textContent).not.toContain('%')
    expect(card.textContent).toContain('Needs at least 5 students.')
  })

  it('offers a retry when the server fails', async () => {
    api.getCoordinatorDashboard.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce(DASH)
    renderAt('/coordinator')
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByLabelText('Statistics')).toBeInTheDocument()
  })
})

describe('students', () => {
  beforeEach(() => api.getStudents.mockResolvedValue(PAGE))

  it('lists students with their stage and counts per stage', async () => {
    renderAt('/coordinator/students')
    expect(await screen.findByRole('link', { name: 'Asha Patil' })).toHaveAttribute('href', '/coordinator/students/1')
    const table = screen.getByRole('table', { name: 'Students' })
    expect(within(table).getByText('Placed')).toBeInTheDocument()
    expect(within(table).getByText('(2 backlogs)')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'In process (1)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'All (2)' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('searches and filters through the API', async () => {
    renderAt('/coordinator/students')
    await screen.findByRole('link', { name: 'Asha Patil' })
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search students' }), 'asha{Enter}')
    await waitFor(() => expect(api.getStudents).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'asha' })))
    await userEvent.click(screen.getByRole('button', { name: 'In process (1)' }))
    await waitFor(() => expect(api.getStudents).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'asha', stage: 'in_process' })))
    await userEvent.selectOptions(screen.getByLabelText('Branch'), '2')
    await waitFor(() => expect(api.getStudents).toHaveBeenLastCalledWith(expect.objectContaining({ branch_id: '2', stage: 'in_process', q: 'asha' })))
    await userEvent.selectOptions(screen.getByLabelText('Resume'), 'false')
    await waitFor(() => expect(api.getStudents).toHaveBeenLastCalledWith(expect.objectContaining({ has_resume: 'false' })))
  })

  it('reads the filters from the URL', async () => {
    renderAt('/coordinator/students?stage=placed&min_cgpa=8')
    await screen.findByRole('link', { name: 'Asha Patil' })
    expect(api.getStudents).toHaveBeenCalledWith(expect.objectContaining({ stage: 'placed', min_cgpa: '8' }))
    expect(screen.getByRole('button', { name: /^Placed/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('says so when nothing matches, or when nobody has registered', async () => {
    api.getStudents.mockResolvedValue({ ...PAGE, items: [], total: 0 })
    renderAt('/coordinator/students?q=zzz')
    expect(await screen.findByText('No students match these filters.')).toBeInTheDocument()
  })

  it('pages through long lists', async () => {
    api.getStudents.mockResolvedValue({ ...PAGE, total: 45 })
    renderAt('/coordinator/students')
    await screen.findByText(/Page 1 of 3/)
    await userEvent.click(screen.getByRole('button', { name: 'Next →' }))
    await waitFor(() => expect(api.getStudents).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 20 })))
  })
})

describe('student placement profile', () => {
  const detail = {
    student_id: 1, stage: 'in_process', errors: {},
    profile: { id: 1, email: 'asha@example.com', full_name: 'Asha Patil', college: 'ABC Institute', branch: { id: 1, name: 'Computer Science and Engineering' }, year: 2, semester: 3, cgpa: 8.5, backlogs: 0,
      skills: [{ skill_id: 1, name: 'Python' }, { skill_id: 2, name: 'SQL' }], projects: [{}], experiences: [], certifications: [], completeness: { score: 82, missing: ['Interests'] } },
    resume: { uploaded: true, filename: 'asha.pdf', completeness_score: 90, skills_detected: 12 },
    progress: { percent: 33, done: 2, total: 6, next_step: null, milestones: [{ key: 'profile', label: 'Complete your profile', done: true, detail: '82% complete' }, { key: 'selected', label: 'Receive an offer', done: false, detail: 'Not yet' }] },
    skill_gaps: { student_has_skills: true, based_on_jobs: 10, top_missing: [{ name: 'Docker', jobs_needing: 4, example_jobs: [] }], closest_job: null },
    applications: { items: [app()], total: 1, limit: 20, offset: 0, counts: { applied: 1 } },
    interviews: { items: [{ id: 7, application_id: 10, stage: 'technical_interview', scheduled_at: '2030-05-20T14:30:00', outcome: 'passed', notes: null, is_upcoming: true, needs_result: false, application: { id: 10, status: 'applied', job } }], total: 1, counts: {} },
  }

  it('shows profile, resume, progress, skill gaps, applications and interviews', async () => {
    api.getStudentDetail.mockResolvedValue(detail)
    renderAt('/coordinator/students/1')
    expect(await screen.findByRole('heading', { name: 'Asha Patil' })).toBeInTheDocument()
    expect(api.getStudentDetail).toHaveBeenCalledWith('1')
    expect(screen.getByText('Python, SQL')).toBeInTheDocument()
    expect(screen.getByText('Missing: Interests')).toBeInTheDocument()
    expect(screen.getByText(/asha\.pdf · score 90\/100/)).toBeInTheDocument()
    expect(screen.getByText('2 of 6 steps done')).toBeInTheDocument()
    expect(screen.getByText('Docker (4 jobs)')).toBeInTheDocument()
    expect(screen.getByText('Passed')).toBeInTheDocument()
    expect(screen.getAllByText('In process').length).toBeGreaterThan(0)
  })

  it('updates an application status with the existing endpoint, then reloads', async () => {
    api.getStudentDetail.mockResolvedValue(detail)
    api.updateApplicationStatus.mockResolvedValue({})
    renderAt('/coordinator/students/1')
    const select = await screen.findByLabelText('Status for Asha Patil, Data Analyst')
    const update = screen.getByRole('button', { name: 'Update Status for Asha Patil, Data Analyst' })
    expect(update).toBeDisabled()
    expect(within(select).queryByRole('option', { name: 'Withdrawn' })).not.toBeInTheDocument()
    await userEvent.selectOptions(select, 'shortlisted')
    await userEvent.click(update)
    await waitFor(() => expect(api.updateApplicationStatus).toHaveBeenCalledWith(10, 'shortlisted'))
    await waitFor(() => expect(api.getStudentDetail).toHaveBeenCalledTimes(2))
  })

  it('shows the server message when a status cannot be changed', async () => {
    api.getStudentDetail.mockResolvedValue(detail)
    api.updateApplicationStatus.mockRejectedValue({ response: { status: 409, data: { detail: 'The student withdrew this application; its status cannot be changed.' } } })
    renderAt('/coordinator/students/1')
    await userEvent.selectOptions(await screen.findByLabelText('Status for Asha Patil, Data Analyst'), 'rejected')
    await userEvent.click(screen.getByRole('button', { name: /^Update Status/ }))
    expect(await screen.findByText(/withdrew this application/)).toBeInTheDocument()
  })

  it('locks withdrawn applications', async () => {
    api.getStudentDetail.mockResolvedValue({ ...detail, applications: { ...detail.applications, items: [app({ status: 'withdrawn' })] } })
    renderAt('/coordinator/students/1')
    expect(await screen.findByText('Withdrawn by the student')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Update/ })).not.toBeInTheDocument()
  })

  it('shows "not found" for an unknown student', async () => {
    api.getStudentDetail.mockRejectedValue({ response: { status: 404, data: { detail: 'Student not found.' } } })
    renderAt('/coordinator/students/999')
    expect(await screen.findByRole('alert')).toHaveTextContent('Student not found.')
  })
})

describe('companies', () => {
  it('lists companies', async () => {
    renderAt('/coordinator/companies')
    expect(await screen.findByText('Aurora Analytics')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://aurora.example' })).toHaveAttribute('rel', 'noreferrer noopener')
  })

  it('adds a company after validating the form', async () => {
    api.createCompany.mockResolvedValue({ id: 2 })
    renderAt('/coordinator/companies')
    await screen.findByText('Aurora Analytics')
    await userEvent.click(screen.getByRole('button', { name: 'Add company' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Add company' })[1])
    expect(await screen.findByText(/Enter the company name/)).toBeInTheDocument()
    expect(api.createCompany).not.toHaveBeenCalled()

    await userEvent.type(screen.getByLabelText('Company name'), '  Nova Labs ')
    await userEvent.type(screen.getByLabelText('Website'), 'nova.example')
    await userEvent.click(screen.getAllByRole('button', { name: 'Add company' })[1])
    expect(await screen.findByText('Website must start with http:// or https://')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Website'))
    await userEvent.type(screen.getByLabelText('Website'), 'https://nova.example')
    await userEvent.click(screen.getAllByRole('button', { name: 'Add company' })[1])
    await waitFor(() => expect(api.createCompany).toHaveBeenCalledWith({ name: 'Nova Labs', industry: null, website: 'https://nova.example', location: null, description: null }))
    expect(await screen.findByRole('status')).toHaveTextContent('Company added.')
  })

  it('edits a company', async () => {
    api.updateCompany.mockResolvedValue({})
    renderAt('/coordinator/companies')
    await userEvent.click(await screen.findByRole('button', { name: 'Edit Aurora Analytics' }))
    const name = screen.getByLabelText('Company name')
    expect(name).toHaveValue('Aurora Analytics')
    await userEvent.clear(name)
    await userEvent.type(name, 'Aurora Data')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.updateCompany).toHaveBeenCalledWith(1, expect.objectContaining({ name: 'Aurora Data', industry: 'Analytics' })))
  })

  it('asks before deleting, and explains why a company with applications cannot be deleted', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValue(true)
    api.deleteCompany.mockRejectedValue({ response: { status: 409, data: { detail: 'This company has applications and cannot be deleted. Close its jobs instead.' } } })
    renderAt('/coordinator/companies')
    const button = await screen.findByRole('button', { name: 'Delete Aurora Analytics' })
    await userEvent.click(button)
    expect(api.deleteCompany).not.toHaveBeenCalled()
    await userEvent.click(button)
    await waitFor(() => expect(api.deleteCompany).toHaveBeenCalledWith(1))
    expect(await screen.findByRole('alert')).toHaveTextContent('cannot be deleted')
    confirm.mockRestore()
  })

  it('validates company details', () => {
    expect(validateCompany({ name: 'A', website: '' })).toHaveProperty('name')
    expect(validateCompany({ name: 'Acme', website: 'ftp://x' })).toHaveProperty('website')
    expect(validateCompany({ name: 'Acme', website: 'https://acme.example' })).toEqual({})
  })
})

describe('jobs', () => {
  const jobOut = {
    id: 3, title: 'Data Analyst', description: 'Analyse data', location: 'Pune', job_type: 'full_time', min_cgpa: 7, max_backlogs: null, min_experience_months: 0, deadline: '2030-01-01', is_expired: false,
    status: 'open', company: { id: 1, name: 'Aurora Analytics', industry: null, location: null }, role: { id: 4, name: 'Data Analyst' },
    skills: [{ skill_id: 7, name: 'Python', category: null, importance: 'required', weight: 3 }], allowed_branches: [{ id: 1, name: 'Computer Science and Engineering' }],
    required_certifications: ['AWS'], created_at: '2026-10-01T10:00:00',
  }
  beforeEach(() => jobsApi.getJobs.mockResolvedValue({ items: [jobOut], total: 1, limit: 15, offset: 0 }))

  it('lists jobs and filters by company and status', async () => {
    renderAt('/coordinator/jobs')
    expect(await screen.findByText('Data Analyst', { selector: 'p' })).toBeInTheDocument()
    await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Filter by status' }), 'closed')
    await waitFor(() => expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'closed' })))
    await waitFor(() => expect(screen.getByRole('option', { name: 'Aurora Analytics' })).toBeInTheDocument())
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Filter by company' }), '1')
    await waitFor(() => expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '1', status: 'closed' })))
  })

  it('adds a job with skills, branches and certifications', async () => {
    api.createJob.mockResolvedValue({ id: 9 })
    renderAt('/coordinator/jobs')
    await screen.findByText('Data Analyst', { selector: 'p' })
    const add = screen.getByRole('button', { name: 'Add job' })
    await waitFor(() => expect(add).toBeEnabled())
    await userEvent.click(add)
    await userEvent.click(screen.getAllByRole('button', { name: 'Add job' })[1])
    expect(await screen.findByText('Choose the company.')).toBeInTheDocument()
    expect(screen.getByText(/Enter the job title/)).toBeInTheDocument()
    expect(api.createJob).not.toHaveBeenCalled()

    await userEvent.selectOptions(screen.getByLabelText('Company'), '1')
    await userEvent.type(screen.getByLabelText('Job title'), 'Data Engineer')
    await userEvent.clear(screen.getByLabelText('Minimum CGPA'))
    await userEvent.type(screen.getByLabelText('Minimum CGPA'), '7.5')
    await userEvent.click(screen.getByRole('button', { name: 'Add a skill' }))
    await userEvent.selectOptions(screen.getByLabelText('Skill 1'), '7')
    await userEvent.click(screen.getByLabelText('Computer Science and Engineering'))
    await userEvent.type(screen.getByLabelText(/Required certifications/), 'AWS, , Azure ')
    await userEvent.click(screen.getAllByRole('button', { name: 'Add job' })[1])
    await waitFor(() => expect(api.createJob).toHaveBeenCalledWith(expect.objectContaining({
      company_id: 1, title: 'Data Engineer', min_cgpa: 7.5, max_backlogs: null, status: 'open', job_type: 'full_time', deadline: null,
      skills: [{ skill_id: 7, importance: 'required', weight: 3 }], allowed_branch_ids: [1], required_certifications: ['AWS', 'Azure'],
    })))
    expect(await screen.findByRole('status')).toHaveTextContent('Job added.')
  })

  it('edits a job, starting from its current values', async () => {
    api.updateJob.mockResolvedValue({})
    renderAt('/coordinator/jobs')
    const edit = await screen.findByRole('button', { name: 'Edit Data Analyst at Aurora Analytics' })
    await waitFor(() => expect(edit).toBeEnabled())
    await userEvent.click(edit)
    expect(screen.getByLabelText('Job title')).toHaveValue('Data Analyst')
    expect(screen.getByLabelText('Skill 1')).toHaveValue('7')
    expect(screen.getByLabelText('Computer Science and Engineering')).toBeChecked()
    expect(screen.getByLabelText(/Required certifications/)).toHaveValue('AWS')
    await userEvent.selectOptions(screen.getByLabelText('Status'), 'closed')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.updateJob).toHaveBeenCalledWith(3, expect.objectContaining({ status: 'closed', title: 'Data Analyst', min_cgpa: 7, deadline: '2030-01-01', role_id: 4 })))
  })

  it('explains why a job with applications cannot be deleted', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    api.deleteJob.mockRejectedValue({ response: { status: 409, data: { detail: 'This job has applications. Close it instead of deleting it.' } } })
    renderAt('/coordinator/jobs')
    await userEvent.click(await screen.findByRole('button', { name: 'Delete Data Analyst at Aurora Analytics' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Close it instead')
  })

  it('validates jobs and converts the form to the API shape', () => {
    const blank = jobToForm(null)
    expect(Object.keys(validateJob(blank))).toEqual(['company_id', 'title'])
    expect(validateJob({ ...blank, company_id: '1', title: 'QA', min_cgpa: '11' })).toHaveProperty('min_cgpa')
    expect(validateJob({ ...blank, company_id: '1', title: 'QA', skills: [{ skill_id: '', importance: 'required', weight: '1' }] })).toHaveProperty('skills')
    const dup = { skill_id: '7', importance: 'required', weight: '1' }
    expect(validateJob({ ...blank, company_id: '1', title: 'QA', skills: [dup, dup] }).skills).toMatch(/only be listed once/)
    expect(validateJob({ ...blank, company_id: '1', title: 'QA' })).toEqual({})
    expect(formToPayload(jobToForm(jobOut))).toEqual({
      company_id: 1, role_id: 4, title: 'Data Analyst', description: 'Analyse data', location: 'Pune', job_type: 'full_time', min_cgpa: 7, max_backlogs: null,
      min_experience_months: 0, deadline: '2030-01-01', status: 'open', skills: [{ skill_id: 7, importance: 'required', weight: 3 }], allowed_branch_ids: [1], required_certifications: ['AWS'],
    })
  })
})

describe('applications', () => {
  const list = (items, counts = { applied: items.length }) => ({ items, total: items.length, limit: 20, offset: 0, counts })

  it('filters by company, job and status', async () => {
    api.getApplications.mockResolvedValue(list([app()], { applied: 1, selected: 2 }))
    jobsApi.getJobs.mockResolvedValue({ items: [{ id: 3, title: 'Data Analyst', company: { id: 1, name: 'Aurora Analytics' } }], total: 1, limit: 100, offset: 0 })
    renderAt('/coordinator/applications')
    expect(await screen.findByRole('link', { name: 'Asha Patil' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'All (3)' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('option', { name: 'Aurora Analytics' })).toBeInTheDocument())
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Filter by company' }), '1')
    await waitFor(() => expect(api.getApplications).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '1' })))
    await waitFor(() => expect(jobsApi.getJobs).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '1' })))
    await userEvent.selectOptions(await screen.findByRole('combobox', { name: 'Filter by job' }), '3')
    await waitFor(() => expect(api.getApplications).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '1', job_id: '3' })))
    await userEvent.click(screen.getByRole('button', { name: 'Selected (2)' }))
    await waitFor(() => expect(api.getApplications).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '1', job_id: '3', status: 'selected' })))
  })

  it('changing the company clears the job filter', async () => {
    api.getApplications.mockResolvedValue(list([app()]))
    jobsApi.getJobs.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    renderAt('/coordinator/applications?company_id=1&job_id=3')
    await screen.findByRole('link', { name: 'Asha Patil' })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Filter by company' }), '')
    await waitFor(() => expect(api.getApplications).toHaveBeenLastCalledWith(expect.objectContaining({ company_id: '', job_id: '' })))
  })

  it('updates the status of an application in the list', async () => {
    api.getApplications.mockResolvedValue(list([app()]))
    jobsApi.getJobs.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    api.updateApplicationStatus.mockResolvedValue({})
    renderAt('/coordinator/applications')
    await userEvent.selectOptions(await screen.findByLabelText('Status for Asha Patil, Data Analyst'), 'selected')
    await userEvent.click(screen.getByRole('button', { name: /^Update Status/ }))
    await waitFor(() => expect(api.updateApplicationStatus).toHaveBeenCalledWith(10, 'selected'))
    await waitFor(() => expect(api.getApplications).toHaveBeenCalledTimes(2))
  })

  it('has an empty state', async () => {
    api.getApplications.mockResolvedValue(list([], {}))
    jobsApi.getJobs.mockResolvedValue({ items: [], total: 0, limit: 100, offset: 0 })
    renderAt('/coordinator/applications')
    expect(await screen.findByText('No applications yet.')).toBeInTheDocument()
  })
})

describe('progress and analytics', () => {
  it('shows the cohort funnel and who needs attention', async () => {
    api.getCohortProgress.mockResolvedValue({
      total_students: 7,
      funnel: [{ key: 'registered', label: 'Registered', count: 7, percent: 100 }, { key: 'applied', label: 'Applied to a job', count: 5, percent: 71 }],
      current_stage: [{ key: 'placed', label: 'Placed', count: 1, percent: 14 }, { key: 'not_applied', label: 'Not applied yet', count: 2, percent: 29 }],
      needs_attention: { no_resume: 5, profile_not_ready: 1, not_applied: 2 },
    })
    renderAt('/coordinator/progress')
    expect(await screen.findByText('Milestones reached (7 students)')).toBeInTheDocument()
    expect(screen.getByText('5 · 71%')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '5 students have not uploaded a resume' })).toHaveAttribute('href', '/coordinator/students?has_resume=false')
    expect(screen.getByRole('link', { name: '1 student have a profile under 80% complete' })).toBeInTheDocument()
  })

  it('shows analytics and hides rates for small groups', async () => {
    api.getAnalytics.mockResolvedValue({
      status_funnel: [], min_group_size: 5,
      by_company: [{ company: 'Aurora Analytics', jobs: 3, applications: 4, shortlisted: 1, selected: 1, rejected: 0 }],
      by_branch: [{ branch: 'Computer Science and Engineering', students: 3, applicants: 2, placed: 1, placement_rate: null }, { branch: 'Information Technology', students: 6, applicants: 4, placed: 3, placement_rate: 50 }],
      by_cgpa: [{ band: '8.0 - 8.9', students: 1, placed: 1, placement_rate: null }],
      skill_supply: [{ skill: 'Python', jobs_requiring: 6, students_with: 2, students_percent: 29 }],
      interview_outcomes: { total: 3, passed: 1, not_cleared: 1, pending: 1, pass_rate: 50 },
    })
    renderAt('/coordinator/analytics')
    expect(await screen.findByText('Aurora Analytics')).toBeInTheDocument()
    expect(screen.getAllByText('needs 5+ students').length).toBe(2)
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.getByText('Pass rate: 50%')).toBeInTheDocument()
    expect(screen.getByText('6 open jobs · 2 students (29%)')).toBeInTheDocument()
  })
})

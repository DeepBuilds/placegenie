import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/profile'
import Profile from '../pages/student/Profile'
import { basicPayload, validateAcademic } from '../utils/profile'

vi.mock('../api/profile')

const emptyProfile = {
  id: 1, email: 'a@x.com', full_name: 'Asha Patil', phone: null, college: null, branch: null,
  year: null, semester: null, cgpa: null, backlogs: 0, interests: null, preferred_location: null,
  preferred_job_type: null, skills: [], certifications: [], projects: [], experiences: [],
  preferred_roles: [], preferred_companies: [],
  completeness: { score: 0, missing: ['Phone number', 'CGPA'] },
}

const branches = [{ id: 1, name: 'Computer Science and Engineering' }]
const skills = [{ id: 10, name: 'Python', category: 'Programming' }, { id: 11, name: 'SQL', category: 'Database' }]
const roles = [{ id: 5, name: 'Data Analyst', category: 'Data' }]

beforeEach(() => {
  vi.resetAllMocks()
  api.getProfile.mockResolvedValue(emptyProfile)
  api.getBranches.mockResolvedValue(branches)
  api.getSkills.mockResolvedValue(skills)
  api.getJobRoles.mockResolvedValue(roles)
})

describe('profile page', () => {
  it('shows loading, then the profile and completeness hints', async () => {
    render(<Profile />)
    expect(screen.getByText(/loading your profile/i)).toBeInTheDocument()
    expect(await screen.findByDisplayValue('Asha Patil')).toBeInTheDocument()
    expect(screen.getByText(/Still missing: Phone number, CGPA/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Email/)).toHaveValue('a@x.com')
  })

  it('shows an error with a retry button when loading fails', async () => {
    api.getProfile.mockRejectedValueOnce({ response: { status: 500, data: {} } })
    render(<Profile />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(await screen.findByDisplayValue('Asha Patil')).toBeInTheDocument()
  })

  it('blocks invalid academic data without calling the API', async () => {
    render(<Profile />)
    await screen.findByDisplayValue('Asha Patil')
    await userEvent.type(screen.getByLabelText('CGPA (out of 10)'), '11')
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }))
    expect(await screen.findByText('CGPA must be between 0 and 10.')).toBeInTheDocument()
    expect(api.saveProfile).not.toHaveBeenCalled()
  })

  it('saves academic details and shows a success message', async () => {
    api.saveProfile.mockResolvedValue({ ...emptyProfile, cgpa: 8.5, college: 'ABC' })
    render(<Profile />)
    await screen.findByDisplayValue('Asha Patil')
    await userEvent.type(screen.getByLabelText('College'), 'ABC')
    await userEvent.type(screen.getByLabelText('CGPA (out of 10)'), '8.5')
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }))
    expect(await screen.findByRole('status')).toHaveTextContent(/saved/i)
    expect(api.saveProfile).toHaveBeenCalledWith(expect.objectContaining({ college: 'ABC', cgpa: 8.5 }))
  })

  it('shows the server validation message when saving fails', async () => {
    api.saveProfile.mockRejectedValue({ response: { status: 422, data: { detail: 'Selected branch does not exist.' } } })
    render(<Profile />)
    await screen.findByDisplayValue('Asha Patil')
    await userEvent.click(screen.getByRole('button', { name: 'Save details' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Selected branch does not exist.')
  })

  it('adds and removes a skill by sending the full skill list', async () => {
    const withPython = {
      ...emptyProfile,
      skills: [{ skill_id: 10, name: 'Python', category: 'Programming', proficiency: 'beginner', source: 'manual' }],
    }
    api.saveSkills.mockResolvedValueOnce(withPython).mockResolvedValueOnce(emptyProfile)
    render(<Profile />)
    await screen.findByDisplayValue('Asha Patil')

    await userEvent.selectOptions(screen.getByLabelText('Add a skill'), 'Python')
    await userEvent.click(screen.getByRole('button', { name: 'Add skill' }))
    expect(api.saveSkills).toHaveBeenLastCalledWith([{ skill_id: 10, proficiency: 'beginner' }])
    const list = await screen.findByRole('list', { name: 'Your skills' })
    expect(within(list).getByText('Python')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Remove Python' }))
    expect(api.saveSkills).toHaveBeenLastCalledWith([])
    await waitFor(() => expect(screen.queryByRole('list', { name: 'Your skills' })).not.toBeInTheDocument())
  })

  it('adds a certification and requires its name', async () => {
    api.addItem.mockResolvedValue({ ...emptyProfile, certifications: [{ id: 1, name: 'AWS CP', issuer: 'Amazon', issued_on: null }] })
    render(<Profile />)
    await screen.findByDisplayValue('Asha Patil')
    await userEvent.click(screen.getByRole('button', { name: '+ Add certification' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(await screen.findByText('Certification name is required.')).toBeInTheDocument()
    expect(api.addItem).not.toHaveBeenCalled()

    await userEvent.type(screen.getByLabelText(/Certification name/), 'AWS CP')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    expect(api.addItem).toHaveBeenCalledWith('certifications', { name: 'AWS CP', issuer: null, issued_on: null })
    expect(await screen.findByText('AWS CP')).toBeInTheDocument()
  })

  it('removes a project', async () => {
    api.getProfile.mockResolvedValue({ ...emptyProfile, projects: [{ id: 3, title: 'Placement app', tech_stack: null, description: null, url: null }] })
    api.removeItem.mockResolvedValue(emptyProfile)
    render(<Profile />)
    await userEvent.click(await screen.findByRole('button', { name: 'Remove Placement app' }))
    expect(api.removeItem).toHaveBeenCalledWith('projects', 3)
    await waitFor(() => expect(screen.queryByText('Placement app')).not.toBeInTheDocument())
  })
})

describe('profile helpers', () => {
  it('validateAcademic enforces ranges and year/semester consistency', () => {
    const ok = { full_name: 'Asha', phone: '', cgpa: '8', backlogs: '0', year: '2', semester: '3' }
    expect(validateAcademic(ok)).toEqual({})
    expect(validateAcademic({ ...ok, semester: '6' }).semester).toMatch(/Year 2 has semesters 3 and 4/)
    expect(validateAcademic({ ...ok, cgpa: '12' }).cgpa).toBeDefined()
    expect(validateAcademic({ ...ok, backlogs: '-1' }).backlogs).toBeDefined()
    expect(validateAcademic({ ...ok, phone: 'abc' }).phone).toBeDefined()
  })

  it('basicPayload keeps unchanged fields when overriding some', () => {
    const p = { ...emptyProfile, branch: { id: 1, name: 'CSE' }, cgpa: 8 }
    expect(basicPayload(p, { interests: 'AI' })).toMatchObject({ branch_id: 1, cgpa: 8, interests: 'AI' })
  })
})

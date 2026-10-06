import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '../api/auth'
import { AuthProvider } from '../context/AuthContext'
import Login from '../pages/Login'
import Register from '../pages/Register'
import ProtectedRoute from '../routes/ProtectedRoute'
import { getErrorMessage } from '../utils/errors'
import { getToken, setToken } from '../utils/storage'

vi.mock('../api/auth')

const student = { id: 1, email: 'a@x.com', role: 'student', full_name: 'Asha' }
const coordinator = { id: 2, email: 'c@x.com', role: 'coordinator', full_name: 'Rao' }

function renderApp(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<ProtectedRoute role="student" />}>
            <Route path="/student" element={<p>student area</p>} />
          </Route>
          <Route element={<ProtectedRoute role="coordinator" />}>
            <Route path="/coordinator" element={<p>coordinator area</p>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.resetAllMocks()
})

describe('protected routes', () => {
  it('redirects anonymous visitors to the login page', async () => {
    renderApp('/student')
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByText('student area')).not.toBeInTheDocument()
  })

  it('lets a logged-in student into the student area', async () => {
    setToken('t')
    authApi.fetchCurrentUser.mockResolvedValue(student)
    renderApp('/student')
    expect(await screen.findByText('student area')).toBeInTheDocument()
  })

  it('sends a student away from the coordinator area to their own dashboard', async () => {
    setToken('t')
    authApi.fetchCurrentUser.mockResolvedValue(student)
    renderApp('/coordinator')
    expect(await screen.findByText('student area')).toBeInTheDocument()
    expect(screen.queryByText('coordinator area')).not.toBeInTheDocument()
  })

  it('lets a coordinator into the coordinator area', async () => {
    setToken('t')
    authApi.fetchCurrentUser.mockResolvedValue(coordinator)
    renderApp('/coordinator')
    expect(await screen.findByText('coordinator area')).toBeInTheDocument()
  })

  it('discards an invalid stored token and shows login', async () => {
    setToken('stale')
    authApi.fetchCurrentUser.mockRejectedValue(new Error('401'))
    renderApp('/student')
    expect(await screen.findByRole('heading', { name: 'Log in' })).toBeInTheDocument()
    expect(getToken()).toBeNull()
  })
})

describe('login form', () => {
  it('shows the server error for wrong credentials and stays on the page', async () => {
    authApi.loginRequest.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid email or password.' } },
    })
    renderApp('/login')
    await userEvent.type(screen.getByLabelText('Email'), 'a@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpass1')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
    expect(getToken()).toBeNull()
  })

  it('explains a temporary lock after too many failed attempts', async () => {
    authApi.loginRequest.mockRejectedValue({
      response: { status: 429, data: { detail: 'Too many failed login attempts. Please try again in 15 minutes.' } },
    })
    renderApp('/login')
    await userEvent.type(screen.getByLabelText('Email'), 'a@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'wrongpass1')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Please try again in 15 minutes.')
    expect(getToken()).toBeNull()
  })

  it('stores the token and opens the right dashboard on success', async () => {
    authApi.loginRequest.mockResolvedValue({ access_token: 'tok', user: coordinator })
    renderApp('/login')
    await userEvent.type(screen.getByLabelText('Email'), 'c@x.com')
    await userEvent.type(screen.getByLabelText('Password'), 'Passw0rd1')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('coordinator area')).toBeInTheDocument()
    expect(getToken()).toBe('tok')
  })

  it('does not call the API when fields are empty', async () => {
    renderApp('/login')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/enter your email and password/i)
    expect(authApi.loginRequest).not.toHaveBeenCalled()
  })
})

describe('register form', () => {
  async function fill({ name = 'Asha Patil', email = 'a@x.com', pw = 'Passw0rd1', confirm = pw }) {
    await userEvent.type(screen.getByLabelText('Full name'), name)
    await userEvent.type(screen.getByLabelText('Email'), email)
    await userEvent.type(screen.getByLabelText('Password'), pw)
    await userEvent.type(screen.getByLabelText('Confirm password'), confirm)
    await userEvent.click(screen.getByRole('button', { name: 'Register' }))
  }

  it('blocks weak passwords and mismatches client-side', async () => {
    renderApp('/register')
    await fill({ pw: 'onlyletters', confirm: 'different' })
    expect(await screen.findByText(/at least one letter and one number/i)).toBeInTheDocument()
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(authApi.registerRequest).not.toHaveBeenCalled()
  })

  it('registers a student and lands on the student area', async () => {
    authApi.registerRequest.mockResolvedValue({ access_token: 'tok', user: student })
    renderApp('/register')
    await fill({})
    expect(await screen.findByText('student area')).toBeInTheDocument()
    expect(authApi.registerRequest).toHaveBeenCalledWith({
      full_name: 'Asha Patil',
      email: 'a@x.com',
      password: 'Passw0rd1',
    })
  })

  it('shows the duplicate-email error from the server', async () => {
    authApi.registerRequest.mockRejectedValue({
      response: { status: 409, data: { detail: 'An account with this email already exists.' } },
    })
    renderApp('/register')
    await fill({})
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/already exists/))
  })
})

describe('getErrorMessage', () => {
  it('handles network failure, validation lists, and server errors', () => {
    expect(getErrorMessage({})).toMatch(/cannot reach the server/i)
    expect(
      getErrorMessage({
        response: {
          status: 422,
          data: { detail: [{ loc: ['body', 'password'], msg: 'Value error, Too weak' }] },
        },
      }),
    ).toBe('password: Too weak')
    expect(getErrorMessage({ response: { status: 500, data: {} } })).toMatch(/server/i)
  })
})

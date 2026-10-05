import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import Navbar from '../components/Navbar'
import { AuthContext } from '../context/AuthContext'

const logout = vi.fn().mockResolvedValue(undefined)

function renderNav(user, path = '/student') {
  return render(
    <AuthContext.Provider value={{ user, logout, loading: false }}>
      <MemoryRouter initialEntries={[path]}>
        <Navbar />
        <Routes>
          <Route path="/login" element={<p>login page</p>} />
          <Route path="*" element={<p>some page</p>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

const student = { id: 1, full_name: 'Asha Patil', role: 'student' }
const coordinator = { id: 2, full_name: 'Dr. Rao', role: 'coordinator' }

describe('navbar', () => {
  it('offers register and log in to visitors', () => {
    renderNav(null, '/')
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/register')
    expect(screen.queryByRole('button', { name: 'Menu' })).not.toBeInTheDocument()
  })

  it('shows every student page, with the current one marked', () => {
    renderNav(student, '/student/jobs')
    const nav = within(screen.getByRole('navigation', { name: 'Main' }))
    const labels = nav.getAllByRole('link').map((a) => a.textContent).filter((t) => t !== 'PlaceGenie AI')
    expect(labels).toEqual(['Dashboard', 'Recommended', 'Jobs', 'Skill gap', 'Companies', 'Applications', 'Interviews', 'Assistant', 'Report', 'Resume', 'My profile'])
    expect(nav.getByRole('link', { name: 'Jobs' })).toHaveAttribute('aria-current', 'page')
    expect(nav.getByRole('link', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')
    expect(nav.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/student')
  })

  it('marks the dashboard only on the dashboard itself', () => {
    renderNav(student, '/student')
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows coordinators their own pages and none of the student pages', () => {
    renderNav(coordinator, '/coordinator/jobs')
    const nav = within(screen.getByRole('navigation', { name: 'Main' }))
    const labels = nav.getAllByRole('link').map((a) => a.textContent).filter((t) => t !== 'PlaceGenie AI')
    expect(labels).toEqual(['Dashboard', 'Students', 'Companies', 'Jobs', 'Applications', 'Progress', 'Analytics', 'Report'])
    expect(nav.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/coordinator')
    expect(nav.getByRole('link', { name: 'Jobs' })).toHaveAttribute('aria-current', 'page')
    expect(nav.queryByRole('link', { name: 'Recommended' })).not.toBeInTheDocument()
  })

  it('has a menu button that opens and closes the small-screen menu', async () => {
    renderNav(student)
    const button = screen.getByRole('button', { name: 'Menu' })
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(document.getElementById('mobile-menu')).toBeNull()
    await userEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    const menu = within(document.getElementById('mobile-menu'))
    expect(menu.getAllByRole('link')).toHaveLength(11)
    await userEvent.click(button)
    expect(document.getElementById('mobile-menu')).toBeNull()
  })

  it('closes the menu after choosing a page', async () => {
    renderNav(student)
    await userEvent.click(screen.getByRole('button', { name: 'Menu' }))
    await userEvent.click(within(document.getElementById('mobile-menu')).getByRole('link', { name: 'Resume' }))
    expect(document.getElementById('mobile-menu')).toBeNull()
  })

  it('logs out and returns to the login page', async () => {
    renderNav(student)
    await userEvent.click(screen.getAllByRole('button', { name: 'Log out' })[0])
    expect(logout).toHaveBeenCalled()
    expect(await screen.findByText('login page')).toBeInTheDocument()
  })
})

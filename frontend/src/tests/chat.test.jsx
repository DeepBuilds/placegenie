import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '../api/chat'
import Chatbot from '../pages/student/Chatbot'

vi.mock('../api/chat')

const info = (over = {}) => ({
  mode: 'guide', provider: null, max_message_chars: 100, disclaimer: 'PlaceGenie gives guidance only. It has no live information about companies.',
  starters: ['Which jobs am I eligible for?', 'Recommend jobs for me'], ...over,
})
const conv = (id, title, count = 2) => ({ id, title, created_at: '2026-10-01T10:00:00', updated_at: '2026-10-01T10:00:00', message_count: count })
const msg = (id, role, content, source = null) => ({ id, role, content, source, created_at: '2026-10-01T10:00:00' })
const reply = (text, source = 'guide', over = {}) => ({
  conversation: conv(7, 'How to prepare'), user_message: msg(1, 'user', 'q'), reply: msg(2, 'assistant', text, source),
  suggestions: [], ...over,
})

const renderChat = () => render(<MemoryRouter><Chatbot /></MemoryRouter>)
const box = () => screen.getByLabelText('Your message')

beforeEach(() => {
  vi.resetAllMocks()
  api.getChatInfo.mockResolvedValue(info())
  api.listConversations.mockResolvedValue([])
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

describe('opening the assistant', () => {
  it('shows a greeting, the mode, starter questions and the disclaimer', async () => {
    renderChat()
    expect(await screen.findByText('Built-in guide')).toBeInTheDocument()
    expect(screen.getByText(/No AI model is connected/)).toBeInTheDocument()
    expect(screen.getByText(/I'm the PlaceGenie assistant/)).toBeInTheDocument()
    const starters = within(screen.getByLabelText('Suggested questions'))
    expect(starters.getByRole('button', { name: 'Recommend jobs for me' })).toBeInTheDocument()
    expect(screen.getByText(/no live information about companies/)).toBeInTheDocument()
  })

  it('shows the AI mode when a model is connected', async () => {
    api.getChatInfo.mockResolvedValue(info({ mode: 'ai', provider: 'anthropic' }))
    renderChat()
    expect(await screen.findByText('AI assistant')).toBeInTheDocument()
    expect(screen.getByText(/answered by an AI model/)).toBeInTheDocument()
  })

  it('reports a problem loading the assistant', async () => {
    api.getChatInfo.mockRejectedValue({ response: { status: 500, data: {} } })
    renderChat()
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
  })
})

describe('sending messages', () => {
  it('shows the question and the answer, labelled with how it was produced', async () => {
    api.sendChatMessage.mockResolvedValue(reply('Think aloud and test with an example.', 'guide'))
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'How do I prepare for a technical interview?')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    const log = within(screen.getByRole('log', { name: 'Messages' }))
    expect(await log.findByText('Think aloud and test with an example.')).toBeInTheDocument()
    expect(api.sendChatMessage).toHaveBeenCalledWith('How do I prepare for a technical interview?', null)
    expect(log.getByText('Built-in placement guide')).toBeInTheDocument()
    expect(box()).toHaveValue('')
    expect(screen.queryByText(/I'm the PlaceGenie assistant/)).not.toBeInTheDocument()
  })

  it('shows a loading state while waiting and blocks double sending', async () => {
    let resolve
    api.sendChatMessage.mockReturnValue(new Promise((r) => { resolve = r }))
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'hello there')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('PlaceGenie is thinking…')).toBeInTheDocument()
    expect(screen.getByText('hello there')).toBeInTheDocument() // the question is shown straight away
    expect(box()).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    await act(async () => resolve(reply('Hi!', 'help')))
    await waitFor(() => expect(screen.queryByText('PlaceGenie is thinking…')).not.toBeInTheDocument())
    expect(api.sendChatMessage).toHaveBeenCalledTimes(1)
  })

  it('sends with Enter, and Shift+Enter adds a new line instead', async () => {
    api.sendChatMessage.mockResolvedValue(reply('ok'))
    renderChat()
    const input = await screen.findByLabelText('Your message')
    await userEvent.type(input, 'line one{Shift>}{Enter}{/Shift}line two')
    expect(api.sendChatMessage).not.toHaveBeenCalled()
    expect(input).toHaveValue('line one\nline two')
    await userEvent.type(input, '{Enter}')
    await waitFor(() => expect(api.sendChatMessage).toHaveBeenCalledWith('line one\nline two', null))
  })

  it('does not send empty or blank messages', async () => {
    renderChat()
    const send = await screen.findByRole('button', { name: 'Send' })
    expect(send).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Your message'), '    ')
    expect(send).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Your message'), '{Enter}')
    expect(api.sendChatMessage).not.toHaveBeenCalled()
  })

  it('refuses over-long messages before calling the server', async () => {
    renderChat()
    await userEvent.click(await screen.findByLabelText('Your message'))
    await userEvent.paste('x'.repeat(101))
    expect(screen.getByText('101 / 100')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Messages can be at most 100 characters.')
    expect(api.sendChatMessage).not.toHaveBeenCalled()
  })

  it('offers follow-up questions after a reply and sends one when clicked', async () => {
    api.sendChatMessage
      .mockResolvedValueOnce(reply('Eligible for 3 jobs.', 'data', { suggestions: ['Show my skill gap'] }))
      .mockResolvedValueOnce(reply('Here is your skill gap.', 'data'))
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Which jobs am I eligible for?' }))
    const chip = await screen.findByRole('button', { name: 'Show my skill gap' })
    await userEvent.click(chip)
    expect(await screen.findByText('Here is your skill gap.')).toBeInTheDocument()
    expect(api.sendChatMessage).toHaveBeenLastCalledWith('Show my skill gap', 7)
  })

  it('labels each kind of answer honestly', async () => {
    renderChat()
    const log = () => within(screen.getByRole('log', { name: 'Messages' }))
    const cases = [
      ['data', 'From your PlaceGenie data'], ['ai', 'AI-written: may contain mistakes'],
      ['fallback', 'AI unavailable: built-in guide used'], ['limit', 'Something I cannot know'],
    ]
    for (const [source, label] of cases) {
      api.sendChatMessage.mockResolvedValueOnce(reply(`answer ${source}`, source, { reply: msg(Math.random(), 'assistant', `answer ${source}`, source), user_message: msg(Math.random(), 'user', `q ${source}`) }))
      await userEvent.type(await screen.findByLabelText('Your message'), `q ${source}{Enter}`)
      expect(await log().findByText(`answer ${source}`)).toBeInTheDocument()
      expect(log().getByText(label)).toBeInTheDocument()
    }
  })
})

describe('errors', () => {
  it('shows the server message, keeps the typed text and removes the unsent bubble', async () => {
    api.sendChatMessage.mockRejectedValue({ response: { status: 429, data: { detail: 'You are sending messages too quickly. Please wait a few seconds and try again.' } } })
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'aptitude tips')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('too quickly')
    expect(box()).toHaveValue('aptitude tips')
    expect(within(screen.getByRole('log', { name: 'Messages' })).queryByText('aptitude tips')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled()
  })

  it('can retry after an error', async () => {
    api.sendChatMessage.mockRejectedValueOnce({ response: { status: 500, data: {} } }).mockResolvedValueOnce(reply('Second time lucky.'))
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'aptitude tips')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/something went wrong/i)
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText('Second time lucky.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('explains a network failure', async () => {
    api.sendChatMessage.mockRejectedValue({ message: 'Network Error' })
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'hello{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent(/cannot reach the server/i)
  })
})

describe('conversations', () => {
  const saved = [conv(3, 'Interview tips'), conv(4, 'Resume help')]

  beforeEach(() => {
    api.listConversations.mockResolvedValue(saved)
    api.getConversation.mockResolvedValue({
      ...conv(3, 'Interview tips', 2), messages: [msg(1, 'user', 'How to crack HR?'), msg(2, 'assistant', 'Use the STAR method.', 'guide')],
    })
  })

  it('lists saved conversations and opens one with its messages', async () => {
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Interview tips' }))
    expect(await screen.findByText('Use the STAR method.')).toBeInTheDocument()
    expect(screen.getByText('How to crack HR?')).toBeInTheDocument()
    expect(api.getConversation).toHaveBeenCalledWith(3)
    expect(screen.getByRole('button', { name: 'Interview tips' })).toHaveAttribute('aria-current', 'true')
  })

  it('continues the opened conversation instead of starting a new one', async () => {
    api.sendChatMessage.mockResolvedValue(reply('More on HR.', 'guide', { conversation: conv(3, 'Interview tips', 4) }))
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Interview tips' }))
    await screen.findByText('Use the STAR method.')
    await userEvent.type(screen.getByLabelText('Your message'), 'and weaknesses?{Enter}')
    await waitFor(() => expect(api.sendChatMessage).toHaveBeenCalledWith('and weaknesses?', 3))
    expect(await screen.findByText('More on HR.')).toBeInTheDocument()
    expect(screen.getByText('Use the STAR method.')).toBeInTheDocument() // history is still there
  })

  it('starts a fresh conversation with New chat', async () => {
    api.sendChatMessage.mockResolvedValue(reply('Fresh start.'))
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Interview tips' }))
    await screen.findByText('Use the STAR method.')
    await userEvent.click(screen.getByRole('button', { name: '+ New chat' }))
    expect(screen.queryByText('Use the STAR method.')).not.toBeInTheDocument()
    expect(screen.getByText(/I'm the PlaceGenie assistant/)).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Your message'), 'hello{Enter}')
    await waitFor(() => expect(api.sendChatMessage).toHaveBeenCalledWith('hello', null))
  })

  it('shows a message when a conversation cannot be opened', async () => {
    api.getConversation.mockRejectedValue({ response: { status: 404, data: { detail: 'Conversation not found.' } } })
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Interview tips' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Conversation not found.')
  })

  it('deletes a conversation only after confirmation', async () => {
    api.deleteConversation.mockResolvedValue({})
    const confirm = vi.spyOn(window, 'confirm')
    renderChat()
    const del = await screen.findByRole('button', { name: 'Delete conversation Interview tips' })
    confirm.mockReturnValueOnce(false)
    await userEvent.click(del)
    expect(api.deleteConversation).not.toHaveBeenCalled()
    confirm.mockReturnValueOnce(true)
    await userEvent.click(del)
    await waitFor(() => expect(api.deleteConversation).toHaveBeenCalledWith(3))
    expect(screen.queryByRole('button', { name: 'Interview tips' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Resume help' })).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('clearing the open conversation returns to a new chat', async () => {
    api.deleteConversation.mockResolvedValue({})
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderChat()
    await userEvent.click(await screen.findByRole('button', { name: 'Interview tips' }))
    await screen.findByText('Use the STAR method.')
    await userEvent.click(screen.getByRole('button', { name: 'Delete conversation Interview tips' }))
    await waitFor(() => expect(screen.queryByText('Use the STAR method.')).not.toBeInTheDocument())
    expect(screen.getByText(/I'm the PlaceGenie assistant/)).toBeInTheDocument()
    confirm.mockRestore()
  })

  it('clears the whole history after confirmation', async () => {
    api.deleteAllConversations.mockResolvedValue({})
    const confirm = vi.spyOn(window, 'confirm')
    renderChat()
    const clear = await screen.findByRole('button', { name: 'Clear all history' })
    confirm.mockReturnValueOnce(false)
    await userEvent.click(clear)
    expect(api.deleteAllConversations).not.toHaveBeenCalled()
    confirm.mockReturnValueOnce(true)
    await userEvent.click(clear)
    await waitFor(() => expect(api.deleteAllConversations).toHaveBeenCalled())
    expect(await screen.findByText('No saved conversations yet.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear all history' })).not.toBeInTheDocument()
    confirm.mockRestore()
  })

  it('ignores a late reply that arrives after the student started a new chat', async () => {
    let resolve
    api.sendChatMessage.mockReturnValue(new Promise((r) => { resolve = r }))
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), 'slow question{Enter}')
    await screen.findByText('PlaceGenie is thinking…')
    await userEvent.click(screen.getByRole('button', { name: '+ New chat' }))
    await act(async () => resolve(reply('A very late answer.')))
    expect(screen.queryByText('A very late answer.')).not.toBeInTheDocument()
    expect(screen.queryByText('slow question')).not.toBeInTheDocument()
  })

  it('shows an empty list message when there is no history', async () => {
    api.listConversations.mockResolvedValue([])
    renderChat()
    expect(await screen.findByText('No saved conversations yet.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear all history' })).not.toBeInTheDocument()
  })
})

describe('safety of what is shown', () => {
  it('renders message text as plain text, never as HTML', async () => {
    api.sendChatMessage.mockResolvedValue(reply('<img src=x onerror=alert(1)> done', 'ai'))
    renderChat()
    await userEvent.type(await screen.findByLabelText('Your message'), '<b>bold</b>{Enter}')
    expect(await screen.findByText('<img src=x onerror=alert(1)> done')).toBeInTheDocument()
    expect(document.querySelector('img')).toBeNull()
    expect(document.querySelector('b')).toBeNull()
  })
})

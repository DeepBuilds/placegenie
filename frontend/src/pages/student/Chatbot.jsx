import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deleteAllConversations,
  deleteConversation,
  getChatInfo,
  getConversation,
  listConversations,
  sendChatMessage,
} from '../../api/chat'
import MessageBubble from '../../components/chat/MessageBubble'
import { secondaryButton } from '../../components/profile/Section'
import { getErrorMessage } from '../../utils/errors'

const GREETING = {
  id: 'welcome',
  role: 'assistant',
  source: 'help',
  content:
    "Hi! I'm the PlaceGenie assistant. Ask me about your eligibility, jobs that suit you, your applications and interviews, your resume, or how to prepare for placements.",
}

export default function Chatbot() {
  const [info, setInfo] = useState(null)
  const [conversations, setConversations] = useState([])
  const [activeId, setActiveId] = useState(null) // null = a new conversation that is not saved yet
  const [messages, setMessages] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [loadingChat, setLoadingChat] = useState(false)
  const endRef = useRef(null)
  const requestId = useRef(0) // ignores a slow response that arrives after the student switched conversations

  useEffect(() => {
    let cancelled = false
    Promise.all([getChatInfo(), listConversations()])
      .then(([i, list]) => {
        if (cancelled) return
        setInfo(i)
        setConversations(list)
      })
      .catch((err) => !cancelled && setLoadError(getErrorMessage(err)))
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  const refreshList = useCallback(() => listConversations().then(setConversations).catch(() => {}), [])

  const startNew = () => {
    requestId.current += 1
    setActiveId(null)
    setMessages([])
    setSuggestions([])
    setError('')
  }

  const open = async (id) => {
    if (id === activeId || sending) return
    const mine = ++requestId.current
    setLoadingChat(true)
    setError('')
    try {
      const detail = await getConversation(id)
      if (mine !== requestId.current) return
      setActiveId(id)
      setMessages(detail.messages)
      setSuggestions([])
    } catch (err) {
      if (mine === requestId.current) setError(getErrorMessage(err))
    } finally {
      if (mine === requestId.current) setLoadingChat(false)
    }
  }

  const send = async (text) => {
    const message = (text ?? draft).trim()
    if (!message || sending) return
    if (info && message.length > info.max_message_chars) {
      setError(`Messages can be at most ${info.max_message_chars} characters.`)
      return
    }
    setError('')
    setSending(true)
    setSuggestions([])
    const mine = ++requestId.current
    const pending = { id: `pending-${mine}`, role: 'user', content: message, pending: true }
    setMessages((m) => [...m, pending])
    setDraft('')
    try {
      const res = await sendChatMessage(message, activeId)
      if (mine !== requestId.current) return
      setActiveId(res.conversation.id)
      setMessages((m) => [...m.filter((x) => x.id !== pending.id), res.user_message, res.reply])
      setSuggestions(res.suggestions)
      refreshList()
    } catch (err) {
      if (mine !== requestId.current) return
      setMessages((m) => m.filter((x) => x.id !== pending.id))
      setDraft(message) // keep what the student typed so nothing is lost
      setError(getErrorMessage(err))
    } finally {
      if (mine === requestId.current) setSending(false)
    }
  }

  const remove = async (c) => {
    if (!window.confirm(`Delete the conversation "${c.title}"?`)) return
    try {
      await deleteConversation(c.id)
      setConversations((list) => list.filter((x) => x.id !== c.id))
      if (c.id === activeId) startNew()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const clearAll = async () => {
    if (!window.confirm('Delete your entire chat history? This cannot be undone.')) return
    try {
      await deleteAllConversations()
      setConversations([])
      startNew()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const empty = messages.length === 0
  const starters = empty ? info?.starters ?? [] : suggestions
  const limit = info?.max_message_chars ?? 1000

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Placement assistant</h1>
          {info && (
            <p className="text-sm text-slate-600">
              <span className={`mr-2 rounded-full px-2.5 py-0.5 text-xs font-semibold ${info.mode === 'ai' ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700'}`}>
                {info.mode === 'ai' ? 'AI assistant' : 'Built-in guide'}
              </span>
              {info.mode === 'ai'
                ? 'General questions are answered by an AI model; your own data comes straight from PlaceGenie.'
                : 'No AI model is connected: answers come from the built-in placement guide and your PlaceGenie data.'}
            </p>
          )}
        </div>
      </div>
      {loadError && <p role="alert" className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{loadError}</p>}

      <div className="mt-4 flex flex-col gap-4 md:flex-row">
        <aside className="md:w-64 md:shrink-0" aria-label="Conversations">
          <button type="button" onClick={startNew} className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            + New chat
          </button>
          <ul className="mt-3 max-h-64 space-y-1 overflow-y-auto md:max-h-[28rem]">
            {conversations.length === 0 && <li className="px-1 text-sm text-slate-500">No saved conversations yet.</li>}
            {conversations.map((c) => (
              <li key={c.id} className={`group flex items-center gap-1 rounded-md ${c.id === activeId ? 'bg-indigo-50' : 'hover:bg-slate-100'}`}>
                <button type="button" onClick={() => open(c.id)} aria-current={c.id === activeId ? 'true' : undefined}
                  className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm text-slate-800">
                  {c.title}
                </button>
                <button type="button" onClick={() => remove(c)} aria-label={`Delete conversation ${c.title}`}
                  className="rounded px-2 py-1 text-slate-400 hover:bg-red-50 hover:text-red-600">
                  ×
                </button>
              </li>
            ))}
          </ul>
          {conversations.length > 0 && (
            <button type="button" onClick={clearAll} className={`${secondaryButton} mt-3 w-full`}>Clear all history</button>
          )}
        </aside>

        <section className="flex min-h-[28rem] flex-1 flex-col rounded-lg border border-slate-200 bg-slate-50 shadow-sm" aria-label="Chat">
          <ul role="log" aria-live="polite" aria-label="Messages" className="flex-1 space-y-3 overflow-y-auto p-4 md:max-h-[28rem]">
            {loadingChat && <li className="text-center text-sm text-slate-500">Loading conversation…</li>}
            {empty && !loadingChat && <MessageBubble message={GREETING} />}
            {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
            {sending && (
              <li className="flex justify-start" role="status">
                <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-500">
                  PlaceGenie is thinking…
                </div>
              </li>
            )}
            <li ref={endRef} aria-hidden="true" />
          </ul>

          {starters.length > 0 && !sending && (
            <div className="flex flex-wrap gap-2 px-4 pb-2" aria-label="Suggested questions">
              {starters.map((s) => (
                <button key={s} type="button" onClick={() => send(s)}
                  className="rounded-full border border-indigo-200 bg-white px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-50">
                  {s}
                </button>
              ))}
            </div>
          )}

          {error && (
            <p role="alert" className="mx-4 mb-2 rounded-md bg-red-50 p-2.5 text-sm text-red-700">{error}</p>
          )}

          <form onSubmit={(e) => { e.preventDefault(); send() }} className="border-t border-slate-200 bg-white p-3">
            <label htmlFor="chat-input" className="sr-only">Your message</label>
            <div className="flex items-end gap-2">
              <textarea id="chat-input" rows={2} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={onKeyDown}
                disabled={sending} placeholder="Ask about placements, e.g. “Am I eligible for the Data Analyst job?”"
                className="block w-full resize-none rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-slate-100" />
              <button type="submit" disabled={sending || !draft.trim()}
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                Send
              </button>
            </div>
            <p className={`mt-1 text-right text-xs ${draft.length > limit ? 'text-red-600' : 'text-slate-400'}`}>{draft.length} / {limit}</p>
          </form>
        </section>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        {info?.disclaimer ?? 'PlaceGenie gives guidance only and has no live information about companies or hiring decisions.'}
      </p>
    </div>
  )
}

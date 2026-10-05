// How an assistant reply was produced, shown under it so students know how far to trust it.
const SOURCES = {
  data: { label: 'From your PlaceGenie data', cls: 'text-emerald-700' },
  guide: { label: 'Built-in placement guide', cls: 'text-slate-500' },
  ai: { label: 'AI-written: may contain mistakes', cls: 'text-indigo-700' },
  fallback: { label: 'AI unavailable: built-in guide used', cls: 'text-amber-700' },
  limit: { label: 'Something I cannot know', cls: 'text-amber-700' },
  help: { label: 'PlaceGenie assistant', cls: 'text-slate-500' },
}

export default function MessageBubble({ message }) {
  const mine = message.role === 'user'
  const source = !mine && SOURCES[message.source]
  return (
    <li className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
          mine ? 'rounded-br-sm bg-indigo-600 text-white' : 'rounded-bl-sm border border-slate-200 bg-white text-slate-800'
        } ${message.pending ? 'opacity-70' : ''}`}
      >
        <p className="whitespace-pre-line break-words">{message.content}</p>
        {source && <p className={`mt-1.5 text-xs ${source.cls}`}>{source.label}</p>}
      </div>
    </li>
  )
}

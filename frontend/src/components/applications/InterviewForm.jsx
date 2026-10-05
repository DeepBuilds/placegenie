import { useState } from 'react'
import { Field, inputClass, primaryButton, secondaryButton } from '../profile/Section'
import { OUTCOMES, STAGES, fromInputValue, toInputValue, validateInterview } from '../../utils/applications'

/**
 * Add or edit an interview. `applications` (optional) adds an "Application" dropdown for the
 * tracker page; `initial` pre-fills the fields when editing.
 */
export default function InterviewForm({ initial, applications, onSubmit, onCancel, submitLabel = 'Save interview', idPrefix = 'iv' }) {
  const [form, setForm] = useState({
    application_id: applications?.[0]?.id ?? '',
    stage: initial?.stage ?? 'technical_interview',
    scheduled_at: toInputValue(initial?.scheduled_at),
    outcome: initial?.outcome ?? 'pending',
    notes: initial?.notes ?? '',
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    const found = validateInterview(form)
    if (applications && !form.application_id) found.application_id = 'Choose the application this interview belongs to.'
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    try {
      await onSubmit({
        application_id: Number(form.application_id) || undefined,
        stage: form.stage,
        scheduled_at: fromInputValue(form.scheduled_at),
        outcome: form.outcome,
        notes: form.notes.trim() || null,
      })
    } finally {
      setSaving(false)
    }
  }

  const id = (name) => `${idPrefix}-${name}`
  return (
    <form onSubmit={submit} noValidate className="grid gap-3 rounded-md bg-slate-50 p-4 sm:grid-cols-2">
      {applications && (
        <Field label="Application" id={id('application')} error={errors.application_id} className="sm:col-span-2">
          <select id={id('application')} className={inputClass} value={form.application_id} onChange={set('application_id')}>
            <option value="">Choose…</option>
            {applications.map((a) => (
              <option key={a.id} value={a.id}>{a.job.title} · {a.job.company}</option>
            ))}
          </select>
        </Field>
      )}
      <Field label="Stage" id={id('stage')}>
        <select id={id('stage')} className={inputClass} value={form.stage} onChange={set('stage')}>
          {Object.entries(STAGES).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </Field>
      <Field label="Date and time" id={id('date')} error={errors.scheduled_at}>
        <input id={id('date')} type="datetime-local" className={inputClass} value={form.scheduled_at} onChange={set('scheduled_at')} />
      </Field>
      <Field label="Result" id={id('outcome')}>
        <select id={id('outcome')} className={inputClass} value={form.outcome} onChange={set('outcome')}>
          {Object.entries(OUTCOMES).map(([value, o]) => (
            <option key={value} value={value}>{o.label}</option>
          ))}
        </select>
      </Field>
      <Field label="Notes" id={id('notes')} error={errors.notes} className="sm:col-span-2">
        <textarea id={id('notes')} rows={3} maxLength={2100} className={inputClass} value={form.notes} onChange={set('notes')}
          placeholder="Venue or meeting link, topics, questions asked, how it went…" />
      </Field>
      <div className="flex gap-2 sm:col-span-2">
        <button type="submit" disabled={saving} className={primaryButton}>{saving ? 'Saving…' : submitLabel}</button>
        {onCancel && <button type="button" onClick={onCancel} className={secondaryButton}>Cancel</button>}
      </div>
    </form>
  )
}

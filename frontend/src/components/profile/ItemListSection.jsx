import { useState } from 'react'
import { addItem, removeItem } from '../../api/profile'
import { getErrorMessage } from '../../utils/errors'
import Section, { Field, inputClass, primaryButton, secondaryButton } from './Section'

/**
 * Generic add / view / remove list used for certifications, projects and experience.
 * `fields` describes the add-form; `renderItem` describes how a saved item is shown.
 */
export default function ItemListSection({
  kind, title, subtitle, emptyText, addLabel, fields, items, renderItem, onSaved, notify,
}) {
  const blank = Object.fromEntries(fields.map((f) => [f.name, '']))
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(blank)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const found = {}
    for (const f of fields) {
      if (f.required && !form[f.name].trim()) found[f.name] = `${f.label} is required.`
    }
    setErrors(found)
    if (Object.keys(found).length) return

    const payload = Object.fromEntries(
      fields.map((f) => [f.name, form[f.name].trim() === '' ? null : form[f.name].trim()]),
    )
    setBusy(true)
    try {
      onSaved(await addItem(kind, payload))
      notify('success', `${addLabel.replace('Add ', '')} added.`)
      setForm(blank)
      setOpen(false)
    } catch (err) {
      notify('error', getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    setBusy(true)
    try {
      onSaved(await removeItem(kind, id))
      notify('success', 'Removed.')
    } catch (err) {
      notify('error', getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section title={title} subtitle={subtitle}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">{emptyText}</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {items.map((item) => (
            <li key={item.id} className="flex items-start justify-between gap-3 py-3">
              <div className="min-w-0 text-sm">{renderItem(item)}</div>
              <button
                type="button"
                disabled={busy}
                onClick={() => remove(item.id)}
                aria-label={`Remove ${item.name || item.title || item.organization}`}
                className={secondaryButton}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {open ? (
        <form onSubmit={submit} noValidate className="mt-4 grid gap-3 rounded-md bg-slate-50 p-4 sm:grid-cols-2">
          {fields.map((f) => (
            <Field
              key={f.name}
              label={f.label + (f.required ? ' *' : '')}
              id={`${kind}-${f.name}`}
              error={errors[f.name]}
              className={f.wide ? 'sm:col-span-2' : ''}
            >
              {f.textarea ? (
                <textarea
                  id={`${kind}-${f.name}`}
                  rows={3}
                  className={inputClass}
                  value={form[f.name]}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                />
              ) : (
                <input
                  id={`${kind}-${f.name}`}
                  type={f.type || 'text'}
                  placeholder={f.placeholder}
                  className={inputClass}
                  value={form[f.name]}
                  onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}
                />
              )}
            </Field>
          ))}
          <div className="flex gap-2 sm:col-span-2">
            <button type="submit" disabled={busy} className={primaryButton}>
              {busy ? 'Saving…' : 'Save'}
            </button>
            <button type="button" className={secondaryButton} onClick={() => { setOpen(false); setErrors({}) }}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className={`${secondaryButton} mt-4`} onClick={() => setOpen(true)}>
          + {addLabel}
        </button>
      )}
    </Section>
  )
}

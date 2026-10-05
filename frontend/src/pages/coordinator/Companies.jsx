import { useState } from 'react'
import { createCompany, deleteCompany, updateCompany } from '../../api/admin'
import { getCompanies } from '../../api/jobs'
import { ErrorNote, PageHeader } from '../../components/coordinator/Parts'
import Section, { Field, inputClass, primaryButton, secondaryButton } from '../../components/profile/Section'
import { useLoad } from '../../hooks/useLoad'
import { validateCompany } from '../../utils/companyForm'
import { getErrorMessage } from '../../utils/errors'

const BLANK = { name: '', industry: '', website: '', location: '', description: '' }

function CompanyForm({ company, onSaved, onCancel }) {
  const [values, setValues] = useState(company ? Object.fromEntries(Object.keys(BLANK).map((k) => [k, company[k] ?? ''])) : BLANK)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    const found = validateCompany(values)
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    setServerError('')
    const payload = Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim() || null]))
    try {
      if (company) await updateCompany(company.id, payload)
      else await createCompany(payload)
      onSaved()
    } catch (err) {
      setServerError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title={company ? `Edit ${company.name}` : 'Add a company'}>
      <form onSubmit={submit} noValidate className="grid gap-4 md:grid-cols-2">
        <Field label="Company name" id="c-name" error={errors.name}>
          <input id="c-name" value={values.name} onChange={set('name')} maxLength={150} className={inputClass} aria-invalid={errors.name ? 'true' : undefined} />
        </Field>
        <Field label="Industry" id="c-industry"><input id="c-industry" value={values.industry} onChange={set('industry')} maxLength={100} className={inputClass} /></Field>
        <Field label="Website" id="c-website" error={errors.website}>
          <input id="c-website" value={values.website} onChange={set('website')} placeholder="https://" maxLength={255} className={inputClass} aria-invalid={errors.website ? 'true' : undefined} />
        </Field>
        <Field label="Location" id="c-location"><input id="c-location" value={values.location} onChange={set('location')} maxLength={100} className={inputClass} /></Field>
        <Field label="Description" id="c-description" className="md:col-span-2">
          <textarea id="c-description" rows={3} value={values.description} onChange={set('description')} maxLength={3000} className={inputClass} />
        </Field>
        <div className="flex items-center gap-3 md:col-span-2">
          <button type="submit" disabled={saving} className={primaryButton}>{saving ? 'Saving…' : company ? 'Save changes' : 'Add company'}</button>
          <button type="button" onClick={onCancel} className={secondaryButton}>Cancel</button>
          {serverError && <span role="alert" className="text-sm text-red-600">{serverError}</span>}
        </div>
      </form>
    </Section>
  )
}

export default function Companies() {
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const [editing, setEditing] = useState(null) // null | 'new' | company
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const { data, error, loading, reload } = useLoad(() => getCompanies({ q: search, limit: 100 }), search)

  const remove = async (c) => {
    if (!window.confirm(`Delete ${c.name}? This cannot be undone.`)) return
    setActionError('')
    setNotice('')
    try {
      await deleteCompany(c.id)
      setNotice(`${c.name} was deleted.`)
      reload()
    } catch (err) {
      setActionError(getErrorMessage(err))
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader title="Companies" subtitle="Companies that recruit from the college.">
        <button type="button" className={primaryButton} onClick={() => setEditing('new')}>Add company</button>
      </PageHeader>

      {editing && (
        <div className="mt-5">
          <CompanyForm company={editing === 'new' ? null : editing} onCancel={() => setEditing(null)}
            onSaved={() => { setNotice(editing === 'new' ? 'Company added.' : 'Company updated.'); setEditing(null); reload() }} />
        </div>
      )}

      <form className="mt-5 flex gap-2" role="search" onSubmit={(e) => { e.preventDefault(); setSearch(q.trim()) }}>
        <input type="search" aria-label="Search companies" placeholder="Search by name or industry" value={q} maxLength={100} onChange={(e) => setQ(e.target.value)} className={`${inputClass} mt-0`} />
        <button type="submit" className={primaryButton}>Search</button>
      </form>

      <div className="mt-4 space-y-3" aria-live="polite">
        {notice && <p role="status" className="rounded-md bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p>}
        <ErrorNote>{actionError}</ErrorNote>
        <ErrorNote>{error}</ErrorNote>
        {loading && !data && <p className="py-10 text-center text-slate-500">Loading companies…</p>}
        {data && data.items.length === 0 && <p className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">No companies found.</p>}
        {data && data.items.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-left text-sm">
              <caption className="sr-only">Companies</caption>
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>{['Company', 'Industry', 'Location', 'Open jobs', 'Actions'].map((h) => <th key={h} scope="col" className="px-4 py-2">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.items.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2">
                      <p className="font-medium text-slate-900">{c.name}</p>
                      {c.website && <a href={c.website} target="_blank" rel="noreferrer noopener" className="text-xs text-indigo-600 hover:underline">{c.website}</a>}
                    </td>
                    <td className="px-4 py-2">{c.industry ?? '—'}</td>
                    <td className="px-4 py-2">{c.location ?? '—'}</td>
                    <td className="px-4 py-2">{c.open_jobs}</td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2">
                        <button type="button" className={secondaryButton} onClick={() => setEditing(c)} aria-label={`Edit ${c.name}`}>Edit</button>
                        <button type="button" className={`${secondaryButton} text-red-700`} onClick={() => remove(c)} aria-label={`Delete ${c.name}`}>Delete</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

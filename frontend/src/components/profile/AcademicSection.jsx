import { useState } from 'react'
import { saveProfile } from '../../api/profile'
import { getErrorMessage } from '../../utils/errors'
import { basicPayload, toNumberOrNull, validateAcademic } from '../../utils/profile'
import Section, { Field, inputClass, primaryButton } from './Section'

const fromProfile = (p) => ({
  full_name: p.full_name ?? '',
  phone: p.phone ?? '',
  college: p.college ?? '',
  branch_id: p.branch?.id ?? '',
  year: p.year ?? '',
  semester: p.semester ?? '',
  cgpa: p.cgpa ?? '',
  backlogs: p.backlogs ?? 0,
})

export default function AcademicSection({ profile, branches, onSaved, notify }) {
  const [form, setForm] = useState(() => fromProfile(profile))
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const found = validateAcademic(form)
    setErrors(found)
    if (Object.keys(found).length) {
      notify('error', 'Please fix the highlighted fields.')
      return
    }
    setSaving(true)
    try {
      const updated = await saveProfile(
        basicPayload(profile, {
          full_name: form.full_name.trim(),
          phone: form.phone.trim() || null,
          college: form.college.trim() || null,
          branch_id: toNumberOrNull(form.branch_id),
          year: toNumberOrNull(form.year),
          semester: toNumberOrNull(form.semester),
          cgpa: toNumberOrNull(form.cgpa),
          backlogs: toNumberOrNull(form.backlogs) ?? 0,
        }),
      )
      onSaved(updated)
      notify('success', 'Personal and academic details saved.')
    } catch (err) {
      notify('error', getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Personal & academic details" subtitle="Used for eligibility checks and recommendations.">
      <form onSubmit={handleSubmit} noValidate className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name" id="full_name" error={errors.full_name}>
          <input id="full_name" className={inputClass} value={form.full_name} onChange={set('full_name')} />
        </Field>
        <Field label="Email (from your account)" id="email">
          <input id="email" className={`${inputClass} bg-slate-100`} value={profile.email} readOnly />
        </Field>
        <Field label="Phone" id="phone" error={errors.phone}>
          <input id="phone" className={inputClass} placeholder="+91 98765 43210" value={form.phone} onChange={set('phone')} />
        </Field>
        <Field label="College" id="college">
          <input id="college" className={inputClass} value={form.college} onChange={set('college')} />
        </Field>
        <Field label="Branch / department" id="branch_id">
          <select id="branch_id" className={inputClass} value={form.branch_id} onChange={set('branch_id')}>
            <option value="">Select branch</option>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Year" id="year" error={errors.year}>
            <select id="year" className={inputClass} value={form.year} onChange={set('year')}>
              <option value="">–</option>
              {[1, 2, 3, 4].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Semester" id="semester" error={errors.semester}>
            <select id="semester" className={inputClass} value={form.semester} onChange={set('semester')}>
              <option value="">–</option>
              {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <Field label="CGPA (out of 10)" id="cgpa" error={errors.cgpa}>
          <input id="cgpa" type="number" step="0.01" min="0" max="10" className={inputClass} value={form.cgpa} onChange={set('cgpa')} />
        </Field>
        <Field label="Active backlogs" id="backlogs" error={errors.backlogs}>
          <input id="backlogs" type="number" min="0" className={inputClass} value={form.backlogs} onChange={set('backlogs')} />
        </Field>
        <div className="sm:col-span-2">
          <button type="submit" disabled={saving} className={primaryButton}>
            {saving ? 'Saving…' : 'Save details'}
          </button>
        </div>
      </form>
    </Section>
  )
}

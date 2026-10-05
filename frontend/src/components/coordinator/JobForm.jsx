import { useState } from 'react'
import { createJob, updateJob } from '../../api/admin'
import { getErrorMessage } from '../../utils/errors'
import { formToPayload, jobToForm, validateJob } from '../../utils/jobForm'
import { JOB_TYPE_LABELS } from '../../utils/jobs'
import Section, { Field, inputClass, primaryButton, secondaryButton } from '../profile/Section'

const TYPES = Object.entries(JOB_TYPE_LABELS)
const IMPORTANCE = [['required', 'Required'], ['preferred', 'Preferred']]

export default function JobForm({ job, companies, skills, branches, roles, onSaved, onCancel }) {
  const [values, setValues] = useState(() => jobToForm(job))
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [saving, setSaving] = useState(false)
  const set = (k) => (e) => setValues((v) => ({ ...v, [k]: e.target.value }))
  const setSkill = (i, k, value) => setValues((v) => ({ ...v, skills: v.skills.map((s, n) => (n === i ? { ...s, [k]: value } : s)) }))
  const toggleBranch = (id) =>
    setValues((v) => ({ ...v, allowed_branch_ids: v.allowed_branch_ids.includes(id) ? v.allowed_branch_ids.filter((b) => b !== id) : [...v.allowed_branch_ids, id] }))

  const submit = async (e) => {
    e.preventDefault()
    const found = validateJob(values)
    setErrors(found)
    if (Object.keys(found).length) return
    setSaving(true)
    setServerError('')
    try {
      if (job) await updateJob(job.id, formToPayload(values))
      else await createJob(formToPayload(values))
      onSaved()
    } catch (err) {
      setServerError(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title={job ? `Edit ${job.title}` : 'Add a job'} subtitle="Eligibility and recommendations for students are computed from these requirements.">
      <form onSubmit={submit} noValidate className="grid gap-4 md:grid-cols-3">
        <Field label="Company" id="j-company" error={errors.company_id}>
          <select id="j-company" value={values.company_id} onChange={set('company_id')} className={inputClass}>
            <option value="">Choose a company</option>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </Field>
        <Field label="Job title" id="j-title" error={errors.title} className="md:col-span-2">
          <input id="j-title" value={values.title} onChange={set('title')} maxLength={150} className={inputClass} aria-invalid={errors.title ? 'true' : undefined} />
        </Field>
        <Field label="Role" id="j-role">
          <select id="j-role" value={values.role_id} onChange={set('role_id')} className={inputClass}>
            <option value="">No specific role</option>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </Field>
        <Field label="Location" id="j-location"><input id="j-location" value={values.location} onChange={set('location')} maxLength={100} className={inputClass} /></Field>
        <Field label="Job type" id="j-type">
          <select id="j-type" value={values.job_type} onChange={set('job_type')} className={inputClass}>
            {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </Field>
        <Field label="Minimum CGPA" id="j-cgpa" error={errors.min_cgpa}>
          <input id="j-cgpa" type="number" step="0.1" min="0" max="10" value={values.min_cgpa} onChange={set('min_cgpa')} className={inputClass} />
        </Field>
        <Field label="Maximum backlogs (empty = no limit)" id="j-backlogs" error={errors.max_backlogs}>
          <input id="j-backlogs" type="number" min="0" value={values.max_backlogs} onChange={set('max_backlogs')} className={inputClass} />
        </Field>
        <Field label="Minimum experience (months)" id="j-exp" error={errors.min_experience_months}>
          <input id="j-exp" type="number" min="0" max="120" value={values.min_experience_months} onChange={set('min_experience_months')} className={inputClass} />
        </Field>
        <Field label="Application deadline" id="j-deadline"><input id="j-deadline" type="date" value={values.deadline} onChange={set('deadline')} className={inputClass} /></Field>
        <Field label="Status" id="j-status">
          <select id="j-status" value={values.status} onChange={set('status')} className={inputClass}>
            <option value="open">Open</option><option value="closed">Closed</option>
          </select>
        </Field>
        <Field label="Description" id="j-description" className="md:col-span-3">
          <textarea id="j-description" rows={3} value={values.description} onChange={set('description')} maxLength={5000} className={inputClass} />
        </Field>

        <fieldset className="md:col-span-3">
          <legend className="text-sm font-medium text-slate-700">Skills</legend>
          {values.skills.map((s, i) => (
            <div key={i} className="mt-2 flex flex-wrap items-center gap-2">
              <select aria-label={`Skill ${i + 1}`} value={s.skill_id} onChange={(e) => setSkill(i, 'skill_id', e.target.value)} className={`${inputClass} mt-0 w-56`}>
                <option value="">Choose a skill</option>
                {skills.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
              </select>
              <select aria-label={`Importance of skill ${i + 1}`} value={s.importance} onChange={(e) => setSkill(i, 'importance', e.target.value)} className={`${inputClass} mt-0 w-36`}>
                {IMPORTANCE.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <select aria-label={`Weight of skill ${i + 1}`} value={s.weight} onChange={(e) => setSkill(i, 'weight', e.target.value)} className={`${inputClass} mt-0 w-32`}>
                {[1, 2, 3, 4, 5].map((w) => <option key={w} value={w}>Weight {w}</option>)}
              </select>
              <button type="button" className={secondaryButton} onClick={() => setValues((v) => ({ ...v, skills: v.skills.filter((_, n) => n !== i) }))}>Remove</button>
            </div>
          ))}
          {errors.skills && <p className="mt-1 text-sm text-red-600">{errors.skills}</p>}
          <button type="button" className={`${secondaryButton} mt-2`} onClick={() => setValues((v) => ({ ...v, skills: [...v.skills, { skill_id: '', importance: 'required', weight: '3' }] }))}>Add a skill</button>
        </fieldset>

        <fieldset className="md:col-span-3">
          <legend className="text-sm font-medium text-slate-700">Allowed branches (none ticked = every branch)</legend>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
            {branches.map((b) => (
              <label key={b.id} className="flex items-center gap-1.5 text-sm text-slate-700">
                <input type="checkbox" checked={values.allowed_branch_ids.includes(b.id)} onChange={() => toggleBranch(b.id)} />
                {b.name}
              </label>
            ))}
          </div>
        </fieldset>

        <Field label="Required certifications (separate with commas)" id="j-certs" className="md:col-span-3">
          <input id="j-certs" value={values.required_certifications} onChange={set('required_certifications')} className={inputClass} />
        </Field>

        <div className="flex items-center gap-3 md:col-span-3">
          <button type="submit" disabled={saving} className={primaryButton}>{saving ? 'Saving…' : job ? 'Save changes' : 'Add job'}</button>
          <button type="button" onClick={onCancel} className={secondaryButton}>Cancel</button>
          {serverError && <span role="alert" className="text-sm text-red-600">{serverError}</span>}
        </div>
      </form>
    </Section>
  )
}

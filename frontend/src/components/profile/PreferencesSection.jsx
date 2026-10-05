import { useState } from 'react'
import { savePreferences, saveProfile } from '../../api/profile'
import { getErrorMessage } from '../../utils/errors'
import { basicPayload } from '../../utils/profile'
import Section, { Field, inputClass, primaryButton } from './Section'

const JOB_TYPES = [
  ['', 'No preference'],
  ['full_time', 'Full time'],
  ['internship', 'Internship'],
  ['contract', 'Contract'],
]

export default function PreferencesSection({ profile, jobRoles, onSaved, notify }) {
  const [interests, setInterests] = useState(profile.interests ?? '')
  const [location, setLocation] = useState(profile.preferred_location ?? '')
  const [jobType, setJobType] = useState(profile.preferred_job_type ?? '')
  const [roleIds, setRoleIds] = useState(() => new Set(profile.preferred_roles.map((r) => r.id)))
  const [saving, setSaving] = useState(false)

  const toggleRole = (id) =>
    setRoleIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (roleIds.size > 10) {
      notify('error', 'Choose at most 10 preferred roles.')
      return
    }
    setSaving(true)
    try {
      await saveProfile(
        basicPayload(profile, {
          interests: interests.trim() || null,
          preferred_location: location.trim() || null,
          preferred_job_type: jobType || null,
        }),
      )
      const updated = await savePreferences({
        preferred_role_ids: [...roleIds],
        preferred_company_ids: profile.preferred_companies.map((c) => c.id),
      })
      onSaved(updated)
      notify('success', 'Preferences saved.')
    } catch (err) {
      notify('error', getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Section title="Interests & placement preferences" subtitle="Helps rank job recommendations.">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Interests" id="interests">
          <textarea
            id="interests"
            rows={2}
            maxLength={1000}
            className={inputClass}
            placeholder="e.g. web development, data analysis, cloud"
            value={interests}
            onChange={(e) => setInterests(e.target.value)}
          />
        </Field>

        <fieldset>
          <legend className="text-sm font-medium text-slate-700">Preferred job roles</legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {jobRoles.map((r) => (
              <label key={r.id} className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={roleIds.has(r.id)}
                  onChange={() => toggleRole(r.id)}
                  className="h-4 w-4 rounded border-slate-300 text-indigo-600"
                />
                {r.name}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Preferred location" id="preferred_location">
            <input id="preferred_location" className={inputClass} placeholder="e.g. Pune, Remote" value={location} onChange={(e) => setLocation(e.target.value)} />
          </Field>
          <Field label="Preferred job type" id="preferred_job_type">
            <select id="preferred_job_type" className={inputClass} value={jobType} onChange={(e) => setJobType(e.target.value)}>
              {JOB_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <button type="submit" disabled={saving} className={primaryButton}>
          {saving ? 'Saving…' : 'Save preferences'}
        </button>
      </form>
    </Section>
  )
}

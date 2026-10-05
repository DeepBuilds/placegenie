import { useState } from 'react'
import { saveSkills } from '../../api/profile'
import { getErrorMessage } from '../../utils/errors'
import Section, { inputClass, primaryButton } from './Section'

const LEVELS = ['beginner', 'intermediate', 'advanced']

export default function SkillsSection({ profile, allSkills, onSaved, notify }) {
  const [newSkill, setNewSkill] = useState('')
  const [level, setLevel] = useState('beginner')
  const [busy, setBusy] = useState(false)

  const owned = new Set(profile.skills.map((s) => s.skill_id))
  const available = allSkills.filter((s) => !owned.has(s.id))
  const toEntries = (list) => list.map((s) => ({ skill_id: s.skill_id, proficiency: s.proficiency }))

  // Every change sends the full list (the API replaces the whole skill set).
  const persist = async (entries, okMessage) => {
    setBusy(true)
    try {
      onSaved(await saveSkills(entries))
      notify('success', okMessage)
    } catch (err) {
      notify('error', getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const add = (e) => {
    e.preventDefault()
    if (!newSkill) {
      notify('error', 'Choose a skill to add.')
      return
    }
    persist(
      [...toEntries(profile.skills), { skill_id: Number(newSkill), proficiency: level }],
      'Skill added.',
    )
    setNewSkill('')
  }

  const remove = (skillId) =>
    persist(toEntries(profile.skills).filter((s) => s.skill_id !== skillId), 'Skill removed.')

  const changeLevel = (skillId, proficiency) =>
    persist(
      toEntries(profile.skills).map((s) => (s.skill_id === skillId ? { ...s, proficiency } : s)),
      'Skill level updated.',
    )

  return (
    <Section title="Skills" subtitle="Add the skills you actually have; they drive job matching and skill-gap analysis.">
      {profile.skills.length === 0 ? (
        <p className="text-sm text-slate-500">No skills added yet.</p>
      ) : (
        <ul className="flex flex-wrap gap-2" aria-label="Your skills">
          {profile.skills.map((s) => (
            <li key={s.skill_id} className="flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 py-1 pl-3 pr-1 text-sm">
              <span className="font-medium text-indigo-900">{s.name}</span>
              <select
                aria-label={`Level for ${s.name}`}
                value={s.proficiency}
                disabled={busy}
                onChange={(e) => changeLevel(s.skill_id, e.target.value)}
                className="rounded border-0 bg-transparent text-xs text-indigo-700"
              >
                {LEVELS.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
              <button
                type="button"
                aria-label={`Remove ${s.name}`}
                disabled={busy}
                onClick={() => remove(s.skill_id)}
                className="rounded-full px-2 text-indigo-700 hover:bg-indigo-200"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={add} className="mt-4 flex flex-wrap items-end gap-3">
        <div className="min-w-48 flex-1">
          <label htmlFor="new-skill" className="block text-sm font-medium text-slate-700">
            Add a skill
          </label>
          <select id="new-skill" className={inputClass} value={newSkill} onChange={(e) => setNewSkill(e.target.value)}>
            <option value="">Select skill…</option>
            {available.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="new-level" className="block text-sm font-medium text-slate-700">
            Level
          </label>
          <select id="new-level" className={inputClass} value={level} onChange={(e) => setLevel(e.target.value)}>
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={busy} className={primaryButton}>
          Add skill
        </button>
      </form>
    </Section>
  )
}

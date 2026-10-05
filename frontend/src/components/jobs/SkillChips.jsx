// Required skills are solid indigo, preferred skills are outlined.
export default function SkillChips({ skills, limit }) {
  const shown = limit ? skills.slice(0, limit) : skills
  const hidden = skills.length - shown.length
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Skills">
      {shown.map((s) => (
        <li
          key={s.skill_id}
          title={s.importance === 'required' ? 'Required' : 'Preferred'}
          className={
            s.importance === 'required'
              ? 'rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800'
              : 'rounded-full border border-slate-300 px-2.5 py-0.5 text-xs text-slate-600'
          }
        >
          {s.name}
        </li>
      ))}
      {hidden > 0 && <li className="px-1 text-xs text-slate-500">+{hidden} more</li>}
    </ul>
  )
}

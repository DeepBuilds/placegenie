export function jobToForm(job) {
  if (!job) {
    return {
      company_id: '', role_id: '', title: '', description: '', location: '', job_type: 'full_time', min_cgpa: '0', max_backlogs: '',
      min_experience_months: '0', deadline: '', status: 'open', skills: [], allowed_branch_ids: [], required_certifications: '',
    }
  }
  return {
    company_id: String(job.company.id), role_id: job.role ? String(job.role.id) : '', title: job.title, description: job.description ?? '',
    location: job.location ?? '', job_type: job.job_type, min_cgpa: String(job.min_cgpa), max_backlogs: job.max_backlogs === null ? '' : String(job.max_backlogs),
    min_experience_months: String(job.min_experience_months), deadline: job.deadline ?? '', status: job.status,
    skills: job.skills.map((s) => ({ skill_id: String(s.skill_id), importance: s.importance, weight: String(s.weight) })),
    allowed_branch_ids: job.allowed_branches.map((b) => b.id), required_certifications: job.required_certifications.join(', '),
  }
}

export function validateJob(v) {
  const errors = {}
  if (!v.company_id) errors.company_id = 'Choose the company.'
  if (v.title.trim().length < 2) errors.title = 'Enter the job title (at least 2 characters).'
  const cgpa = Number(v.min_cgpa)
  if (v.min_cgpa === '' || Number.isNaN(cgpa) || cgpa < 0 || cgpa > 10) errors.min_cgpa = 'Minimum CGPA must be between 0 and 10.'
  if (v.max_backlogs !== '' && !(Number.isInteger(Number(v.max_backlogs)) && Number(v.max_backlogs) >= 0)) errors.max_backlogs = 'Enter a whole number, or leave empty for no limit.'
  const months = Number(v.min_experience_months)
  if (!Number.isInteger(months) || months < 0 || months > 120) errors.min_experience_months = 'Enter 0 to 120 months.'
  const ids = v.skills.map((s) => s.skill_id)
  if (ids.some((id) => !id)) errors.skills = 'Choose a skill for every row, or remove the row.'
  else if (new Set(ids).size !== ids.length) errors.skills = 'Each skill can only be listed once.'
  return errors
}

export function formToPayload(v) {
  return {
    company_id: Number(v.company_id), role_id: v.role_id ? Number(v.role_id) : null, title: v.title.trim(),
    description: v.description.trim() || null, location: v.location.trim() || null, job_type: v.job_type,
    min_cgpa: Number(v.min_cgpa), max_backlogs: v.max_backlogs === '' ? null : Number(v.max_backlogs),
    min_experience_months: Number(v.min_experience_months), deadline: v.deadline || null, status: v.status,
    skills: v.skills.map((s) => ({ skill_id: Number(s.skill_id), importance: s.importance, weight: Number(s.weight) })),
    allowed_branch_ids: v.allowed_branch_ids,
    required_certifications: v.required_certifications.split(',').map((c) => c.trim()).filter(Boolean),
  }
}

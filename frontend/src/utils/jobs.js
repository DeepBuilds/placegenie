export const JOB_TYPE_LABELS = {
  full_time: 'Full time',
  internship: 'Internship',
  contract: 'Contract',
}

export const formatJobType = (t) => JOB_TYPE_LABELS[t] ?? t

export function formatDeadline(deadline, isExpired) {
  if (!deadline) return 'No deadline'
  const text = new Date(`${deadline}T00:00:00`).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
  return isExpired ? `Closed on ${text}` : `Apply by ${text}`
}

export const formatBacklogs = (max) =>
  max === null || max === undefined ? 'No limit' : max === 0 ? 'No backlogs allowed' : `Up to ${max}`

export const formatExperience = (months) =>
  !months ? 'Freshers welcome' : `${months} month${months === 1 ? '' : 's'} experience`

export const formatCgpa = (min) => (min > 0 ? `${min.toFixed(2)} or above` : 'No minimum')

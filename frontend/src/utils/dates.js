// Whole calendar days from `today` to a date like "2026-10-12" (negative = in the past).
export function daysLeft(dateStr, today = new Date()) {
  if (!dateStr) return null
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const [y, m, d] = dateStr.split('-').map(Number)
  return Math.round((new Date(y, m - 1, d) - start) / 86400000)
}

export function deadlineText(dateStr, today) {
  const n = daysLeft(dateStr, today)
  if (n === null) return 'No deadline'
  if (n < 0) return 'Deadline passed'
  if (n === 0) return 'Closes today'
  return n === 1 ? 'Closes tomorrow' : `Closes in ${n} days`
}

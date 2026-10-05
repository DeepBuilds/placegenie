// The basic-profile endpoint replaces all basic fields, so every save sends the full set.
export function basicPayload(profile, overrides = {}) {
  return {
    full_name: profile.full_name,
    phone: profile.phone,
    college: profile.college,
    branch_id: profile.branch?.id ?? null,
    year: profile.year,
    semester: profile.semester,
    cgpa: profile.cgpa,
    backlogs: profile.backlogs,
    interests: profile.interests,
    preferred_location: profile.preferred_location,
    preferred_job_type: profile.preferred_job_type,
    ...overrides,
  }
}

const emptyToNull = (v) => (v === '' || v === undefined ? null : v)
export const toNumberOrNull = (v) => (emptyToNull(v) === null ? null : Number(v))

// Client-side checks mirroring the backend rules (the backend remains the authority).
export function validateAcademic(f) {
  const errors = {}
  if (f.full_name.trim().length < 2) errors.full_name = 'Enter your full name.'
  if (f.phone && !/^\+?[0-9][0-9 -]{6,18}[0-9]$/.test(f.phone.trim()))
    errors.phone = 'Enter a valid phone number.'
  const cgpa = toNumberOrNull(f.cgpa)
  if (cgpa !== null && (Number.isNaN(cgpa) || cgpa < 0 || cgpa > 10))
    errors.cgpa = 'CGPA must be between 0 and 10.'
  const backlogs = toNumberOrNull(f.backlogs)
  if (backlogs === null || !Number.isInteger(backlogs) || backlogs < 0)
    errors.backlogs = 'Enter 0 or a positive whole number.'
  const year = toNumberOrNull(f.year)
  const sem = toNumberOrNull(f.semester)
  if (year !== null && (!Number.isInteger(year) || year < 1 || year > 6))
    errors.year = 'Year must be 1 to 6.'
  if (sem !== null && (!Number.isInteger(sem) || sem < 1 || sem > 12))
    errors.semester = 'Semester must be 1 to 12.'
  if (!errors.year && !errors.semester && year && sem && sem !== 2 * year - 1 && sem !== 2 * year)
    errors.semester = `Year ${year} has semesters ${2 * year - 1} and ${2 * year}.`
  return errors
}

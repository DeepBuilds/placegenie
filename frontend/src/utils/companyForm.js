export function validateCompany(v) {
  const errors = {}
  if (v.name.trim().length < 2) errors.name = 'Enter the company name (at least 2 characters).'
  if (v.website.trim() && !/^https?:\/\/\S+$/i.test(v.website.trim())) errors.website = 'Website must start with http:// or https://'
  return errors
}

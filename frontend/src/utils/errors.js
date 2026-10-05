// Turns an Axios error into a message that is safe and understandable to show a user.
export function getErrorMessage(err) {
  if (!err.response) {
    return 'Cannot reach the server. Check your connection and try again.'
  }
  const { status, data } = err.response
  const detail = data?.detail
  if (status === 422 && Array.isArray(detail)) {
    // FastAPI validation errors: [{ loc: [...], msg: "..." }]
    return detail
      .map((d) => {
        const field = d.loc?.[d.loc.length - 1]
        const msg = String(d.msg || '').replace(/^Value error, /, '')
        return field && field !== 'body' ? `${field.replace('_', ' ')}: ${msg}` : msg
      })
      .join(' ')
  }
  if (typeof detail === 'string') return detail
  if (status >= 500) return 'Something went wrong on the server. Please try again later.'
  return 'Request failed. Please try again.'
}

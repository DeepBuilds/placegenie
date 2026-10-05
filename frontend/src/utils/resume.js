export const MAX_RESUME_MB = 5
export const MAX_RESUME_BYTES = MAX_RESUME_MB * 1024 * 1024

// Quick checks in the browser; the server repeats all of them and is the real gatekeeper.
export function validateResumeFile(file) {
  if (!file) return 'Choose a PDF file first.'
  if (!file.name.toLowerCase().endsWith('.pdf')) return 'Only PDF files (.pdf) are supported.'
  if (file.type && !['application/pdf', 'application/x-pdf'].includes(file.type))
    return 'This file does not look like a PDF.'
  if (file.size === 0) return 'This file is empty.'
  if (file.size > MAX_RESUME_BYTES) return `The file is too large. The maximum size is ${MAX_RESUME_MB} MB.`
  return ''
}

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const formatDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : ''

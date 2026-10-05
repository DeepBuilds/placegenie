import client from './client'

const data = (r) => r.data

export const getMyResume = () => client.get('/resumes/me').then(data)
export const getAnalysis = (id) => client.get(`/resumes/${id}/analysis`).then(data)
export const reanalyze = (id) => client.post(`/resumes/${id}/analyze`).then(data)
export const syncSkills = (id) => client.post(`/resumes/${id}/sync-skills`).then(data)
export const deleteResume = (id) => client.delete(`/resumes/${id}`)

// Uploads can take a few seconds (text extraction + analysis), so allow more than the default timeout.
export const uploadResume = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return client
    .post('/resumes', form, {
      timeout: 60000,
      onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
    })
    .then(data)
}

// The PDF is fetched with the login token and opened from a temporary blob URL.
export const fetchResumeFile = (id) =>
  client.get(`/resumes/${id}/file`, { responseType: 'blob' }).then((r) => URL.createObjectURL(r.data))

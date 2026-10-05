import client from './client'

const data = (r) => r.data
const clean = (params = {}) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))

export const applyToJob = (jobId) => client.post('/applications', { job_id: jobId }).then(data)
export const getMyApplications = (params) => client.get('/applications/me', { params: clean(params) }).then(data)
export const getApplication = (id) => client.get(`/applications/${id}`).then(data)
export const withdrawApplication = (id) => client.post(`/applications/${id}/withdraw`).then(data)

export const addInterview = (applicationId, payload) =>
  client.post(`/applications/${applicationId}/interviews`, payload).then(data)
export const getMyInterviews = (when = 'all') => client.get('/interviews/me', { params: { when } }).then(data)
export const getInterview = (id) => client.get(`/interviews/${id}`).then(data)
export const updateInterview = (id, changes) => client.patch(`/interviews/${id}`, changes).then(data)
export const deleteInterview = (id) => client.delete(`/interviews/${id}`)

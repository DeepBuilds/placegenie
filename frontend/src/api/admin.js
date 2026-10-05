import client from './client'

const data = (r) => r.data
const clean = (params = {}) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))

// Coordinator-only views (the server rejects anyone else with 403).
export const getCoordinatorDashboard = () => client.get('/coordinators/dashboard').then(data)
export const getStudents = (params) => client.get('/coordinators/students', { params: clean(params) }).then(data)
export const getStudentDetail = (id) => client.get(`/coordinators/students/${id}`).then(data)
export const getCohortProgress = () => client.get('/coordinators/progress').then(data)
export const getAnalytics = () => client.get('/coordinators/analytics').then(data)
export const getReports = () => client.get('/coordinators/reports').then(data)

/** Downloads a CSV through the authenticated client (a plain link would not carry the login token). */
export async function downloadReport(kind) {
  const res = await client.get(`/coordinators/reports/${kind}.csv`, { responseType: 'blob' })
  const match = /filename="([^"]+)"/.exec(res.headers['content-disposition'] ?? '')
  const filename = match ? match[1] : `placegenie-${kind}.csv`
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return filename
}

// Existing management APIs (shared with the rest of the app, authorised as coordinator on the server).
export const getApplications = (params) => client.get('/applications', { params: clean(params) }).then(data)
export const updateApplicationStatus = (id, status) => client.patch(`/applications/${id}/status`, { status }).then(data)

export const createCompany = (payload) => client.post('/companies', payload).then(data)
export const updateCompany = (id, payload) => client.put(`/companies/${id}`, payload).then(data)
export const deleteCompany = (id) => client.delete(`/companies/${id}`)

export const createJob = (payload) => client.post('/jobs', payload).then(data)
export const updateJob = (id, payload) => client.put(`/jobs/${id}`, payload).then(data)
export const deleteJob = (id) => client.delete(`/jobs/${id}`)

import client from './client'

const data = (r) => r.data

// params: plain object; empty values are dropped so the URL stays clean.
const clean = (params = {}) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))

export const getJobs = (params) => client.get('/jobs', { params: clean(params) }).then(data)
export const getJob = (id) => client.get(`/jobs/${id}`).then(data)
export const getCompanies = (params) => client.get('/companies', { params: clean(params) }).then(data)
export const getCompany = (id) => client.get(`/companies/${id}`).then(data)

export const checkEligibility = (jobId) => client.post(`/jobs/${jobId}/eligibility`).then(data)

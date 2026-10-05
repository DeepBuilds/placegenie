import client from './client'

const data = (r) => r.data

export const getProfile = () => client.get('/students/me').then(data)
export const saveProfile = (payload) => client.put('/students/me', payload).then(data)
export const saveSkills = (skills) => client.put('/students/me/skills', { skills }).then(data)
export const savePreferences = (payload) =>
  client.put('/students/me/preferences', payload).then(data)

// kind: 'certifications' | 'projects' | 'experiences'
export const addItem = (kind, payload) => client.post(`/students/me/${kind}`, payload).then(data)
export const removeItem = (kind, id) => client.delete(`/students/me/${kind}/${id}`).then(data)

export const getBranches = () => client.get('/branches').then(data)
export const getSkills = () => client.get('/skills').then(data)
export const getJobRoles = () => client.get('/job-roles').then(data)

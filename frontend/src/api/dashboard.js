import client from './client'

export const getDashboard = () => client.get('/dashboard').then((r) => r.data)

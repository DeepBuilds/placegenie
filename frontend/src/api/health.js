import client from './client'

export const getHealth = () => client.get('/health').then((r) => r.data)

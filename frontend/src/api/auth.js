import client from './client'

export const loginRequest = (email, password) =>
  client.post('/auth/login', { email, password }).then((r) => r.data)

export const registerRequest = (payload) =>
  client.post('/auth/register', payload).then((r) => r.data)

export const fetchCurrentUser = () => client.get('/auth/me').then((r) => r.data)

export const logoutRequest = () => client.post('/auth/logout')

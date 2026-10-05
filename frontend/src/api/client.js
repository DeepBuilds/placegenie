import axios from 'axios'
import { clearToken, getToken } from '../utils/storage'

export const AUTH_EXPIRED_EVENT = 'auth:expired'

// Single configured Axios instance used by every API module.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
})

// Attach the JWT to every request.
client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// A 401 on a request that carried a token means the session expired or is invalid:
// drop the token and tell the app. (Login failures also return 401 but carry no token.)
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && error.config?.headers?.Authorization) {
      clearToken()
      window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    }
    return Promise.reject(error)
  },
)

export default client

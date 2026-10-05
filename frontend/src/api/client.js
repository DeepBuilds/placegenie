import axios from 'axios'

// Single configured Axios instance used by every API module.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 10000,
})

export default client

import client from './client'

// params: role_id, location, eligible_only, sort, limit, offset (empty values are dropped)
export const getRecommendations = (params = {}) =>
  client
    .get('/recommendations', {
      params: Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null)),
    })
    .then((r) => r.data)

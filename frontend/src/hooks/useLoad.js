import { useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../utils/errors'

/**
 * Loads data when `key` changes. While a newer request is running, the previous data stays
 * on screen (`loading` is true). `reload()` repeats the request, e.g. after an edit.
 * `notFound` replaces the server's text when the answer is 404 (e.g. an id in the URL that does not exist).
 */
export function useLoad(fetcher, key, { notFound } = {}) {
  const latest = useRef({ fetcher, notFound })
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState({ key: null, data: null, error: '' })
  const requestKey = `${key}|${version}`

  useEffect(() => {
    latest.current = { fetcher, notFound }
  })

  useEffect(() => {
    let cancelled = false
    const { fetcher: load, notFound: missing } = latest.current
    load()
      .then((data) => !cancelled && setResult({ key: requestKey, data, error: '' }))
      .catch((err) => !cancelled && setResult({
        key: requestKey, data: null, error: missing && err.response?.status === 404 ? missing : getErrorMessage(err),
      }))
    return () => {
      cancelled = true
    }
  }, [requestKey])

  return {
    data: result.data,
    error: result.error,
    loading: result.key !== requestKey,
    reload: () => setVersion((v) => v + 1),
  }
}

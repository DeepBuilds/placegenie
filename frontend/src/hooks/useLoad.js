import { useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../utils/errors'

/**
 * Loads data when `key` changes. While a newer request is running, the previous data stays
 * on screen (`loading` is true). `reload()` repeats the request, e.g. after an edit.
 */
export function useLoad(fetcher, key) {
  const latest = useRef(fetcher)
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState({ key: null, data: null, error: '' })
  const requestKey = `${key}|${version}`

  useEffect(() => {
    latest.current = fetcher
  })

  useEffect(() => {
    let cancelled = false
    latest
      .current()
      .then((data) => !cancelled && setResult({ key: requestKey, data, error: '' }))
      .catch((err) => !cancelled && setResult({ key: requestKey, data: null, error: getErrorMessage(err) }))
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

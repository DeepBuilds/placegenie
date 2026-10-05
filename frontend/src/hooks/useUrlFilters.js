import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * Keeps page filters in the URL (shareable, survives reload, back button works).
 *
 * `update` builds on the latest parameters held in a ref, not on the last render's,
 * because react-router does not queue updates: two changes in one tick would
 * otherwise overwrite each other.
 */
export function useUrlFilters() {
  const [params, setParams] = useSearchParams()
  const latest = useRef(params)

  useEffect(() => {
    latest.current = params
  }, [params])

  const get = (key) => params.get(key) ?? ''

  const update = (changes, { keepOffset = false } = {}) => {
    const next = new URLSearchParams(latest.current)
    for (const [k, v] of Object.entries(changes)) {
      if (v === '' || v === null || v === false || v === undefined) next.delete(k)
      else next.set(k, String(v))
    }
    if (!keepOffset) next.delete('offset')
    latest.current = next
    setParams(next, { replace: true })
  }

  const reset = () => {
    latest.current = new URLSearchParams()
    setParams({}, { replace: true })
  }

  return { params, query: params.toString(), get, update, reset }
}

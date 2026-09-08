import { useState, useEffect, useCallback } from 'react'
import type { OHRecord } from '../types'

export function useOH() {
  const [ohData, setOhData] = useState<OHRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/api/oh')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: OHRecord[]) => {
        setOhData(data)
        setError(null)
      })
      .catch((e) => {
        setOhData([])
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { ohData, loading, error }
}

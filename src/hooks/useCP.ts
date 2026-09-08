import { useState, useEffect, useCallback } from 'react'
import type { CPRecord } from '../types'

export function useCP() {
  const [cpData, setCpData] = useState<CPRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/cp')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: CPRecord[]) => {
        setCpData(data)
        setError(null)
      })
      .catch((e) => {
        setCpData([])
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { cpData, loading, error }
}

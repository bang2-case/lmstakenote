import { useState, useEffect, useCallback } from 'react'
import type { TPRecord } from '../types'

export function useTP() {
  const [tpData, setTpData] = useState<TPRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/tp')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: TPRecord[]) => {
        setTpData(data)
        setError(null)
      })
      .catch((e) => {
        setTpData([])
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { tpData, loading, error }
}

import { useState, useEffect } from 'react'
import type { TPRecord } from '../types'

export function useTP() {
  const [tpData, setTpData] = useState<TPRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/tp')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: TPRecord[]) => setTpData(data))
      .catch(() => {
        // Fallback: đọc từ JSON tĩnh
        fetch('/tp.json')
          .then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            return res.json()
          })
          .then((data: TPRecord[]) => setTpData(data))
          .catch((e) => setError(e.message))
      })
      .finally(() => setLoading(false))
  }, [])

  return { tpData, loading, error }
}

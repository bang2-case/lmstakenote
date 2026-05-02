import { useState, useEffect, useCallback } from 'react'
import type { ClassItem } from '../types'

export function useClasses() {
  const [classes, setClasses] = useState<ClassItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/classes')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: ClassItem[]) => {
        setClasses(data)
        setError(null)
      })
      .catch(() => {
        fetch('/classes.json')
          .then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            return res.json()
          })
          .then((data: ClassItem[]) => setClasses(data))
          .catch((e) => setError(e.message))
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    // Reload when server pushes data-updated event
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { classes, loading, error }
}

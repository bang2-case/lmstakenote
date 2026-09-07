import { useState, useEffect, useCallback } from 'react'
import type { ClassItem } from '../types'

interface UseClassesOptions {
  includeStudents?: boolean
  includeSlots?: boolean
}

export function useClasses(options: UseClassesOptions = {}) {
  const includeStudents = Boolean(options.includeStudents)
  const includeSlots = options.includeSlots !== false
  const [classes, setClasses] = useState<ClassItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (includeStudents) params.set('include_students', 'true')
    if (!includeSlots) params.set('include_slots', 'false')
    const query = params.toString()
    const url = query ? `/api/classes?${query}` : '/api/classes'
    fetch(url)
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
  }, [includeStudents, includeSlots])

  useEffect(() => {
    load()
    // Reload when server pushes data-updated event
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { classes, loading, error }
}

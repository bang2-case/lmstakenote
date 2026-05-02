import { useState, useEffect, useCallback } from 'react'
import type { TeacherItem } from '../types'

export function useTeachers() {
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    fetch('/api/teachers')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: TeacherItem[]) => {
        setTeachers(data)
        setError(null)
      })
      .catch(() => {
        fetch('/teachers.json')
          .then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            return res.json()
          })
          .then((data: TeacherItem[]) => setTeachers(data))
          .catch((e) => setError(e.message))
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    window.addEventListener('lms-data-updated', load)
    return () => window.removeEventListener('lms-data-updated', load)
  }, [load])

  return { teachers, loading, error }
}

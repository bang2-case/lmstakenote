import { useState, useEffect } from 'react'
import type { TeacherItem } from '../types'

export function useTeachers() {
  const [teachers, setTeachers] = useState<TeacherItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/teachers.json')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: TeacherItem[]) => setTeachers(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return { teachers, loading, error }
}

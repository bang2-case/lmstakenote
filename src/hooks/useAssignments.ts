import { useCallback, useEffect, useState } from 'react'
import type { AssignmentClassRecord, AssignmentFetchError, AssignmentPayload } from '../types'

type AssignmentResponse = AssignmentClassRecord[] | Partial<AssignmentPayload>

function normalizeAssignmentResponse(data: AssignmentResponse): AssignmentPayload {
  if (Array.isArray(data)) {
    return { records: data, errors: [] }
  }
  return {
    records: Array.isArray(data.records) ? data.records : [],
    errors: Array.isArray(data.errors) ? data.errors : [],
  }
}

export function useAssignments() {
  const [assignmentData, setAssignmentData] = useState<AssignmentClassRecord[]>([])
  const [assignmentErrors, setAssignmentErrors] = useState<AssignmentFetchError[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    fetch('/api/assignments')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: AssignmentResponse) => {
        const payload = normalizeAssignmentResponse(data)
        setAssignmentData(payload.records)
        setAssignmentErrors(payload.errors)
        setError(null)
      })
      .catch(() => {
        return fetch('/assignments.json')
          .then((res) => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`)
            return res.json()
          })
          .then((data: AssignmentResponse) => {
            const payload = normalizeAssignmentResponse(data)
            setAssignmentData(payload.records)
            setAssignmentErrors(payload.errors)
            setError(null)
          })
          .catch((e) => {
            setAssignmentData([])
            setAssignmentErrors([])
            setError(e.message)
          })
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    window.addEventListener('lms-assignments-updated', load)
    return () => window.removeEventListener('lms-assignments-updated', load)
  }, [load])

  return { assignmentData, assignmentErrors, loading, error }
}

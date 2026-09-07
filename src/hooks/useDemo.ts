import { useState, useCallback } from 'react'

export interface DemoClass {
  id: string
  name: string
  status: string
  centre: string
  centre_full: string
  area: string
  block: 'Coding' | 'Robotics' | 'Art'
  teacher: string
  student_count: number
  date: string
  day_of_week: string
  time: string
  time_demo: string
  slot_14_date: string
}

export interface ExportResult {
  url: string
  tab_name: string
  coding_count: number
  robotics_count: number
  art_count: number
  total: number
}

export function useDemo() {
  const [classes, setClasses] = useState<DemoClass[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exportResult, setExportResult] = useState<ExportResult | null>(null)

  const fetchClasses = useCallback(async (date: string, dateTo: string = "") => {
    setLoading(true)
    setError(null)
    setClasses([])
    setExportResult(null)
    try {
      const params = new URLSearchParams({ date })
      if (dateTo && dateTo !== date) params.set('date_to', dateTo)
      const res = await fetch(`/api/demo/classes?${params}`)
      const data = await res.json()
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`)
      setClasses(data)
      return data as DemoClass[]
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const exportSheet = useCallback(async (date: string, dateTo: string = "", classesToExport?: DemoClass[]) => {
    setExporting(true)
    setError(null)
    setExportResult(null)
    try {
      const res = await fetch('/api/demo/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date, date_to: dateTo || date, classes: classesToExport }),
      })
      const data = await res.json()
      if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`)
      setExportResult(data)
      return data as ExportResult
    } catch (e: any) {
      setError(e.message)
      throw e
    } finally {
      setExporting(false)
    }
  }, [])

  return { classes, loading, exporting, error, exportResult, fetchClasses, exportSheet }
}

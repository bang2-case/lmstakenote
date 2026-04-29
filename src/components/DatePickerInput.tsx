import { useState, useRef, useEffect } from 'react'
import { DayPicker } from 'react-day-picker'
import 'react-day-picker/style.css'

interface Props {
  label: string
  value: { from: string; to: string }
  onChange: (from: string, to: string) => void
  placeholder?: string
}

// Convert Date → 'YYYY-MM-DD' string (local timezone)
function toDateStr(date: Date): string {
  return (
    date.getFullYear() +
    '-' +
    String(date.getMonth() + 1).padStart(2, '0') +
    '-' +
    String(date.getDate()).padStart(2, '0')
  )
}

// Convert 'YYYY-MM-DD' → Date (local timezone, tránh UTC offset)
function fromDateStr(str: string): Date {
  const [y, m, d] = str.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatDisplay(from: string, to: string): string {
  if (!from) return ''
  const fromDate = fromDateStr(from).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
  if (!to || from === to) return fromDate
  const toDate = fromDateStr(to).toLocaleDateString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
  return `${fromDate} → ${toDate}`
}

export default function DatePickerInput({ label, value, onChange, placeholder = 'Chọn ngày...' }: Props) {
  const [open, setOpen] = useState(false)
  const [range, setRange] = useState<{ from?: Date; to?: Date }>({
    from: value.from ? fromDateStr(value.from) : undefined,
    to: value.to ? fromDateStr(value.to) : undefined,
  })
  const containerRef = useRef<HTMLDivElement>(null)

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Sync external reset (when filters are cleared)
  useEffect(() => {
    setRange({
      from: value.from ? fromDateStr(value.from) : undefined,
      to: value.to ? fromDateStr(value.to) : undefined,
    })
  }, [value.from, value.to])

  const handleSelect = (selected: { from?: Date; to?: Date } | undefined) => {
    if (!selected) {
      setRange({})
      onChange('', '')
      return
    }

    const { from, to } = selected

    // If same date selected (from === to) → single date filter
    if (from && to && toDateStr(from) === toDateStr(to)) {
      setRange({ from, to })
      onChange(toDateStr(from), toDateStr(to))
      setOpen(false)
      return
    }

    // Range selected
    if (from && to) {
      setRange({ from, to })
      onChange(toDateStr(from), toDateStr(to))
      setOpen(false)
      return
    }

    // First click - only from selected
    setRange({ from, to: undefined })
    onChange(from ? toDateStr(from) : '', '')
  }

  const displayText = formatDisplay(value.from, value.to)

  return (
    <div className="filter-group" ref={containerRef} style={{ position: 'relative' }}>
      <label className="filter-label">{label}</label>
      <div
        className={`date-picker-input ${open ? 'active' : ''} ${displayText ? 'has-value' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className={displayText ? 'date-picker-value' : 'date-picker-placeholder'}>
          {displayText || placeholder}
        </span>
        <span className="date-picker-icon">
          {displayText ? (
            <button
              className="date-picker-clear"
              onClick={(e) => {
                e.stopPropagation()
                setRange({})
                onChange('', '')
              }}
            >
              ✕
            </button>
          ) : (
            '📅'
          )}
        </span>
      </div>

      {open && (
        <div className="date-picker-popup">
          <DayPicker
            mode="range"
            selected={range as any}
            onSelect={handleSelect as any}
            locale={undefined}
            weekStartsOn={1}
            showOutsideDays
            fixedWeeks
          />
        </div>
      )}
    </div>
  )
}

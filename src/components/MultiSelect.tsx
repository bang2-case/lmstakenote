import { useState, useRef, useEffect } from 'react'

interface Props {
  label: string
  options: string[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  renderOption?: (value: string) => string
}

export default function MultiSelect({ label, options, selected, onChange, placeholder = 'Tất cả', renderOption }: Props) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((v) => v !== value))
    } else {
      onChange([...selected, value])
    }
  }

  const displayText = selected.length === 0
    ? placeholder
    : selected.map(v => renderOption ? renderOption(v) : v).join(', ')

  const hasValue = selected.length > 0

  return (
    <div className="filter-group" ref={containerRef} style={{ position: 'relative' }}>
      <label className="filter-label">{label}</label>

      {/* Trigger button */}
      <div
        className={`date-picker-input ${open ? 'active' : ''} ${hasValue ? 'has-value' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span
          className={hasValue ? 'date-picker-value' : 'date-picker-placeholder'}
          style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '85%' }}
        >
          {displayText}
        </span>
        <span className="date-picker-icon">
          {hasValue ? (
            <button
              className="date-picker-clear"
              onClick={(e) => { e.stopPropagation(); onChange([]) }}
            >
              ✕
            </button>
          ) : (
            <span style={{ fontSize: 10, color: '#9ca3af', transition: 'transform 0.2s', display: 'inline-block', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
          )}
        </span>
      </div>

      {/* Dropdown */}
      {open && (
        <div className="multiselect-popup">
          {options.map((opt) => {
            const isSelected = selected.includes(opt)
            return (
              <div
                key={opt}
                className={`multiselect-item ${isSelected ? 'multiselect-item-selected' : ''}`}
                onClick={() => toggle(opt)}
              >
                <span className="multiselect-item-text">
                  {renderOption ? renderOption(opt) : opt}
                </span>
                {isSelected && <span className="multiselect-item-check">✓</span>}
              </div>
            )
          })}
          {options.length === 0 && (
            <div className="multiselect-empty">Không có dữ liệu</div>
          )}
        </div>
      )}
    </div>
  )
}

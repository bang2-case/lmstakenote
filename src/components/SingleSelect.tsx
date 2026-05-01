import { useState, useRef, useEffect } from 'react'

interface Option {
  value: string
  label: string
}

interface Props {
  label: string
  options: Option[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export default function SingleSelect({ label, options, value, onChange, placeholder = 'Tất cả' }: Props) {
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

  const selected = options.find((o) => o.value === value)
  const hasValue = !!value

  const handleSelect = (optValue: string) => {
    onChange(optValue === value ? '' : optValue) // bấm lại để bỏ chọn
    setOpen(false)
  }

  return (
    <div className="filter-group" ref={containerRef} style={{ position: 'relative' }}>
      <label className="filter-label">{label}</label>

      <div
        className={`filter-select-trigger ${open ? 'active' : ''} ${hasValue ? 'has-value' : ''}`}
        onClick={() => setOpen(!open)}
      >
        <span className={hasValue ? 'filter-select-value' : 'filter-select-placeholder'}>
          {selected ? selected.label : placeholder}
        </span>
        <span className="filter-select-icon">
          {hasValue ? (
            <button
              className="filter-select-clear"
              onClick={(e) => { e.stopPropagation(); onChange('') }}
            >
              ✕
            </button>
          ) : (
            <span className={`filter-select-arrow ${open ? 'open' : ''}`}>▾</span>
          )}
        </span>
      </div>

      {open && (
        <div className="multiselect-popup">
          {options.map((opt) => {
            const isSelected = opt.value === value
            return (
              <div
                key={opt.value}
                className={`multiselect-item ${isSelected ? 'multiselect-item-selected' : ''}`}
                onClick={() => handleSelect(opt.value)}
              >
                <span className="multiselect-item-text">{opt.label}</span>
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

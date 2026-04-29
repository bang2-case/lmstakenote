import { useState } from 'react'
import type { ClassFilters, ClassItem } from '../types'

interface Props {
  filters: ClassFilters
  onChange: (filters: ClassFilters) => void
  centres: string[]
  courses: string[]
  statuses: string[]
  mentors: string[]
  blocks: string[]
  filteredClasses?: ClassItem[]
}

export default function ClassFiltersComponent({ filters, onChange, centres, courses, statuses, mentors, blocks, filteredClasses = [] }: Props) {
  const [startDateRange, setStartDateRange] = useState<[string, string]>(['', ''])
  const [endDateRange, setEndDateRange] = useState<[string, string]>(['', ''])
  const [slotRange, setSlotRange] = useState<[string, string]>(['', ''])
  const [startDateClicks, setStartDateClicks] = useState(0)
  const [endDateClicks, setEndDateClicks] = useState(0)
  const [slotClicks, setSlotClicks] = useState(0)
  const [showSummary, setShowSummary] = useState(false)

  // Local state for filters to avoid prop dependency issues
  const [localFilters, setLocalFilters] = useState<ClassFilters>(filters)

  const update = (key: keyof ClassFilters, value: string) => {
    const newFilters = { ...localFilters, [key]: value }
    setLocalFilters(newFilters)
    onChange(newFilters)
  }

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    if (startDateClicks === 0) {
      setStartDateRange([value, ''])
      setStartDateClicks(1)
      const newFilters = { ...localFilters, startDate: value, startDateTo: '' }
      setLocalFilters(newFilters)
      onChange(newFilters)
    } else {
      const [first] = startDateRange
      if (first === value) {
        // Same date selected twice - filter for exact date
        setStartDateRange([value, value])
        setStartDateClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, startDate: value, startDateTo: value }
        setLocalFilters(newFilters)
        onChange(newFilters)
      } else {
        // Different dates - create range
        const sorted = [first, value].sort()
        setStartDateRange([sorted[0], sorted[1]])
        setStartDateClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, startDate: sorted[0], startDateTo: sorted[1] }
        setLocalFilters(newFilters)
        onChange(newFilters)
      }
    }
  }

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    if (endDateClicks === 0) {
      setEndDateRange([value, ''])
      setEndDateClicks(1)
      const newFilters = { ...localFilters, endDate: value, endDateTo: '' }
      setLocalFilters(newFilters)
      onChange(newFilters)
    } else {
      const [first] = endDateRange
      if (first === value) {
        // Same date selected twice - filter for exact date
        setEndDateRange([value, value])
        setEndDateClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, endDate: value, endDateTo: value }
        setLocalFilters(newFilters)
        onChange(newFilters)
      } else {
        // Different dates - create range
        const sorted = [first, value].sort()
        setEndDateRange([sorted[0], sorted[1]])
        setEndDateClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, endDate: sorted[0], endDateTo: sorted[1] }
        setLocalFilters(newFilters)
        onChange(newFilters)
      }
    }
  }

  const handleSlotChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    
    if (slotClicks === 0) {
      // First click - set start date
      setSlotRange([value, ''])
      setSlotClicks(1)
      const newFilters = { ...localFilters, slot: value, slotTo: '' }
      setLocalFilters(newFilters)
      onChange(newFilters)
    } else {
      // Second click
      const [first] = slotRange
      if (first === value) {
        // Same date selected twice - filter for exact date
        setSlotRange([value, value])
        setSlotClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, slot: value, slotTo: value }
        setLocalFilters(newFilters)
        onChange(newFilters)
      } else {
        // Different dates - create range
        const sorted = [first, value].sort()
        setSlotRange([sorted[0], sorted[1]])
        setSlotClicks(0) // Reset to allow new selection
        const newFilters = { ...localFilters, slot: sorted[0], slotTo: sorted[1] }
        setLocalFilters(newFilters)
        onChange(newFilters)
      }
    }
  }

  const getStartDateDisplay = () => {
    if (startDateRange[0] && startDateRange[1]) {
      if (startDateRange[0] === startDateRange[1]) {
        return `${new Date(startDateRange[0]).toLocaleDateString('vi-VN')}`
      }
      return `${new Date(startDateRange[0]).toLocaleDateString('vi-VN')} → ${new Date(startDateRange[1]).toLocaleDateString('vi-VN')}`
    }
    if (startDateRange[0]) {
      return `${new Date(startDateRange[0]).toLocaleDateString('vi-VN')} (chọn ngày kết thúc)`
    }
    return ''
  }

  const getEndDateDisplay = () => {
    if (endDateRange[0] && endDateRange[1]) {
      if (endDateRange[0] === endDateRange[1]) {
        return `${new Date(endDateRange[0]).toLocaleDateString('vi-VN')}`
      }
      return `${new Date(endDateRange[0]).toLocaleDateString('vi-VN')} → ${new Date(endDateRange[1]).toLocaleDateString('vi-VN')}`
    }
    if (endDateRange[0]) {
      return `${new Date(endDateRange[0]).toLocaleDateString('vi-VN')} (chọn ngày kết thúc)`
    }
    return ''
  }

  const getSlotDisplay = () => {
    if (slotRange[0] && slotRange[1]) {
      if (slotRange[0] === slotRange[1]) {
        return `${new Date(slotRange[0]).toLocaleDateString('vi-VN')}`
      }
      return `${new Date(slotRange[0]).toLocaleDateString('vi-VN')} → ${new Date(slotRange[1]).toLocaleDateString('vi-VN')}`
    }
    if (slotRange[0]) {
      return `${new Date(slotRange[0]).toLocaleDateString('vi-VN')} (chọn ngày kết thúc)`
    }
    return ''
  }

  return (
    <div className="filters-container">
      <div className="filter-group">
        <label className="filter-label">Cơ sở</label>
        <select value={localFilters.centre} onChange={(e) => update('centre', e.target.value)}>
          <option value="">Tất cả</option>
          {centres.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">Ngày bắt đầu</label>
        <input
          type="date"
          onChange={handleStartDateChange}
          onFocus={() => {
            // Reset clicks when user focuses on input to allow fresh selection
            if (startDateClicks === 1 && startDateRange[1] === '') {
              setStartDateClicks(0)
              setStartDateRange(['', ''])
            }
          }}
          placeholder="Chọn khoảng ngày"
        />
        {getStartDateDisplay() && <div className="date-range-display">{getStartDateDisplay()}</div>}
      </div>

      <div className="filter-group">
        <label className="filter-label">Ngày kết thúc</label>
        <input
          type="date"
          onChange={handleEndDateChange}
          onFocus={() => {
            // Reset clicks when user focuses on input to allow fresh selection
            if (endDateClicks === 1 && endDateRange[1] === '') {
              setEndDateClicks(0)
              setEndDateRange(['', ''])
            }
          }}
          placeholder="Chọn khoảng ngày"
        />
        {getEndDateDisplay() && <div className="date-range-display">{getEndDateDisplay()}</div>}
      </div>

      <div className="filter-group">
        <label className="filter-label">Ngày diễn ra</label>
        <input
          type="date"
          onChange={handleSlotChange}
          onFocus={() => {
            // Reset clicks when user focuses on input to allow fresh selection
            if (slotClicks === 1 && slotRange[1] === '') {
              setSlotClicks(0)
              setSlotRange(['', ''])
            }
          }}
          placeholder="Chọn khoảng ngày"
        />
        {getSlotDisplay() && <div className="date-range-display">{getSlotDisplay()}</div>}
      </div>

      <div className="filter-group">
        <label className="filter-label">Khối</label>
        <select value={localFilters.block} onChange={(e) => update('block', e.target.value)}>
          <option value="">Tất cả</option>
          {blocks.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">Khóa học</label>
        <select value={localFilters.course} onChange={(e) => update('course', e.target.value)}>
          <option value="">Tất cả</option>
          {courses.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">Trạng thái</label>
        <select value={localFilters.status} onChange={(e) => update('status', e.target.value)}>
          <option value="">Tất cả</option>
          {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">Nhận xét</label>
        <select value={localFilters.hasComments} onChange={(e) => update('hasComments', e.target.value)}>
          <option value="">Tất cả</option>
          <option value="100">Đã nhận xét</option>
          <option value="0">Chưa nhận xét</option>
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">Giáo viên</label>
        <select value={localFilters.mentor} onChange={(e) => update('mentor', e.target.value)}>
          <option value="">Tất cả</option>
          {mentors.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <div className="filter-group">
        <label className="filter-label">&nbsp;</label>
        <button className="btn-reset" onClick={() => {
            setStartDateRange(['', ''])
            setEndDateRange(['', ''])
            setSlotRange(['', ''])
            setStartDateClicks(0)
            setEndDateClicks(0)
            setSlotClicks(0)
            const resetFilters = {
              centre: '', startDate: '', startDateTo: '', endDate: '', endDateTo: '', 
              slot: '', slotTo: '', course: '', status: '', hasComments: '', mentor: '', block: ''
            }
            setLocalFilters(resetFilters)
            onChange(resetFilters)
          }}>
          Xóa bộ lọc
        </button>
      </div>

      <div className="filter-group">
        <label className="filter-label">&nbsp;</label>
        <button className="btn-summary" onClick={() => setShowSummary(true)}>
          📋 Tổng hợp
        </button>
      </div>

      {/* Summary Modal */}
      {showSummary && (
        <div className="modal-overlay" onClick={() => setShowSummary(false)}>
          <div className="modal-content summary-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowSummary(false)}>✕</button>
            <div className="modal-header">
              <h2 className="modal-title">
                Tổng hợp danh sách lớp
                <span className="summary-count">{filteredClasses.length} lớp</span>
              </h2>
            </div>
            <div className="summary-table-wrapper">
              {filteredClasses.length === 0 ? (
                <p className="state-msg">Không có lớp nào phù hợp với bộ lọc.</p>
              ) : (
                <table className="summary-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Tên lớp</th>
                      <th>Khóa học</th>
                      <th>Cơ sở</th>
                      <th>Trạng thái</th>
                      <th>Giáo viên</th>
                      <th>Học viên</th>
                      <th>Nhận xét</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredClasses.map((c, i) => (
                      <tr key={c.id}>
                        <td>{i + 1}</td>
                        <td className="summary-name">{c.name}</td>
                        <td>{c.course || '—'}</td>
                        <td>{c.centre || '—'}</td>
                        <td>{c.status}</td>
                        <td>{c.teachers[0]?.name || '—'}</td>
                        <td>{c.studentCount}</td>
                        <td>
                          {c.totalSlotsWithStudents > 0
                            ? `${c.commentPercentage}%`
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

import { useState } from 'react'
import type { ClassFilters } from '../types'
import DatePickerInput from './DatePickerInput'
import MultiSelect from './MultiSelect'

interface Props {
  filters: ClassFilters
  onChange: (filters: ClassFilters) => void
  centres: string[]
  courses: string[]
  statuses: string[]
  mentors: string[]
  blocks: string[]
  onSummary: () => void
}

const STATUS_MAP: Record<string, string> = {
  PENDING: 'Pending', PRE_OPEN: 'Pre Open', OPEN: 'Open', RUNNING: 'Running',
  FINISHED: 'Finished', NEW: 'New', PREPARING: 'Preparing', ABANDONED: 'Abandoned', REJECT: 'Reject',
}

export default function ClassFiltersComponent({ filters, onChange, centres, courses, statuses, mentors, blocks, onSummary }: Props) {
  const [localFilters, setLocalFilters] = useState<ClassFilters>(filters)

  const update = (key: keyof ClassFilters, value: string) => {
    const newFilters = { ...localFilters, [key]: value }
    setLocalFilters(newFilters)
    onChange(newFilters)
  }

  const updateMultiple = (updates: Partial<ClassFilters>) => {
    const newFilters = { ...localFilters, ...updates }
    setLocalFilters(newFilters)
    onChange(newFilters)
  }

  return (
    <div className="filters-container">
      {/* Cơ sở */}
      <div className="filter-group">
        <label className="filter-label">Cơ sở</label>
        <select value={localFilters.centre} onChange={(e) => update('centre', e.target.value)}>
          <option value="">Tất cả</option>
          {centres.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Ngày bắt đầu */}
      <DatePickerInput
        label="Ngày bắt đầu"
        value={{ from: localFilters.startDate, to: localFilters.startDateTo }}
        onChange={(from, to) => updateMultiple({ startDate: from, startDateTo: to })}
      />

      {/* Ngày kết thúc */}
      <DatePickerInput
        label="Ngày kết thúc"
        value={{ from: localFilters.endDate, to: localFilters.endDateTo }}
        onChange={(from, to) => updateMultiple({ endDate: from, endDateTo: to })}
      />

      {/* Ngày diễn ra */}
      <DatePickerInput
        label="Ngày diễn ra"
        value={{ from: localFilters.slot, to: localFilters.slotTo }}
        onChange={(from, to) => updateMultiple({ slot: from, slotTo: to })}
      />

      {/* Khối - multi-select */}
      <MultiSelect
        label="Khối"
        options={blocks}
        selected={localFilters.block}
        onChange={(val) => updateMultiple({ block: val })}
        placeholder="Tất cả"
      />

      {/* Khóa học */}
      <div className="filter-group">
        <label className="filter-label">Khóa học</label>
        <select value={localFilters.course} onChange={(e) => update('course', e.target.value)}>
          <option value="">Tất cả</option>
          {courses.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Trạng thái - multi-select */}
      <MultiSelect
        label="Trạng thái"
        options={statuses}
        selected={localFilters.status}
        onChange={(val) => updateMultiple({ status: val })}
        placeholder="Tất cả"
        renderOption={(v) => STATUS_MAP[v] ?? v}
      />

      {/* Nhận xét */}
      <div className="filter-group">
        <label className="filter-label">Nhận xét</label>
        <select value={localFilters.hasComments} onChange={(e) => update('hasComments', e.target.value)}>
          <option value="">Tất cả</option>
          <option value="100">Đã nhận xét</option>
          <option value="0">Chưa nhận xét</option>
        </select>
      </div>

      {/* Mentor */}
      <div className="filter-group">
        <label className="filter-label">Mentor</label>
        <select value={localFilters.mentor} onChange={(e) => update('mentor', e.target.value)}>
          <option value="">Tất cả</option>
          {mentors.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      {/* Reset */}
      <div className="filter-group">
        <label className="filter-label">&nbsp;</label>
        <button className="btn-reset" onClick={() => {
          const resetFilters: ClassFilters = {
            centre: '', startDate: '', startDateTo: '', endDate: '', endDateTo: '',
            slot: '', slotTo: '', course: '', status: [], hasComments: '', mentor: '', block: []
          }
          setLocalFilters(resetFilters)
          onChange(resetFilters)
        }}>
          Xóa bộ lọc
        </button>
      </div>

      {/* Tổng hợp */}
      <div className="filter-group">
        <label className="filter-label">&nbsp;</label>
        <button className="btn-summary" onClick={onSummary}>
          📋 Tổng hợp
        </button>
      </div>
    </div>
  )
}

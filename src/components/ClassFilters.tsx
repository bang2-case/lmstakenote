import { useState } from 'react'
import type { ClassFilters } from '../types'
import DatePickerInput from './DatePickerInput'
import MultiSelect from './MultiSelect'
import SingleSelect from './SingleSelect'
import { AREA_CENTRES, AREA_OPTIONS, filterCentresByArea } from '../utils/areas'

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
  const centreOptions = filterCentresByArea(centres, localFilters.area)

  const update = (key: keyof ClassFilters, value: string) => {
    const newFilters = { ...localFilters, [key]: value }
    setLocalFilters(newFilters)
    onChange(newFilters)
  }

  const updateArea = (area: string) => {
    const nextCentre = area && !AREA_CENTRES[area]?.some((keyword) => localFilters.centre.includes(keyword))
      ? ''
      : localFilters.centre
    updateMultiple({ area, centre: nextCentre })
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
        <label className="filter-label">Tìm lớp</label>
        <input
          type="text"
          placeholder="Nhập tên lớp..."
          value={localFilters.search}
          onChange={(e) => update('search', e.target.value)}
        />
      </div>

      <SingleSelect
        label="Khu vực"
        options={AREA_OPTIONS}
        value={localFilters.area}
        onChange={updateArea}
      />

      <SingleSelect
        label="Cơ sở"
        options={centreOptions.map((c) => ({ value: c, label: c }))}
        value={localFilters.centre}
        onChange={(v) => update('centre', v)}
      />

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
      <SingleSelect
        label="Khóa học"
        options={courses.map((c) => ({ value: c, label: c }))}
        value={localFilters.course}
        onChange={(v) => update('course', v)}
      />

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
      <SingleSelect
        label="Nhận xét"
        options={[
          { value: 'commented', label: 'Đã nhận xét' },
          { value: 'pending',   label: 'Chưa nhận xét (Chưa quá hạn)' },
          { value: 'overdue',   label: 'Chưa nhận xét (Đã quá hạn)' },
        ]}
        value={localFilters.hasComments}
        onChange={(v) => update('hasComments', v)}
      />

      {/* Giáo viên */}
      <SingleSelect
        label="Giáo viên"
        options={mentors.map((m) => ({ value: m, label: m }))}
        value={localFilters.mentor}
        onChange={(v) => update('mentor', v)}
      />

      {/* Khảo sát */}
      <SingleSelect
        label="Khảo sát"
        options={[
          { value: 'all', label: 'Tất cả' },
          { value: 'tp1', label: 'TP 1' },
          { value: 'tp2', label: 'TP 2' },
          { value: 'pending', label: 'Chưa thao tác' },
        ]}
        value={localFilters.tpRound}
        onChange={(v) => update('tpRound', v)}
      />

      {/* Checkpoint */}
      <SingleSelect
        label="Checkpoint"
        options={[
          { value: 'all', label: 'Tất cả' },
          { value: 'cp1', label: 'Checkpoint 1' },
          { value: 'cp2', label: 'Checkpoint 2' },
        ]}
        value={localFilters.cpRound}
        onChange={(v) => update('cpRound', v)}
      />

      {/* Reset */}
      <div className="filter-group">
        <label className="filter-label">&nbsp;</label>
        <button className="btn-reset" onClick={() => {
          const resetFilters: ClassFilters = {
            area: '', centre: '', startDate: '', startDateTo: '', endDate: '', endDateTo: '',
            slot: '', slotTo: '', course: '', search: '', status: [], hasComments: '', mentor: '', tpRound: '', cpRound: '', block: []
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

import { useState, useMemo, useEffect } from 'react'
import { useClasses } from '../hooks/useClasses'
import SingleSelect from '../components/SingleSelect'
import DatePickerInput from '../components/DatePickerInput'
import type { ClassItem, CRStudent } from '../types'
import { AREA_OPTIONS, centreMatchesArea, filterCentresByArea } from '../utils/areas'

// Lớp chính quy:
// - Có 2 phần: TL-JSB01, TL-CSB01 → ✅
// - Có 3+ phần, phần giữa (index 1) là mã khối hợp lệ: TL-ROB-ARMB13, 01TC-KIND-X01 → ✅
// - Có 3 phần, phần cuối là suffix học bù/online: TT-JSB15-HB, LBB-CSB07-ONL → ✅
// - Có 3+ phần, phần giữa khác: 01TC-THT-D30301 → ❌ đặc biệt
const VALID_BLOCK_CODES = new Set(['ROB', 'KIND', 'XART', 'C4K'])
const SUFFIX_CODES = new Set(['HB', 'ONL', 'HB2', 'HB3', 'ONL2'])

function isRegularClass(name: string): boolean {
  // Bỏ phần trong ngoặc như (1:1), (ONL) trước khi xử lý
  const cleaned = name.replace(/\s*\(.*?\)/g, '').trim()
  const parts = cleaned.split('-')
  if (parts.length < 2) return false
  if (parts.length === 2) return true  // TL-JSB01 → chính quy
  // 3+ phần: kiểm tra phần giữa (index 1)
  if (VALID_BLOCK_CODES.has(parts[1].toUpperCase())) return true
  // 3 phần: phần cuối là suffix học bù/online → chính quy
  if (parts.length === 3 && SUFFIX_CODES.has(parts[2].toUpperCase())) return true
  return false
}

interface CRFilters {
  area: string
  centre: string
  block: string
  mentor: string
  rateFilter: string  // 'high' = >=80%, 'low' = <80%
  endDateFrom: string
  endDateTo: string
}

function CRBar({ rate }: { rate: number }) {
  const color =
    rate >= 80 ? '#16a34a' :
    rate >= 50 ? '#d97706' : '#dc2626'
  return (
    <div className="cr-bar-wrap">
      <div className="cr-bar-track">
        <div className="cr-bar-fill" style={{ width: `${rate}%`, background: color }} />
      </div>
      <span className="cr-bar-label" style={{ color }}>{rate}%</span>
    </div>
  )
}

function cleanText(value: string | null | undefined) {
  if (value === null || value === undefined) return ''
  const text = String(value).trim()
  return text && text.toLowerCase() !== 'null' ? text : ''
}

function displayValue(value: string | number | boolean | null | undefined) {
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  return cleanText(value === undefined || value === null ? '' : String(value)) || '—'
}

function formatDate(value: string | null | undefined) {
  const text = cleanText(value)
  if (!text) return '—'
  const date = new Date(text)
  if (Number.isNaN(date.getTime())) return text
  return date.toLocaleDateString('vi-VN')
}

function humanizeStatus(value: string | null | undefined) {
  const status = cleanText(value)
  if (!status) return '—'
  const map: Record<string, string> = {
    ACTIVE: 'Active',
    COMPLETED: 'Complete',
    UNCOMPLETED: 'Incomplete',
    WAITING: 'Waiting',
    WAITING_CLASS: 'Waiting class',
    ON_HOLD: 'On hold',
  }
  return map[status.toUpperCase()] || status.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
}

function completionLabel(student: CRStudent) {
  const status = cleanText(student.completionInfo?.status)
  const reason = cleanText(student.completionInfo?.reason)
  if (status.toUpperCase() === 'COMPLETED') return 'Complete'
  if (reason) return humanizeStatus(reason)
  return humanizeStatus(status || student.student.status)
}

function completionPillClass(student: CRStudent) {
  const label = completionLabel(student).toLowerCase()
  const status = cleanText(student.completionInfo?.status).toUpperCase()
  if (status === 'COMPLETED' || label === 'complete' || label === 'completed') return 'cr-status-complete'
  if (label.includes('hold') || label.includes('waiting')) return 'cr-status-hold'
  if (status === 'UNCOMPLETED' || label.includes('incomplete')) return 'cr-status-incomplete'
  return 'cr-status-neutral'
}

function DetailItem({ label, value }: { label: string; value: string | number | boolean | null | undefined }) {
  return (
    <div className="cr-detail-item">
      <span className="cr-detail-label">{label}</span>
      <span className="cr-detail-value">{displayValue(value)}</span>
    </div>
  )
}

function StudentDetail({ item }: { item: CRStudent | null }) {
  if (!item) {
    return (
      <div className="cr-student-detail-empty">
        Chọn một học viên để xem thông tin chi tiết.
      </div>
    )
  }

  const student = item.student
  const customer = student.customer
  const previousClass = item.previousClass
  const firstTransfer = item.transfers?.[0]

  return (
    <div className="cr-student-detail">
      <div className="cr-student-detail-head">
        <div>
          <div className="cr-student-detail-name">{student.fullName || '—'}</div>
          <div className="cr-student-detail-sub">Mã HV {displayValue(student.studentId)}</div>
        </div>
        <span className={`cr-status-pill ${completionPillClass(item)}`}>{completionLabel(item)}</span>
      </div>

      <section className="cr-detail-section">
        <h3>Thông tin học viên</h3>
        <div className="cr-detail-grid">
          <DetailItem label="Ngày sinh" value={formatDate(student.dob)} />
          <DetailItem label="SĐT liên hệ" value={student.contactPhoneNumber} />
          <DetailItem label="Email" value={student.email} />
        </div>
        <DetailItem label="Địa chỉ" value={student.address} />
      </section>

      <section className="cr-detail-section">
        <h3>Phụ huynh</h3>
        <div className="cr-detail-grid">
          <DetailItem label="Họ tên" value={customer?.fullName} />
          <DetailItem label="Điện thoại" value={customer?.phoneNumber} />
          <DetailItem label="Email" value={customer?.email} />
          <DetailItem label="Zalo" value={customer?.zalo} />
        </div>
      </section>

      <section className="cr-detail-section">
        <h3>Thông tin trong lớp</h3>
        <div className="cr-detail-grid">
          <DetailItem label="Đang active" value={item.activeInClass} />
          <DetailItem label="Completion reason" value={humanizeStatus(item.completionInfo?.reason)} />
          <DetailItem label="Completion note" value={item.completionInfo?.note} />
          <DetailItem label="Completion description" value={item.completionInfo?.description} />
        </div>
      </section>

      <section className="cr-detail-section">
        <h3>Lớp học trước đó</h3>
        <div className="cr-detail-grid">
          <DetailItem label="Tên lớp" value={previousClass?.name || firstTransfer?.classFrom} />
          <DetailItem label="Ngày bắt đầu" value={formatDate(previousClass?.startDate || firstTransfer?.dateFrom)} />
          <DetailItem label="ID lớp" value={previousClass?.id || firstTransfer?.classFrom} />
        </div>
      </section>
    </div>
  )
}

function CRStudentsModal({ classItem, onClose }: { classItem: ClassItem; onClose: () => void }) {
  const initialStudents = classItem.students || []
  const [students, setStudents] = useState<CRStudent[]>(initialStudents)
  const [selectedStudent, setSelectedStudent] = useState<CRStudent | null>(initialStudents[0] || null)
  const [studentsLoading, setStudentsLoading] = useState(initialStudents.length === 0)
  const [studentsError, setStudentsError] = useState('')

  useEffect(() => {
    let cancelled = false
    const seedStudents = classItem.students || []
    setStudents(seedStudents)
    setSelectedStudent(seedStudents[0] || null)
    setStudentsError('')
    setStudentsLoading(seedStudents.length === 0)

    fetch(`/api/classes/${classItem.id}/students`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`)
        return data
      })
      .then((data: CRStudent[]) => {
        if (cancelled) return
        const nextStudents = Array.isArray(data) ? data : []
        setStudents(nextStudents)
        setSelectedStudent((current) => {
          if (!current) return nextStudents[0] || null
          return nextStudents.find((student) => student.id === current.id || student.student?.id === current.student?.id) || nextStudents[0] || null
        })
      })
      .catch((error) => {
        if (!cancelled) setStudentsError(error.message || 'Không tải được danh sách học viên.')
      })
      .finally(() => {
        if (!cancelled) setStudentsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [classItem.id, classItem.students])

  const completed = students.filter((student) => cleanText(student.completionInfo?.status).toUpperCase() === 'COMPLETED').length

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="cr-modal-wrap" onClick={(e) => e.stopPropagation()}>
        <div className="cr-modal-banner">
          <div className="cr-modal-banner-text">
            <p className="cr-modal-banner-sub">{classItem.centre || '—'} · {classItem.teachers[0]?.name || '—'}</p>
            <h2 className="cr-modal-banner-title">{classItem.name}</h2>
          </div>
          <div className="cr-modal-side">
            <div className="cr-modal-kpis">
              <div className="cr-modal-kpi">
                <span>{classItem.completionRate}%</span>
                <small>CPR</small>
              </div>
              <div className="cr-modal-kpi">
                <span>{completed}/{classItem.attendedCount || students.length}</span>
                <small>Complete</small>
              </div>
            </div>
            <button className="cr-modal-close" type="button" onClick={onClose} aria-label="Đóng">×</button>
          </div>
        </div>

        {studentsLoading ? (
          <div className="cr-modal-empty">
            Đang tải danh sách học viên...
          </div>
        ) : students.length === 0 ? (
          <div className="cr-modal-empty">
            {studentsError
              ? `Không tải được danh sách học viên: ${studentsError}`
              : 'Chưa có dữ liệu học viên cho lớp này.'}
          </div>
        ) : (
          <div className="cr-modal-body">
            <div className="cr-student-list">
              <div className="cr-student-list-head">
                <span>Học viên</span>
                <strong>{students.length}</strong>
              </div>
              <div className="cr-student-list-scroll">
                {students.map((student, index) => (
                  <button
                    key={student.id || `${student.student?.id}-${index}`}
                    type="button"
                    className={`cr-student-row ${selectedStudent?.id === student.id ? 'cr-student-row-active' : ''}`}
                    onClick={() => setSelectedStudent(student)}
                  >
                    <span className="cr-student-index">{index + 1}</span>
                    <span className="cr-student-main">
                      <span className="cr-student-name">{student.student.fullName || '—'}</span>
                      <span className="cr-student-code">{student.student.studentId || student.student.id || '—'}</span>
                    </span>
                    <span className={`cr-status-pill ${completionPillClass(student)}`}>{completionLabel(student)}</span>
                  </button>
                ))}
              </div>
            </div>
            <StudentDetail item={selectedStudent} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function CRPage() {
  const { classes, loading, error } = useClasses({ includeSlots: false })
  const [filters, setFilters] = useState<CRFilters>({ area: '', centre: '', block: '', mentor: '', rateFilter: '', endDateFrom: '', endDateTo: '' })
  const [selectedClass, setSelectedClass] = useState<ClassItem | null>(null)

  // Chỉ lấy lớp FINISHED và chính quy
  const finishedClasses = useMemo(
    () => classes.filter((c) => c.status === 'FINISHED' && isRegularClass(c.name)),
    [classes]
  )

  // Options cho bộ lọc
  const { centres, blocks, mentors } = useMemo(() => {
    const cs = new Set<string>()
    const bs = new Set<string>()
    const ms = new Set<string>()
    finishedClasses.forEach((c) => {
      if (c.centre) cs.add(c.centre)
      if (c.block) bs.add(c.block)
      c.teachers.forEach((t) => ms.add(t.name))
    })
    return {
      centres: Array.from(cs).sort(),
      blocks: Array.from(bs).sort(),
      mentors: Array.from(ms).sort(),
    }
  }, [finishedClasses])

  const update = (key: keyof CRFilters, value: string) =>
    setFilters((f) => ({ ...f, [key]: value }))

  const updateArea = (area: string) =>
    setFilters((f) => ({
      ...f,
      area,
      centre: area && !centreMatchesArea(f.centre, area) ? '' : f.centre,
    }))

  const centreOptions = useMemo(() => filterCentresByArea(centres, filters.area), [centres, filters.area])

  const resetFilters = () => setFilters({ area: '', centre: '', block: '', mentor: '', rateFilter: '', endDateFrom: '', endDateTo: '' })

  // Áp dụng bộ lọc
  const filtered = useMemo(() => {
    return finishedClasses.filter((c) => {
      if (filters.centre && c.centre !== filters.centre) return false
      if (filters.area && !centreMatchesArea(c.centre, filters.area)) return false
      if (filters.block && c.block !== filters.block) return false
      if (filters.mentor && !c.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.rateFilter === 'high' && c.completionRate < 80) return false
      if (filters.rateFilter === 'low' && c.completionRate >= 80) return false

      // Lọc theo ngày kết thúc (endDate)
      if ((filters.endDateFrom || filters.endDateTo) && c.endDate) {
        const endDate = new Date(c.endDate)
        const endDateStr = endDate.getFullYear() + '-' +
          String(endDate.getMonth() + 1).padStart(2, '0') + '-' +
          String(endDate.getDate()).padStart(2, '0')

        if (filters.endDateFrom && filters.endDateTo) {
          if (filters.endDateFrom === filters.endDateTo) {
            if (endDateStr !== filters.endDateFrom) return false
          } else {
            if (endDateStr < filters.endDateFrom || endDateStr > filters.endDateTo) return false
          }
        } else if (filters.endDateFrom) {
          if (endDateStr < filters.endDateFrom) return false
        } else if (filters.endDateTo) {
          if (endDateStr > filters.endDateTo) return false
        }
      }

      return true
    })
  }, [finishedClasses, filters])

  // Tổng CR HCM4 — tính theo filtered (đã áp dụng bộ lọc khối/cơ sở/...)
  // Chỉ tính các cơ sở thuộc HCM4
  const hcm4Stats = useMemo(() => {
    const hcm4 = filtered.filter((c) =>
      centreMatchesArea(c.centre, 'HCM4')
    )
    const totalAttended = hcm4.reduce((s, c) => s + c.attendedCount, 0)
    const totalCompleted = hcm4.reduce((s, c) => s + c.completedCount, 0)
    const rate = totalAttended > 0 ? Math.round((totalCompleted / totalAttended) * 100) : 0
    return { totalAttended, totalCompleted, rate, classCount: hcm4.length }
  }, [filtered])

  if (loading) return <div className="state-msg">Đang tải dữ liệu...</div>
  if (error) return (
    <div className="state-msg error">
      Không tải được dữ liệu.<br />
      Hãy chạy <code>python main.py</code> để lấy data trước.
    </div>
  )
  if (classes.length === 0) return (
    <div className="state-msg">
      Chưa có dữ liệu. Hãy chạy <code>python main.py</code> để lấy data.
    </div>
  )

  return (
    <div className="page">
      {/* Header */}
      <div className="page-banner cr-page-banner">
        <div className="cr-banner-left">
          <div>
            <h1 className="page-banner-title">Quản lý CPR</h1>
            <p className="page-banner-sub">Completion Rate</p>
          </div>
          <span className="page-banner-badge">{filtered.length} / {finishedClasses.length} lớp</span>
        </div>
        {/* HCM4 tổng CR — góc phải */}
        <div className="hcm4-summary">
          <div className="hcm4-label">Tổng CPR HCM 4</div>
          <div className="hcm4-rate" style={{
            color: hcm4Stats.rate >= 80 ? '#16a34a' : hcm4Stats.rate >= 50 ? '#d97706' : '#dc2626'
          }}>
            {hcm4Stats.rate}%
          </div>
          <div className="hcm4-sub">
            {hcm4Stats.totalCompleted}/{hcm4Stats.totalAttended} HV &middot; {hcm4Stats.classCount} lớp
          </div>
        </div>
      </div>

      {/* Bộ lọc */}
      <div className="filters-container">
        <SingleSelect
          label="Khu vực"
          options={AREA_OPTIONS}
          value={filters.area}
          onChange={updateArea}
        />
        <SingleSelect
          label="Cơ sở"
          options={centreOptions.map((c) => ({ value: c, label: c }))}
          value={filters.centre}
          onChange={(v) => update('centre', v)}
        />
        <SingleSelect
          label="Khối"
          options={blocks.map((b) => ({ value: b, label: b }))}
          value={filters.block}
          onChange={(v) => update('block', v)}
        />
        <SingleSelect
          label="Giáo viên"
          options={mentors.map((m) => ({ value: m, label: m }))}
          value={filters.mentor}
          onChange={(v) => update('mentor', v)}
        />
        <SingleSelect
          label="Tỉ lệ CPR"
          options={[
            { value: 'high', label: 'Từ 80% trở lên' },
            { value: 'low', label: 'Dưới 80%' },
          ]}
          value={filters.rateFilter}
          onChange={(v) => update('rateFilter', v)}
        />
        <DatePickerInput
          label="Ngày kết thúc"
          value={{ from: filters.endDateFrom, to: filters.endDateTo }}
          onChange={(from, to) => setFilters(f => ({ ...f, endDateFrom: from, endDateTo: to }))}
        />
        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={resetFilters}>Xóa bộ lọc</button>
        </div>
      </div>

      {/* Bảng CR */}
      {filtered.length === 0 ? (
        <div className="state-msg">Không có lớp nào phù hợp.</div>
      ) : (
        <div className="cr-table-wrapper">
          <table className="cr-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Tên lớp</th>
                <th>Cơ sở</th>
                <th>Khối</th>
                <th>Khóa học</th>
                <th>Giáo viên</th>
                <th>Tổng HV</th>
                <th>HV đi học</th>
                <th>Completed</th>
                <th>Completion Rate</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <CRRow key={c.id} item={c} index={i + 1} onSelect={() => setSelectedClass(c)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {selectedClass && (
        <CRStudentsModal classItem={selectedClass} onClose={() => setSelectedClass(null)} />
      )}
    </div>
  )
}

function CRRow({ item, index, onSelect }: { item: ClassItem; index: number; onSelect: () => void }) {
  return (
    <tr className="cr-class-row" onClick={onSelect} tabIndex={0} onKeyDown={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        onSelect()
      }
    }}>
      <td className="cr-td-num">{index}</td>
      <td className="cr-td-name">{item.name}</td>
      <td>{item.centre || '—'}</td>
      <td>{item.block || '—'}</td>
      <td>{item.course || '—'}</td>
      <td>{item.teachers[0]?.name || '—'}</td>
      <td className="cr-td-center">{item.studentCount}</td>
      <td className="cr-td-center">{item.attendedCount}</td>
      <td className="cr-td-center">{item.completedCount}</td>
      <td className="cr-td-bar">
        <CRBar rate={item.completionRate} />
      </td>
    </tr>
  )
}

import { useState, useMemo } from 'react'
import { useOH } from '../hooks/useOH'
import SingleSelect from '../components/SingleSelect'
import DatePickerInput from '../components/DatePickerInput'
import type { OHRecord, OHAppointment } from '../types'

// ── Helpers ────────────────────────────────────────────────────────────────

const APPT_STATUS_MAP: Record<string, string> = {
  WAITING:  'WAITING',
  CANCELED: 'CANCELED',
  FAIL:     'FAIL',
  PASSED:   'PASSED',
}

const APPT_STATUS_COLOR: Record<string, string> = {
  WAITING:  'oh-badge-waiting',
  CANCELED: 'oh-badge-cancled',
  FAIL:     'oh-badge-fail',
  PASSED:   'oh-badge-passed',
}

function fmtTime(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function fmtDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}


// Bộ môn = courseLines[].name
function getSubject(record: OHRecord): string {
  if (record.courseLines.length > 0) return record.courseLines.map(cl => cl.name).join(', ')
  return '—'
}

// Khóa học (case trải nghiệm) = courses[].name
function getCourse(record: OHRecord): string {
  if (record.courses.length > 0) return record.courses.map(c => c.name).join(', ')
  return '—'
}

// Tổng hợp trạng thái appointments của 1 OH
function getOHStatusSummary(record: OHRecord): { passed: number; fail: number; waiting: number; canceled: number } {
  const summary = { passed: 0, fail: 0, waiting: 0, canceled: 0 }
  for (const a of record.appointments) {
    if (a.status === 'PASSED') summary.passed++
    else if (a.status === 'FAIL') summary.fail++
    else if (a.status === 'WAITING') summary.waiting++
    else if (a.status === 'CANCELED') summary.canceled++
  }
  return summary
}

// ── Modal chi tiết ─────────────────────────────────────────────────────────

function OHModal({ record, onClose }: { record: OHRecord; onClose: () => void }) {
  const subject   = getSubject(record)
  const course    = getCourse(record)
  const centre    = record.centre?.name?.replace('HCM - ', '') ?? '—'
  const teacher   = record.teacher?.fullName ?? '—'
  const timeRange = `${fmtTime(record.startTime)} – ${fmtTime(record.endTime)}`
  const dateStr   = fmtDate(record.startTime)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="oh-modal-wrap" onClick={(e) => e.stopPropagation()}>

        {/* Banner */}
        <div className="oh-modal-banner">
          <div className="oh-modal-banner-text">
            <p className="oh-modal-banner-sub">{centre} · {dateStr} · {timeRange}</p>
            <h2 className="oh-modal-banner-title">{course}</h2>
            <p className="oh-modal-banner-meta">{subject} · {teacher}</p>
          </div>
          <div className="oh-modal-banner-count">
            <span className="oh-modal-banner-num">{record.appointments.length}</span>
            <span className="oh-modal-banner-num-label">HV</span>
          </div>
        </div>

        {/* Info grid */}
        <div className="oh-modal-info">
          <div className="oh-info-item">
            <span className="oh-info-label">Cơ sở</span>
            <span className="oh-info-value">{record.centre?.name ?? '—'}</span>
          </div>
          <div className="oh-info-item">
            <span className="oh-info-label">Giáo viên</span>
            <span className="oh-info-value">{teacher}</span>
          </div>
          <div className="oh-info-item">
            <span className="oh-info-label">Bộ môn</span>
            <span className="oh-info-value">{subject}</span>
          </div>
          <div className="oh-info-item">
            <span className="oh-info-label">Khung giờ</span>
            <span className="oh-info-value">{timeRange} · {dateStr}</span>
          </div>
          <div className="oh-info-item">
            <span className="oh-info-label">Loại</span>
            <span className="oh-info-value">{record.type || '—'}</span>
          </div>
          <div className="oh-info-item">
            <span className="oh-info-label">Tạo bởi</span>
            <span className="oh-info-value">{record.createdBy?.username ?? '—'}</span>
          </div>
          {record.note && (
            <div className="oh-info-item oh-info-full">
              <span className="oh-info-label">Note tư vấn</span>
              <span className="oh-info-value">{record.note}</span>
            </div>
          )}
          {record.managerNote && (
            <div className="oh-info-item oh-info-full">
              <span className="oh-info-label">Note quản lý</span>
              <span className="oh-info-value">{record.managerNote}</span>
            </div>
          )}
        </div>

        {/* Appointments */}
        {record.appointments.length > 0 && (
          <div className="oh-modal-appts">
            <div className="oh-modal-appts-title">
              Case trải nghiệm · {record.appointments.length} học viên
            </div>
            <div className="oh-appt-list">
              {record.appointments.map((appt, i) => (
                <AppointmentRow key={appt.id} appt={appt} index={i + 1} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function AppointmentRow({ appt, index }: { appt: OHAppointment; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const statusLabel = APPT_STATUS_MAP[appt.status] ?? appt.status
  const statusCls   = APPT_STATUS_COLOR[appt.status] ?? 'oh-badge-waiting'
  const hasNote = Boolean(appt.note)

  return (
    <div className="oh-appt-row">
      <div
        className={`oh-appt-header ${hasNote ? 'oh-appt-header-clickable' : ''}`}
        onClick={() => hasNote && setExpanded(e => !e)}
      >
        <span className="oh-appt-idx">{index}</span>
        <div className="oh-appt-info">
          {/* title = case trải nghiệm */}
          <span className="oh-appt-name">{appt.candidate?.fullName ?? '—'}</span>
          <span className="oh-appt-title">{appt.title || '—'}</span>
        </div>
        <span className={`oh-badge ${statusCls}`}>{statusLabel}</span>
        {hasNote && (
          <span className="oh-appt-expand">{expanded ? '▲' : '▼'}</span>
        )}
      </div>
      {expanded && appt.note && (
        <div className="oh-appt-note">{appt.note}</div>
      )}
    </div>
  )
}

// ── Summary Modal ──────────────────────────────────────────────────────────

function OHSummaryModal({ records, onClose }: { records: OHRecord[]; onClose: () => void }) {
  const totalAppts = records.reduce((s, r) => s + r.appointments.length, 0)
  let passed = 0, fail = 0, waiting = 0, canceled = 0
  records.forEach(r => r.appointments.forEach(a => {
    if (a.status === 'PASSED') passed++
    else if (a.status === 'FAIL') fail++
    else if (a.status === 'WAITING') waiting++
    else if (a.status === 'CANCELED') canceled++
  }))

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={e => e.stopPropagation()}>
        <div className="summary-banner" style={{ paddingTop: 35, paddingBottom: 35 }}>
          <div>
            <h2 className="summary-banner-title">Tổng hợp OH</h2>
            <p className="summary-banner-sub">Office Hours</p>
          </div>
          <span className="summary-banner-badge">{records.length} OH · {totalAppts} HV</span>
        </div>
        <div className="summary-table-wrapper">
          <table className="summary-table">
            <thead>
              <tr>
                <th className="summary-fixed-col">#</th>
                <th className="summary-fixed-col">Ngày · Giờ</th>
                <th>Cơ sở</th>
                <th>Giáo viên</th>
                <th style={{ textAlign: 'center' }}>HV</th>
                <th style={{ textAlign: 'center' }}>PASSED</th>
                <th style={{ textAlign: 'center' }}>FAIL</th>
                <th style={{ textAlign: 'center' }}>WAITING</th>
                <th style={{ textAlign: 'center' }}>CANCELED</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r, i) => {
                const s = getOHStatusSummary(r)
                return (
                  <tr key={r.id}>
                    <td>{i + 1}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {fmtDate(r.startTime)}<br />
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{fmtTime(r.startTime)}–{fmtTime(r.endTime)}</span>
                    </td>
                    <td>{r.centre?.name?.replace('HCM - ', '') ?? '—'}</td>
                    <td>{r.teacher?.fullName ?? '—'}</td>
                    <td style={{ textAlign: 'center' }}>{r.appointments.length}</td>
                    <td style={{ textAlign: 'center', color: s.passed > 0 ? '#16a34a' : undefined, fontWeight: s.passed > 0 ? 700 : undefined }}>{s.passed || '—'}</td>
                    <td style={{ textAlign: 'center', color: s.fail > 0 ? '#dc2626' : undefined, fontWeight: s.fail > 0 ? 700 : undefined }}>{s.fail || '—'}</td>
                    <td style={{ textAlign: 'center', color: s.waiting > 0 ? '#d97706' : undefined }}>{s.waiting || '—'}</td>
                    <td style={{ textAlign: 'center', color: s.canceled > 0 ? '#6b7280' : undefined }}>{s.canceled || '—'}</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr style={{ fontWeight: 700, background: '#f9fafb' }}>
                <td colSpan={4} style={{ textAlign: 'right', paddingRight: 12 }}>Tổng</td>
                <td style={{ textAlign: 'center' }}>{totalAppts}</td>
                <td style={{ textAlign: 'center', color: '#16a34a' }}>{passed}</td>
                <td style={{ textAlign: 'center', color: '#dc2626' }}>{fail}</td>
                <td style={{ textAlign: 'center', color: '#d97706' }}>{waiting}</td>
                <td style={{ textAlign: 'center', color: '#6b7280' }}>{canceled}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────

interface OHFilters {
  centre: string
  teacher: string
  subject: string
  apptStatus: string
  dateFrom: string
  dateTo: string
}

export default function OHPage() {
  const { ohData, loading, error } = useOH()
  const [filters, setFilters] = useState<OHFilters>({
    centre: '', teacher: '', subject: '', apptStatus: '', dateFrom: '', dateTo: '',
  })
  const [selected, setSelected] = useState<OHRecord | null>(null)
  const [showSummary, setShowSummary] = useState(false)

  const update = (key: keyof OHFilters, v: string) =>
    setFilters(f => ({ ...f, [key]: v }))

  const resetFilters = () =>
    setFilters({ centre: '', teacher: '', subject: '', apptStatus: '', dateFrom: '', dateTo: '' })

  // Build filter options
  const { centres, teachers, subjects } = useMemo(() => {
    const cs = new Set<string>()
    const ts = new Set<string>()
    const ss = new Set<string>()
    ohData.forEach(r => {
      if (r.centre?.name) cs.add(r.centre.name.replace('HCM - ', ''))
      if (r.teacher?.fullName) ts.add(r.teacher.fullName)
      // Bộ môn = courseLines
      r.courseLines.forEach(cl => ss.add(cl.name))
    })
    return {
      centres: Array.from(cs).sort(),
      teachers: Array.from(ts).sort(),
      subjects: Array.from(ss).sort(),
    }
  }, [ohData])

  // Stats
  const stats = useMemo(() => {
    let passed = 0, fail = 0, waiting = 0, canceled = 0
    ohData.forEach(r => {
      r.appointments.forEach(a => {
        if (a.status === 'PASSED') passed++
        else if (a.status === 'FAIL') fail++
        else if (a.status === 'WAITING') waiting++
        else if (a.status === 'CANCELED') canceled++
      })
    })
    return { passed, fail, waiting, canceled, total: passed + fail + waiting + canceled }
  }, [ohData])

  // Apply filters
  const filtered = useMemo(() => {
    return ohData.filter(r => {
      const subject = getSubject(r)
      const centreName = r.centre?.name?.replace('HCM - ', '') ?? ''

      if (filters.centre && centreName !== filters.centre) return false
      if (filters.teacher && r.teacher?.fullName !== filters.teacher) return false
      if (filters.subject && !subject.includes(filters.subject)) return false

      if (filters.apptStatus) {
        const hasStatus = r.appointments.some(a => a.status === filters.apptStatus)
        if (!hasStatus) return false
      }

      // Lọc theo ngày diễn ra
      if (filters.dateFrom || filters.dateTo) {
        const slotDate = new Date(r.startTime)
        const slotDateStr = slotDate.getFullYear() + '-' +
          String(slotDate.getMonth() + 1).padStart(2, '0') + '-' +
          String(slotDate.getDate()).padStart(2, '0')
        if (filters.dateFrom && filters.dateTo) {
          if (filters.dateFrom === filters.dateTo) {
            if (slotDateStr !== filters.dateFrom) return false
          } else {
            if (slotDateStr < filters.dateFrom || slotDateStr > filters.dateTo) return false
          }
        } else if (filters.dateFrom) {
          if (slotDateStr < filters.dateFrom) return false
        } else if (filters.dateTo) {
          if (slotDateStr > filters.dateTo) return false
        }
      }

      return true
    })
  }, [ohData, filters])

  if (loading) return <div className="state-msg">Đang tải dữ liệu...</div>
  if (error) return (
    <div className="state-msg error">
      Không tải được dữ liệu OH.<br />
      <code>{error}</code>
    </div>
  )
  if (ohData.length === 0) return (
    <div className="state-msg">Chưa có dữ liệu OH.</div>
  )

  return (
    <div className="page">
      {/* Banner */}
      <div className="oh-page-banner">
        <div>
          <h1 className="oh-page-banner-title">Quản lý OH</h1>
          <p className="oh-page-banner-sub">Office Hours</p>
        </div>
        <div className="oh-stats-row">
          <div className="oh-stat">
            <span className="oh-stat-num oh-stat-passed">{stats.passed}</span>
            <span className="oh-stat-label">PASSED</span>
          </div>
          <div className="oh-stat">
            <span className="oh-stat-num oh-stat-fail">{stats.fail}</span>
            <span className="oh-stat-label">FAIL</span>
          </div>
          <div className="oh-stat">
            <span className="oh-stat-num oh-stat-waiting">{stats.waiting}</span>
            <span className="oh-stat-label">WAITING</span>
          </div>
          <div className="oh-stat">
            <span className="oh-stat-num oh-stat-cancled">{stats.canceled}</span>
            <span className="oh-stat-label">CANCELED</span>
          </div>
        </div>
        <span className="oh-page-badge">{filtered.length} / {ohData.length} OH</span>
      </div>

      {/* Filters */}
      <div className="filters-container">
        <DatePickerInput
          label="Ngày diễn ra"
          value={{ from: filters.dateFrom, to: filters.dateTo }}
          onChange={(from, to) => setFilters(f => ({ ...f, dateFrom: from, dateTo: to }))}
        />
        <SingleSelect
          label="Cơ sở"
          options={centres.map(c => ({ value: c, label: c }))}
          value={filters.centre}
          onChange={v => update('centre', v)}
        />
        <SingleSelect
          label="Giáo viên"
          options={teachers.map(t => ({ value: t, label: t }))}
          value={filters.teacher}
          onChange={v => update('teacher', v)}
        />
        <SingleSelect
          label="Bộ môn"
          options={subjects.map(s => ({ value: s, label: s }))}
          value={filters.subject}
          onChange={v => update('subject', v)}
        />
        <SingleSelect
          label="Trạng thái"
          options={[
            { value: 'WAITING',  label: 'WAITING' },
            { value: 'PASSED',   label: 'PASSED' },
            { value: 'FAIL',     label: 'FAIL' },
            { value: 'CANCELED', label: 'CANCELED' },
          ]}
          value={filters.apptStatus}
          onChange={v => update('apptStatus', v)}
        />
        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={resetFilters}>Xóa bộ lọc</button>
        </div>
        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-summary" onClick={() => setShowSummary(true)}>📋 Tổng hợp</button>
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="state-msg">Không có OH nào phù hợp.</div>
      ) : (
        <div className="cr-table-wrapper">
          <table className="cr-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Ngày · Giờ</th>
                <th>Cơ sở</th>
                <th>Bộ môn</th>
                <th>Khóa học</th>
                <th>Giáo viên</th>
                <th style={{ textAlign: 'center' }}>HV</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => {
                const summary = getOHStatusSummary(r)
                return (
                  <tr key={r.id} onClick={() => setSelected(r)} style={{ cursor: 'pointer' }}>
                    <td className="cr-td-num">{i + 1}</td>
                    <td className="oh-td-time">
                      <span className="oh-td-date">{fmtDate(r.startTime)}</span>
                      <span className="oh-td-slot">{fmtTime(r.startTime)}–{fmtTime(r.endTime)}</span>
                    </td>
                    <td>{r.centre?.name?.replace('HCM - ', '') ?? '—'}</td>
                    <td>{getSubject(r)}</td>
                    <td className="cr-td-name">{getCourse(r)}</td>
                    <td>{r.teacher?.fullName ?? '—'}</td>
                    <td className="cr-td-center">{r.appointments.length}</td>
                    <td>
                      <div className="oh-status-pills">
                        {summary.passed  > 0 && <span className="oh-badge oh-badge-passed">{summary.passed} PASSED</span>}
                        {summary.fail    > 0 && <span className="oh-badge oh-badge-fail">{summary.fail} FAIL</span>}
                        {summary.waiting > 0 && <span className="oh-badge oh-badge-waiting">{summary.waiting} WAITING</span>}
                        {summary.canceled > 0 && <span className="oh-badge oh-badge-cancled">{summary.canceled} CANCELED</span>}
                        {r.appointments.length === 0 && <span className="oh-badge oh-badge-waiting">—</span>}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected && <OHModal record={selected} onClose={() => setSelected(null)} />}
      {showSummary && <OHSummaryModal records={filtered} onClose={() => setShowSummary(false)} />}
    </div>
  )
}

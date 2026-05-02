import { useState, useMemo } from 'react'
import { useTeachers } from '../hooks/useTeachers'
import MultiSelect from '../components/MultiSelect'
import type { TeacherItem } from '../types'

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function genderLabel(g: string | null): string {
  if (g === 'MALE') return 'Nam'
  if (g === 'FEMALE') return 'Nữ'
  return '—'
}

function blockLabelStyle(block: string) {
  if (block === 'Robotics') return { background: '#facc15', color: '#111' }
  if (block === 'Coding') return { background: '#bfdbfe', color: '#1d4ed8' }
  if (block === 'Art') return { background: '#fecaca', color: '#991b1b' }
  return { background: '#e5e7eb', color: '#374151' }
}

// ── Teacher Card ─────────────────────────────────────────────────────────────

function TeacherCard({ teacher, onClick }: { teacher: TeacherItem; onClick: () => void }) {
  return (
    <div className="card" onClick={onClick}>
      <div className="card-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <h3 className="card-title" style={{ margin: 0 }}>{teacher.fullName}</h3>
            {teacher.blocks.map((b) => (
              <span key={b} className="teacher-block" style={blockLabelStyle(b)}>{b}</span>
            ))}
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>@{teacher.username}</p>
        </div>
      </div>

      {teacher.email && <p className="card-meta">✉️ {teacher.email}</p>}
      {teacher.phoneNumber && <p className="card-meta">📞 {teacher.phoneNumber}</p>}

      {teacher.centres.length > 0 && (
        <p className="card-meta" style={{ marginTop: 6 }}>
          🏢 {teacher.centres.join(', ')}
        </p>
      )}
    </div>
  )
}

// ── Teacher Detail Modal ──────────────────────────────────────────────────────

function TeacherDetail({ teacher, onClose }: { teacher: TeacherItem; onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <h2 className="modal-title" style={{ marginBottom: 0 }}>{teacher.fullName}</h2>
            {teacher.blocks.length > 0 && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {teacher.blocks.map((b) => (
                  <span key={b} className="teacher-block" style={blockLabelStyle(b)}>{b}</span>
                ))}
              </div>
            )}
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>@{teacher.username} · {teacher.code}</p>
          <div className="modal-divider" />
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Email</span>
              <span className="detail-value">{teacher.email || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Số điện thoại</span>
              <span className="detail-value">{teacher.phoneNumber || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Giới tính</span>
              <span className="detail-value">{genderLabel(teacher.gender)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Ngày sinh</span>
              <span className="detail-value">{formatDate(teacher.dob)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Địa chỉ</span>
              <span className="detail-value">{teacher.address || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Ngày vào làm</span>
              <span className="detail-value">{formatDate(teacher.joinedDate)}</span>
            </div>
          </div>

          {teacher.centres.length > 0 && (
            <div className="detail-section">
              <h3>Cơ sở</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {teacher.centres.map((c, i) => (
                  <div key={i} className="teacher-item">
                    <span className="teacher-name">🏢 {c}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

interface TeacherFilters {
  search: string
  centres: string[]
  blocks: string[]
  birthMonth: string  // '1' - '12' hoặc ''
}

const MONTH_LABELS = [
  '', 'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4',
  'Tháng 5', 'Tháng 6', 'Tháng 7', 'Tháng 8',
  'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
]

// ── Summary Modal ─────────────────────────────────────────────────────────────

function SummaryModal({ teachers, onClose }: { teachers: TeacherItem[]; onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={(e) => e.stopPropagation()}>
        <div className="summary-banner">
          <div>
            <h2 className="summary-banner-title">Tổng hợp</h2>
            <p className="summary-banner-sub">Danh sách giáo viên</p>
          </div>
          <span className="summary-banner-badge">{teachers.length} giáo viên</span>
        </div>
        <div className="summary-table-wrapper">
          <table className="summary-table teacher-summary-table">
            <thead>
              <tr>
                <th className="summary-fixed-col">#</th>
                <th className="summary-fixed-col">Họ tên</th>
                <th>Email</th>
                <th>SĐT</th>
                <th>Khối</th>
                <th>Cơ sở</th>
              </tr>
            </thead>
            <tbody>
              {teachers.map((t, i) => (
                  <tr key={t.id}>
                    <td>{i + 1}</td>
                    <td><span className="summary-name summary-nowrap">{t.fullName}</span></td>
                    <td>{t.email || '—'}</td>
                    <td>{t.phoneNumber || '—'}</td>
                    <td>{t.blocks.join(', ') || '—'}</td>
                    <td className="summary-centres">
                      {t.centres.length > 0 ? t.centres.map((centre, idx) => (
                        <div key={idx}>{centre}</div>
                      )) : '—'}
                    </td>
                  </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function MentorsPage() {
  const { teachers, loading, error } = useTeachers()
  const [filters, setFilters] = useState<TeacherFilters>({ search: '', centres: [], blocks: [], birthMonth: '' })
  const [selectedTeacher, setSelectedTeacher] = useState<TeacherItem | null>(null)
  const [showSummary, setShowSummary] = useState(false)

  // Extract unique centres from data
  const { centreOptions, blockOptions } = useMemo(() => {
    const cs = new Set<string>()
    teachers.forEach((t) => t.centres.forEach((c) => cs.add(c)))
    return {
      centreOptions: Array.from(cs).sort(),
      blockOptions: ['Art', 'Robotics', 'Coding'],
    }
  }, [teachers])

  const update = (key: keyof TeacherFilters, value: any) =>
    setFilters((f) => ({ ...f, [key]: value }))

  // Apply filters
  const filtered = useMemo(() => {
    return teachers.filter((t) => {
      if (filters.search) {
        const q = filters.search.toLowerCase()
        if (!t.fullName.toLowerCase().includes(q)) return false
      }
      if (filters.centres.length > 0 && !filters.centres.some((c) => t.centres.includes(c))) return false
      if (filters.blocks.length > 0 && !filters.blocks.some((b) => t.blocks.includes(b))) return false
      if (filters.birthMonth) {
        if (!t.dob) return false
        const month = new Date(t.dob).getMonth() + 1  // getMonth() trả về 0-11
        if (month !== parseInt(filters.birthMonth)) return false
      }
      return true
    })
  }, [teachers, filters])

  if (loading) return <div className="state-msg">Đang tải dữ liệu...</div>

  if (error) return (
    <div className="state-msg error">
      Không tải được dữ liệu.<br />
      Hãy chạy <code>python main.py</code> để lấy data trước.
    </div>
  )

  if (teachers.length === 0) return (
    <div className="state-msg">
      Chưa có dữ liệu. Hãy chạy <code>python main.py</code> để lấy data.
    </div>
  )

  return (
    <div className="page">
      <div className="page-banner">
        <div>
          <h1 className="page-banner-title">Quản lý giáo viên</h1>
          <p className="page-banner-sub">Danh sách giáo viên HCM4</p>
        </div>
        <span className="page-banner-badge">{filtered.length} / {teachers.length} giáo viên</span>
      </div>

      {/* Bộ lọc */}
      <div className="filters-container">
        {/* Search */}
        <div className="filter-group">
          <label className="filter-label">Tìm kiếm</label>
          <div className="search-input-wrap">
            <input
              type="text"
              placeholder="Tìm theo tên giáo viên..."
              value={filters.search}
              onChange={(e) => update('search', e.target.value)}
              className="search-input"
            />
            {filters.search && (
              <button className="search-clear" onClick={() => update('search', '')}>✕</button>
            )}
          </div>
        </div>

        <MultiSelect
          label="Cơ sở"
          options={centreOptions}
          selected={filters.centres}
          onChange={(val) => update('centres', val)}
          placeholder="Tất cả"
        />

        <MultiSelect
          label="Khối"
          options={blockOptions}
          selected={filters.blocks}
          onChange={(val) => update('blocks', val)}
          placeholder="Tất cả"
        />

        <div className="filter-group">
          <label className="filter-label">Tháng sinh</label>
          <select value={filters.birthMonth} onChange={(e) => update('birthMonth', e.target.value)}>
            <option value="">Tất cả</option>
            {MONTH_LABELS.slice(1).map((label, i) => (
              <option key={i + 1} value={String(i + 1)}>{label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={() => setFilters({ search: '', centres: [], blocks: [], birthMonth: '' })}>
            Xóa bộ lọc
          </button>
        </div>

        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-summary" onClick={() => setShowSummary(true)}>
            📋 Tổng hợp
          </button>
        </div>
      </div>

      {/* Cards */}
      <div className="card-grid">
        {filtered.map((t) => (
          <TeacherCard key={t.id} teacher={t} onClick={() => setSelectedTeacher(t)} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="state-msg">Không có giáo viên nào phù hợp.</div>
      )}

      {selectedTeacher && (
        <TeacherDetail teacher={selectedTeacher} onClose={() => setSelectedTeacher(null)} />
      )}

      {showSummary && (
        <SummaryModal teachers={filtered} onClose={() => setShowSummary(false)} />
      )}
    </div>
  )
}

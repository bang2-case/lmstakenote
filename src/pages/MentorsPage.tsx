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

// ── Teacher Card ─────────────────────────────────────────────────────────────

function TeacherCard({ teacher, onClick }: { teacher: TeacherItem; onClick: () => void }) {
  const pointColor =
    teacher.teacherPoint >= 8 ? '#16a34a' :
    teacher.teacherPoint >= 5 ? '#d97706' : '#dc2626'

  return (
    <div className="card" onClick={onClick}>
      <div className="card-header">
        <div>
          <h3 className="card-title">{teacher.fullName}</h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>@{teacher.username}</p>
        </div>
        <div style={{
          minWidth: 40, height: 40, borderRadius: '50%',
          background: pointColor, color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 14, flexShrink: 0
        }}>
          {teacher.teacherPoint}
        </div>
      </div>

      {teacher.email && <p className="card-meta">✉️ {teacher.email}</p>}
      {teacher.phoneNumber && <p className="card-meta">📞 {teacher.phoneNumber}</p>}

      {teacher.blocks.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 8 }}>
          {teacher.blocks.map((b) => (
            <span key={b} className="summary-count" style={{ marginLeft: 0, fontSize: 11 }}>{b}</span>
          ))}
        </div>
      )}

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
  const pointColor =
    teacher.teacherPoint >= 8 ? '#16a34a' :
    teacher.teacherPoint >= 5 ? '#d97706' : '#dc2626'

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: pointColor, color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 700, fontSize: 20, flexShrink: 0
            }}>
              {teacher.teacherPoint}
            </div>
            <div>
              <h2 className="modal-title" style={{ marginBottom: 4 }}>{teacher.fullName}</h2>
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>@{teacher.username} · {teacher.code}</p>
            </div>
          </div>

          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Email</span>
              <span className="detail-value">{teacher.email || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Email cá nhân</span>
              <span className="detail-value">{teacher.personalEmail || '—'}</span>
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
            <div className="detail-item">
              <span className="detail-label">Điểm giáo viên</span>
              <span className="detail-value" style={{ color: pointColor, fontWeight: 700 }}>
                {teacher.teacherPoint} điểm
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Trạng thái</span>
              <span className="detail-value">
                <span className={`status-badge ${teacher.isActive ? 'status-running' : 'status-abandoned'}`}>
                  {teacher.isActive ? 'Đang hoạt động' : 'Ngừng hoạt động'}
                </span>
              </span>
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

          {teacher.courseLines.length > 0 && (
            <div className="detail-section">
              <h3>Khóa học phụ trách</h3>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {teacher.courseLines.map((cl, i) => (
                  <span key={i} className="summary-count" style={{ marginLeft: 0 }}>{cl}</span>
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
  pointFilter: string
}

export default function MentorsPage() {
  const { teachers, loading, error } = useTeachers()
  const [filters, setFilters] = useState<TeacherFilters>({ search: '', centres: [], blocks: [], pointFilter: '' })
  const [selectedTeacher, setSelectedTeacher] = useState<TeacherItem | null>(null)

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
      if (filters.pointFilter === 'high' && t.teacherPoint < 8) return false
      if (filters.pointFilter === 'low' && t.teacherPoint >= 8) return false
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
      <div className="page-header">
        <h1>Quản lý giáo viên</h1>
        <span className="count-badge">{filtered.length} / {teachers.length} giáo viên</span>
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
          <label className="filter-label">Điểm giáo viên</label>
          <select value={filters.pointFilter} onChange={(e) => update('pointFilter', e.target.value)}>
            <option value="">Tất cả</option>
            <option value="high">Từ 8 điểm trở lên</option>
            <option value="low">Dưới 8 điểm</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={() => setFilters({ search: '', centres: [], blocks: [], pointFilter: '' })}>
            Xóa bộ lọc
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
    </div>
  )
}

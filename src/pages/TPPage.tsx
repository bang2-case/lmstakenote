import { useState, useMemo } from 'react'
import { useTP } from '../hooks/useTP'
import type { TPRecord, TPStudentDetail } from '../types'

interface TPFilters {
  search: string
  centre: string
  mentor: string
  tpRound: '' | 'tp1' | 'tp2'
  scoreRange: '' | 'below4' | 'from4'
}

// ── Score bar ──────────────────────────────────────────────────────────────
function TPBar({ score }: { score: number | null }) {
  if (score === null) return <span className="tp-no-data">—</span>
  const pct = (score / 5) * 100
  const color = score >= 4 ? '#16a34a' : score >= 3 ? '#d97706' : '#dc2626'
  return (
    <div className="cr-bar-wrap">
      <div className="cr-bar-track">
        <div className="cr-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="cr-bar-label" style={{ color }}>{score.toFixed(2)}</span>
    </div>
  )
}

// ── Centre bar chart ───────────────────────────────────────────────────────
function CentreChart({ records }: { records: TPRecord[] }) {
  // Group by centre, calc avg TP1 and TP2
  const centreMap: Record<string, { tp1s: number[]; tp2s: number[] }> = {}
  for (const r of records) {
    const key = r.centre || 'Không rõ'
    if (!centreMap[key]) centreMap[key] = { tp1s: [], tp2s: [] }
    if (r.tp1 !== null) centreMap[key].tp1s.push(r.tp1)
    if (r.tp2 !== null) centreMap[key].tp2s.push(r.tp2)
  }

  const centres = Object.entries(centreMap).map(([name, v]) => ({
    name,
    tp1: v.tp1s.length ? +(v.tp1s.reduce((a, b) => a + b, 0) / v.tp1s.length).toFixed(2) : null,
    tp2: v.tp2s.length ? +(v.tp2s.reduce((a, b) => a + b, 0) / v.tp2s.length).toFixed(2) : null,
  })).sort((a, b) => a.name.localeCompare(b.name))

  if (centres.length === 0) return null

  return (
    <div className="tp-chart-wrapper">
      <h2 className="tp-chart-title">Điểm TP trung bình theo cơ sở</h2>
      <div className="tp-chart">
        {centres.map((c) => (
          <div key={c.name} className="tp-chart-row">
            <div className="tp-chart-label">{c.name}</div>
            <div className="tp-chart-bars">
              {/* TP1 */}
              <div className="tp-chart-bar-group">
                <span className="tp-chart-round-label tp1-label">TP1</span>
                <div className="tp-chart-bar-track">
                  {c.tp1 !== null ? (
                    <div
                      className="tp-chart-bar-fill tp1-fill"
                      style={{ width: `${(c.tp1 / 5) * 100}%` }}
                    />
                  ) : null}
                </div>
                <span className="tp-chart-score" style={{ color: c.tp1 !== null && c.tp1 >= 4 ? '#16a34a' : '#d97706' }}>
                  {c.tp1 !== null ? c.tp1.toFixed(2) : '—'}
                </span>
              </div>
              {/* TP2 */}
              <div className="tp-chart-bar-group">
                <span className="tp-chart-round-label tp2-label">TP2</span>
                <div className="tp-chart-bar-track">
                  {c.tp2 !== null ? (
                    <div
                      className="tp-chart-bar-fill tp2-fill"
                      style={{ width: `${(c.tp2 / 5) * 100}%` }}
                    />
                  ) : null}
                </div>
                <span className="tp-chart-score" style={{ color: c.tp2 !== null && c.tp2 >= 4 ? '#16a34a' : '#d97706' }}>
                  {c.tp2 !== null ? c.tp2.toFixed(2) : '—'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
      {/* Legend */}
      <div className="tp-chart-legend">
        <span className="tp-legend-dot tp1-dot" /> TP1
        <span className="tp-legend-dot tp2-dot" style={{ marginLeft: 16 }} /> TP2
      </div>
    </div>
  )
}

// ── Student detail modal ───────────────────────────────────────────────────
function TPModal({ record, onClose }: { record: TPRecord; onClose: () => void }) {
  const [activeRound, setActiveRound] = useState<'tp1' | 'tp2'>('tp1')
  const students: TPStudentDetail[] = activeRound === 'tp1' ? record.tp1_students : record.tp2_students
  const roundScore = activeRound === 'tp1' ? record.tp1 : record.tp2

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>
        <div className="modal-header">
          <h2 className="modal-title">{record.className}</h2>
          <div className="cr-modal-stats">
            <span className="cr-modal-stat">Cơ sở: <strong>{record.centre || '—'}</strong></span>
            <span className="cr-modal-stat">GV: <strong>{record.teachers[0]?.name || '—'}</strong></span>
            <span className="cr-modal-stat">
              TP1: <strong style={{ color: record.tp1 !== null && record.tp1 >= 4 ? '#16a34a' : '#d97706' }}>
                {record.tp1 !== null ? record.tp1.toFixed(2) : '—'}
              </strong>
            </span>
            <span className="cr-modal-stat">
              TP2: <strong style={{ color: record.tp2 !== null && record.tp2 >= 4 ? '#16a34a' : '#d97706' }}>
                {record.tp2 !== null ? record.tp2.toFixed(2) : '—'}
              </strong>
            </span>
          </div>
          {/* Round tabs */}
          <div className="tp-modal-tabs">
            <button
              className={`tp-modal-tab ${activeRound === 'tp1' ? 'active' : ''}`}
              onClick={() => setActiveRound('tp1')}
            >
              TP 1 {record.tp1 !== null ? `(${record.tp1.toFixed(2)})` : '(—)'}
            </button>
            <button
              className={`tp-modal-tab ${activeRound === 'tp2' ? 'active' : ''}`}
              onClick={() => setActiveRound('tp2')}
            >
              TP 2 {record.tp2 !== null ? `(${record.tp2.toFixed(2)})` : '(—)'}
            </button>
          </div>
        </div>
        <div className="modal-body">
          {students.length === 0 ? (
            <div className="cr-modal-empty">Không có dữ liệu khảo sát cho đợt này.</div>
          ) : (
            <>
              <h3 className="schedule-title-fixed">
                {activeRound === 'tp1' ? 'TP 1' : 'TP 2'} — {students.length} học viên
                {roundScore !== null && (
                  <span className="summary-count" style={{ marginLeft: 8 }}>
                    TB: {roundScore.toFixed(2)}/5
                  </span>
                )}
              </h3>
              <div className="slot-list-container">
                {students.map((s, i) => (
                  <div key={i} className="tp-student-row">
                    <span className="cr-student-index">{i + 1}</span>
                    <span className="cr-student-name">{s.name}</span>
                    <div className="tp-student-score-wrap">
                      {s.score !== null ? (
                        <>
                          <div className="tp-mini-bar-track">
                            <div
                              className="tp-mini-bar-fill"
                              style={{
                                width: `${(s.score / 5) * 100}%`,
                                background: s.score >= 4 ? '#16a34a' : s.score >= 3 ? '#d97706' : '#dc2626'
                              }}
                            />
                          </div>
                          <span
                            className="tp-student-score"
                            style={{ color: s.score >= 4 ? '#16a34a' : s.score >= 3 ? '#d97706' : '#dc2626' }}
                          >
                            {s.score.toFixed(2)}/5
                          </span>
                        </>
                      ) : (
                        <span className="tp-no-data">—</span>
                      )}
                    </div>
                    {s.textAnswers.length > 0 && (
                      <div className="tp-text-answers">
                        {s.textAnswers.map((ta, j) => (
                          <div key={j} className="tp-text-answer">💬 {ta.value}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────
export default function TPPage() {
  const { tpData, loading, error } = useTP()
  const [filters, setFilters] = useState<TPFilters>({
    search: '', centre: '', mentor: '', tpRound: '', scoreRange: ''
  })
  const [selectedRecord, setSelectedRecord] = useState<TPRecord | null>(null)

  const update = (key: keyof TPFilters, value: string) =>
    setFilters((f) => ({ ...f, [key]: value }))

  const resetFilters = () =>
    setFilters({ search: '', centre: '', mentor: '', tpRound: '', scoreRange: '' })

  // Filter options
  const { centres, mentors } = useMemo(() => {
    const cs = new Set<string>()
    const ms = new Set<string>()
    tpData.forEach((r) => {
      if (r.centre) cs.add(r.centre)
      r.teachers.forEach((t) => ms.add(t.name))
    })
    return {
      centres: Array.from(cs).sort(),
      mentors: Array.from(ms).sort(),
    }
  }, [tpData])

  // Apply filters
  const filtered = useMemo(() => {
    return tpData.filter((r) => {
      if (filters.search && !r.className.toLowerCase().includes(filters.search.toLowerCase())) return false
      if (filters.centre && r.centre !== filters.centre) return false
      if (filters.mentor && !r.teachers.some((t) => t.name === filters.mentor)) return false

      // Filter by TP round availability
      if (filters.tpRound === 'tp1' && r.tp1 === null) return false
      if (filters.tpRound === 'tp2' && r.tp2 === null) return false

      // Filter by score range
      if (filters.scoreRange) {
        // Determine which score(s) to check
        const scores: (number | null)[] = filters.tpRound === 'tp1' ? [r.tp1]
          : filters.tpRound === 'tp2' ? [r.tp2]
          : [r.tp1, r.tp2]
        const validScores = scores.filter((s): s is number => s !== null)
        if (validScores.length === 0) return false
        const avg = validScores.reduce((a, b) => a + b, 0) / validScores.length
        if (filters.scoreRange === 'below4' && avg >= 4) return false
        if (filters.scoreRange === 'from4' && avg < 4) return false
      }

      return true
    })
  }, [tpData, filters])

  if (loading) return <div className="state-msg">Đang tải dữ liệu...</div>
  if (error) return (
    <div className="state-msg error">
      Không tải được dữ liệu TP.<br />
      Hãy chạy <code>python main.py</code> để lấy data trước.
    </div>
  )
  if (tpData.length === 0) return (
    <div className="state-msg">
      Chưa có dữ liệu TP. Hãy chạy <code>python main.py</code> để lấy data.
    </div>
  )

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <h1>Quản lý TP</h1>
        <span className="count-badge">{filtered.length} / {tpData.length} lớp</span>
      </div>

      {/* Biểu đồ cột ngang */}
      <CentreChart records={filtered} />

      {/* Bộ lọc */}
      <div className="filters-container">
        <div className="filter-group">
          <label className="filter-label">Tìm lớp</label>
          <input
            type="text"
            placeholder="Nhập tên lớp..."
            value={filters.search}
            onChange={(e) => update('search', e.target.value)}
          />
        </div>

        <div className="filter-group">
          <label className="filter-label">Cơ sở</label>
          <select value={filters.centre} onChange={(e) => update('centre', e.target.value)}>
            <option value="">Tất cả</option>
            {centres.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">Giáo viên</label>
          <select value={filters.mentor} onChange={(e) => update('mentor', e.target.value)}>
            <option value="">Tất cả</option>
            {mentors.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">Đợt TP</label>
          <select value={filters.tpRound} onChange={(e) => update('tpRound', e.target.value)}>
            <option value="">Tất cả</option>
            <option value="tp1">TP 1</option>
            <option value="tp2">TP 2</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">Điểm</label>
          <select value={filters.scoreRange} onChange={(e) => update('scoreRange', e.target.value)}>
            <option value="">Tất cả</option>
            <option value="below4">Dưới 4 điểm</option>
            <option value="from4">Từ 4 trở lên</option>
          </select>
        </div>

        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={resetFilters}>Xóa bộ lọc</button>
        </div>
      </div>

      {/* Bảng lớp */}
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
                <th>Giáo viên</th>
                <th>TP 1</th>
                <th>TP 2</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={r.classId} onClick={() => setSelectedRecord(r)} style={{ cursor: 'pointer' }}>
                  <td className="cr-td-num">{i + 1}</td>
                  <td className="cr-td-name">{r.className}</td>
                  <td>{r.centre || '—'}</td>
                  <td>{r.block || '—'}</td>
                  <td>{r.teachers[0]?.name || '—'}</td>
                  <td className="cr-td-bar"><TPBar score={r.tp1} /></td>
                  <td className="cr-td-bar"><TPBar score={r.tp2} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal chi tiết */}
      {selectedRecord && (
        <TPModal record={selectedRecord} onClose={() => setSelectedRecord(null)} />
      )}
    </div>
  )
}

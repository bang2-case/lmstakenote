import { useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { useTP } from '../hooks/useTP'
import SingleSelect from '../components/SingleSelect'
import type { TPRecord, TPStudentDetail } from '../types'

interface TPFilters {
  search: string
  centre: string
  mentor: string
  tpRound: '' | 'tp1' | 'tp2'
  scoreRange: '' | 'below4' | 'from4' | 'hasScore'
}

// Format điểm: 5.00 → "5", 4.30 → "4.3", 3.75 → "3.75"
function fmtScore(score: number): string {
  if (Number.isInteger(score)) return String(score)
  const s = score.toFixed(2)
  return s.endsWith('0') ? score.toFixed(1) : s
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
      <span className="cr-bar-label" style={{ color }}>{fmtScore(score)}</span>
    </div>
  )
}

// ── Centre bar chart (Recharts) ────────────────────────────────────────────
function CentreChart({ records }: { records: TPRecord[] }) {
  const data = useMemo(() => {
    const map: Record<string, { tp1s: number[]; tp2s: number[] }> = {}
    for (const r of records) {
      const key = (r.centre || 'Không rõ').replace('HCM - ', '')
      if (!map[key]) map[key] = { tp1s: [], tp2s: [] }
      if (r.tp1 !== null) map[key].tp1s.push(r.tp1)
      if (r.tp2 !== null) map[key].tp2s.push(r.tp2)
    }
    return Object.entries(map)
      .map(([name, v]) => ({
        name,
        'TP 1': v.tp1s.length ? +(v.tp1s.reduce((a, b) => a + b, 0) / v.tp1s.length).toFixed(2) : null,
        'TP 2': v.tp2s.length ? +(v.tp2s.reduce((a, b) => a + b, 0) / v.tp2s.length).toFixed(2) : null,
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [records])

  if (data.length === 0) return null

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="tp-chart-tooltip">
        <p className="tp-chart-tooltip-label">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.fill, margin: '2px 0', fontSize: 13 }}>
            {p.name}: <strong>{p.value ?? '—'}/5</strong>
          </p>
        ))}
      </div>
    )
  }

  return (
    <div className="tp-chart-wrapper">
      <h2 className="tp-chart-title">Điểm TP trung bình theo cơ sở</h2>
      <ResponsiveContainer width="100%" height={data.length * 72 + 40}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 48, left: 8, bottom: 4 }}
          barCategoryGap="30%"
          barGap={4}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis
            type="number" domain={[0, 5]} tickCount={6}
            tick={{ fontSize: 12, fill: '#9ca3af' }}
            axisLine={false} tickLine={false}
          />
          <YAxis
            type="category" dataKey="name" width={130}
            tick={{ fontSize: 12, fill: '#374151' }}
            axisLine={false} tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(0,0,0,0.04)' }} />
          <Legend
            iconType="circle" iconSize={8}
            wrapperStyle={{ fontSize: 13, paddingTop: 8 }}
          />
          <ReferenceLine x={4} stroke="#dc2626" strokeDasharray="4 3" strokeWidth={1.5}
            label={{ value: '4.0', position: 'top', fontSize: 11, fill: '#dc2626' }} />
          <Bar dataKey="TP 1" fill="#3b82f6" radius={[0, 4, 4, 0]} maxBarSize={18} />
          <Bar dataKey="TP 2" fill="#ec4899" radius={[0, 4, 4, 0]} maxBarSize={18} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Student detail modal ───────────────────────────────────────────────────
function ScorePill({ score }: { score: number | null }) {
  if (score === null) return <span className="tp-pill tp-pill-na">—</span>
  const cls = score >= 4 ? 'tp-pill-green' : score >= 3 ? 'tp-pill-yellow' : 'tp-pill-red'
  return <span className={`tp-pill ${cls}`}>{fmtScore(score)}<span className="tp-pill-denom">/5</span></span>
}

function TPModal({ record, onClose }: { record: TPRecord; onClose: () => void }) {
  const [activeRound, setActiveRound] = useState<'tp1' | 'tp2'>('tp1')
  const students: TPStudentDetail[] = activeRound === 'tp1' ? record.tp1_students : record.tp2_students
  const roundScore = activeRound === 'tp1' ? record.tp1 : record.tp2

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="tp-modal-wrap" onClick={(e) => e.stopPropagation()}>

        {/* ── Header band ── */}
        <div className="tp-modal-banner">
          <div className="tp-modal-banner-text">
            <p className="tp-modal-banner-sub">{record.centre || '—'} · {record.teachers[0]?.name || '—'}</p>
            <h2 className="tp-modal-banner-title">{record.className}</h2>
          </div>

          {/* Score cards — clickable to switch round */}
          <div className="tp-modal-cards">
            <button
              className={`tp-modal-card ${activeRound === 'tp1' ? 'tp-modal-card-active' : ''}`}
              onClick={() => setActiveRound('tp1')}
            >
              <span className="tp-modal-card-label">TP 1</span>
              <ScorePill score={record.tp1} />
              <span className="tp-modal-card-count">
                {record.tp1_students.length > 0 ? `${record.tp1_students.length} HV` : 'Chưa có'}
              </span>
            </button>
            <button
              className={`tp-modal-card ${activeRound === 'tp2' ? 'tp-modal-card-active' : ''}`}
              onClick={() => setActiveRound('tp2')}
            >
              <span className="tp-modal-card-label">TP 2</span>
              <ScorePill score={record.tp2} />
              <span className="tp-modal-card-count">
                {record.tp2_students.length > 0 ? `${record.tp2_students.length} HV` : 'Chưa có'}
              </span>
            </button>
          </div>
        </div>

        {/* ── Student list ── */}
        <div className="tp-modal-list-wrap">
          {record.tp1 === null && record.tp2 === null ? (
            <div className="tp-no-survey">Không có khảo sát</div>
          ) : (
            <>
              <div className="tp-modal-list-head">
                <span className="tp-modal-list-title">
                  {activeRound === 'tp1' ? 'TP 1' : 'TP 2'} · {students.length} học viên
                </span>
                {roundScore !== null && (
                  <span className="tp-modal-list-avg">
                    Trung bình <strong>{fmtScore(roundScore)}/5</strong>
                  </span>
                )}
              </div>

              {students.length === 0 ? (
                <div className="cr-modal-empty">Không có dữ liệu khảo sát cho đợt này.</div>
              ) : (
                <div className="tp-slist">
                  {students.map((s, i) => (
                    <div key={i} className="tp-slist-row">
                      <span className="tp-slist-idx">{i + 1}</span>
                      <span className="tp-slist-name">{s.name}</span>
                      <div className="tp-slist-right">
                        {s.score !== null ? (
                          <>
                            <div className="tp-mini-bar-track">
                              <div className="tp-mini-bar-fill" style={{
                                width: `${(s.score / 5) * 100}%`,
                                background: s.score >= 4 ? '#16a34a' : s.score >= 3 ? '#d97706' : '#dc2626'
                              }} />
                            </div>
                            <ScorePill score={s.score} />
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
              )}
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

  const { centres, mentors } = useMemo(() => {
    const cs = new Set<string>()
    const ms = new Set<string>()
    tpData.forEach((r) => {
      if (r.centre) cs.add(r.centre)
      r.teachers.forEach((t) => ms.add(t.name))
    })
    return { centres: Array.from(cs).sort(), mentors: Array.from(ms).sort() }
  }, [tpData])

  const filtered = useMemo(() => {
    return tpData.filter((r) => {
      if (filters.search && !r.className.toLowerCase().includes(filters.search.toLowerCase())) return false
      if (filters.centre && r.centre !== filters.centre) return false
      if (filters.mentor && !r.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.tpRound === 'tp1' && r.tp1 === null) return false
      if (filters.tpRound === 'tp2' && r.tp2 === null) return false

      if (filters.scoreRange) {
        // "hasScore" — loại trừ lớp không có cả TP1 lẫn TP2
        if (filters.scoreRange === 'hasScore') {
          if (r.tp1 === null && r.tp2 === null) return false
          return true
        }
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
      {/* ── Page header with dark banner ── */}
      <div className="tp-page-banner">
        <div>
          <h1 className="tp-page-banner-title">Quản lý TP</h1>
          <p className="tp-page-banner-sub">Teacher Point — Khối Coding · Lớp chính quy</p>
        </div>
        <span className="tp-page-badge">{filtered.length} / {tpData.length} lớp</span>
      </div>

      {/* ── Chart ── */}
      <CentreChart records={filtered} />

      {/* ── Filters ── */}
      <div className="filters-container">
        <div className="filter-group">
          <label className="filter-label">Tìm lớp</label>
          <input type="text" placeholder="Nhập tên lớp..." value={filters.search}
            onChange={(e) => update('search', e.target.value)} />
        </div>
        <SingleSelect
          label="Cơ sở"
          options={centres.map((c) => ({ value: c, label: c }))}
          value={filters.centre}
          onChange={(v) => update('centre', v)}
        />
        <SingleSelect
          label="Giáo viên"
          options={mentors.map((m) => ({ value: m, label: m }))}
          value={filters.mentor}
          onChange={(v) => update('mentor', v)}
        />
        <SingleSelect
          label="Đợt TP"
          options={[
            { value: 'tp1', label: 'TP 1' },
            { value: 'tp2', label: 'TP 2' },
          ]}
          value={filters.tpRound}
          onChange={(v) => update('tpRound', v)}
        />
        <SingleSelect
          label="Điểm"
          options={[
            { value: 'hasScore', label: 'Trừ lớp không có điểm' },
            { value: 'below4', label: 'Dưới 4 điểm' },
            { value: 'from4', label: 'Từ 4 trở lên' },
          ]}
          value={filters.scoreRange}
          onChange={(v) => update('scoreRange', v)}
        />
        <div className="filter-group">
          <label className="filter-label">&nbsp;</label>
          <button className="btn-reset" onClick={resetFilters}>Xóa bộ lọc</button>
        </div>
      </div>

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

      {selectedRecord && (
        <TPModal record={selectedRecord} onClose={() => setSelectedRecord(null)} />
      )}
    </div>
  )
}

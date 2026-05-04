import { useState, useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts'
import { useCP } from '../hooks/useCP'
import SingleSelect from '../components/SingleSelect'
import type { CPRecord, CPStudentDetail } from '../types'

interface CPFilters {
  search: string
  centre: string
  mentor: string
  cpRound: '' | 'cp1' | 'cp2'
  scoreRange: '' | 'below4' | 'from4' | 'hasScore'
}

// Format điểm: 5.00 → "5", 4.30 → "4.3", 3.75 → "3.75"
function fmtScore(score: number): string {
  if (Number.isInteger(score)) return String(score)
  const s = score.toFixed(2)
  return s.endsWith('0') ? score.toFixed(1) : s
}

// ── Score bar ──────────────────────────────────────────────────────────────
function CPBar({ score }: { score: number | null }) {
  if (score === null) return <span className="cp-no-data">—</span>
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
function CentreChart({ records }: { records: CPRecord[] }) {
  const data = useMemo(() => {
    const map: Record<string, { 
      cp1Theory: number[]
      cp1Practical: number[]
      cp2Theory: number[]
      cp2Practical: number[]
    }> = {}
    for (const r of records) {
      const key = (r.centre || 'Không rõ').replace('HCM - ', '')
      if (!map[key]) map[key] = { cp1Theory: [], cp1Practical: [], cp2Theory: [], cp2Practical: [] }
      if (r.cp1Theory !== null) map[key].cp1Theory.push(r.cp1Theory)
      if (r.cp1Practical !== null) map[key].cp1Practical.push(r.cp1Practical)
      if (r.cp2Theory !== null) map[key].cp2Theory.push(r.cp2Theory)
      if (r.cp2Practical !== null) map[key].cp2Practical.push(r.cp2Practical)
    }
    return Object.entries(map)
      .map(([name, v]) => ({
        name,
        'CP1 LT': v.cp1Theory.length ? +(v.cp1Theory.reduce((a, b) => a + b, 0) / v.cp1Theory.length).toFixed(2) : null,
        'CP1 TH': v.cp1Practical.length ? +(v.cp1Practical.reduce((a, b) => a + b, 0) / v.cp1Practical.length).toFixed(2) : null,
        'CP2 LT': v.cp2Theory.length ? +(v.cp2Theory.reduce((a, b) => a + b, 0) / v.cp2Theory.length).toFixed(2) : null,
        'CP2 TH': v.cp2Practical.length ? +(v.cp2Practical.reduce((a, b) => a + b, 0) / v.cp2Practical.length).toFixed(2) : null,
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [records])

  if (data.length === 0) return null

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="cp-chart-tooltip">
        <p className="cp-chart-tooltip-label">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.fill, margin: '2px 0', fontSize: 13 }}>
            {p.name}: <strong>{p.value ?? '—'}/10</strong>
          </p>
        ))}
      </div>
    )
  }

  return (
    <div className="cp-chart-wrapper">
      <h2 className="cp-chart-title">Điểm Checkpoint trung bình theo cơ sở</h2>
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
          <Bar dataKey="CP1 LT" fill="#3b82f6" radius={[0, 4, 4, 0]} maxBarSize={16} />
          <Bar dataKey="CP1 TH" fill="#06b6d4" radius={[0, 4, 4, 0]} maxBarSize={16} />
          <Bar dataKey="CP2 LT" fill="#ec4899" radius={[0, 4, 4, 0]} maxBarSize={16} />
          <Bar dataKey="CP2 TH" fill="#f59e0b" radius={[0, 4, 4, 0]} maxBarSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Student detail modal ───────────────────────────────────────────────────
function ScorePill({ theory, practical }: { theory: number | null; practical: number | null }) {
  if (theory === null && practical === null) {
    return <span className="cp-pill cp-pill-na">—</span>
  }
  
  const scores = [theory, practical].filter((s): s is number => s !== null)
  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null
  
  if (avg === null) return <span className="cp-pill cp-pill-na">—</span>
  
  const cls = avg >= 4 ? 'cp-pill-green' : avg >= 3 ? 'cp-pill-yellow' : 'cp-pill-red'
  return (
    <span className={`cp-pill ${cls}`}>
      {theory !== null && <span>LT: {fmtScore(theory)}</span>}
      {theory !== null && practical !== null && <span className="cp-pill-sep">·</span>}
      {practical !== null && <span>TH: {fmtScore(practical)}</span>}
      <span className="cp-pill-denom">/5</span>
    </span>
  )
}

function CPModal({ record, onClose }: { record: CPRecord; onClose: () => void }) {
  const [activeRound, setActiveRound] = useState<'cp1' | 'cp2'>('cp1')
  
  const students: CPStudentDetail[] = activeRound === 'cp1' ? record.cp1_students : record.cp2_students
  const theoryScore = activeRound === 'cp1' ? record.cp1Theory : record.cp2Theory
  const practicalScore = activeRound === 'cp1' ? record.cp1Practical : record.cp2Practical

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="cp-modal-wrap" onClick={(e) => e.stopPropagation()}>

        {/* ── Header band ── */}
        <div className="cp-modal-banner">
          <div className="cp-modal-banner-text">
            <p className="cp-modal-banner-sub">{record.centre || '—'} · {record.teachers[0]?.name || '—'}</p>
            <h2 className="cp-modal-banner-title">{record.className}</h2>
          </div>

          {/* Score cards — clickable to switch round */}
          <div className="cp-modal-cards">
            <button
              className={`cp-modal-card ${activeRound === 'cp1' ? 'cp-modal-card-active' : ''}`}
              onClick={() => setActiveRound('cp1')}
            >
              <span className="cp-modal-card-label">Checkpoint 1</span>
              <ScorePill theory={record.cp1Theory} practical={record.cp1Practical} />
              <span className="cp-modal-card-count">
                {record.cp1_students.length > 0 ? `${record.cp1_students.length} HV` : 'Chưa có'}
              </span>
            </button>
            <button
              className={`cp-modal-card ${activeRound === 'cp2' ? 'cp-modal-card-active' : ''}`}
              onClick={() => setActiveRound('cp2')}
            >
              <span className="cp-modal-card-label">Checkpoint 2</span>
              <ScorePill theory={record.cp2Theory} practical={record.cp2Practical} />
              <span className="cp-modal-card-count">
                {record.cp2_students.length > 0 ? `${record.cp2_students.length} HV` : 'Chưa có'}
              </span>
            </button>
          </div>
        </div>

        {/* ── Student list ── */}
        <div className="cp-modal-list-wrap">
          {theoryScore === null && practicalScore === null ? (
            <div className="cp-no-survey">Không có dữ liệu</div>
          ) : (
            <>
              <div className="cp-modal-list-head">
                <span className="cp-modal-list-title">
                  {activeRound === 'cp1' ? 'Checkpoint 1' : 'Checkpoint 2'} · {students.length} học viên
                </span>
                <div className="cp-modal-list-avg">
                  {theoryScore !== null && (
                    <span>Lý thuyết <strong>{fmtScore(theoryScore)}/5</strong></span>
                  )}
                  {theoryScore !== null && practicalScore !== null && <span className="cp-avg-sep">·</span>}
                  {practicalScore !== null && (
                    <span>Thực hành <strong>{fmtScore(practicalScore)}/5</strong></span>
                  )}
                </div>
              </div>

              {students.length === 0 ? (
                <div className="cr-modal-empty">Không có dữ liệu cho checkpoint này.</div>
              ) : (
                <div className="cp-slist">
                  {students.map((s, i) => (
                    <div key={i} className="cp-slist-row">
                      <span className="cp-slist-idx">{i + 1}</span>
                      <span className="cp-slist-name">{s.name}</span>
                      <div className="cp-slist-scores">
                        {s.theoryScore !== null && (
                          <div className="cp-score-item">
                            <span className="cp-score-label">LT:</span>
                            <span className="cp-score-value">{fmtScore(s.theoryScore)}</span>
                          </div>
                        )}
                        {s.practicalScore !== null && (
                          <div className="cp-score-item">
                            <span className="cp-score-label">TH:</span>
                            <span className="cp-score-value">{fmtScore(s.practicalScore)}</span>
                          </div>
                        )}
                      </div>
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
export default function CPPage() {
  const { cpData, loading, error } = useCP()
  const [filters, setFilters] = useState<CPFilters>({
    search: '', centre: '', mentor: '', cpRound: '', scoreRange: ''
  })
  const [selectedRecord, setSelectedRecord] = useState<CPRecord | null>(null)

  const update = (key: keyof CPFilters, value: string) =>
    setFilters((f) => ({ ...f, [key]: value }))

  const resetFilters = () =>
    setFilters({ search: '', centre: '', mentor: '', cpRound: '', scoreRange: '' })

  const { centres, mentors } = useMemo(() => {
    const cs = new Set<string>()
    const ms = new Set<string>()
    cpData.forEach((r) => {
      if (r.centre) cs.add(r.centre)
      r.teachers.forEach((t) => ms.add(t.name))
    })
    return { centres: Array.from(cs).sort(), mentors: Array.from(ms).sort() }
  }, [cpData])

  const filtered = useMemo(() => {
    return cpData.filter((r) => {
      if (filters.search && !r.className.toLowerCase().includes(filters.search.toLowerCase())) return false
      if (filters.centre && r.centre !== filters.centre) return false
      if (filters.mentor && !r.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.cpRound === 'cp1' && r.cp1Theory === null && r.cp1Practical === null) return false
      if (filters.cpRound === 'cp2' && r.cp2Theory === null && r.cp2Practical === null) return false

      if (filters.scoreRange) {
        // "hasScore" — loại trừ lớp không có dữ liệu
        if (filters.scoreRange === 'hasScore') {
          if (r.cp1Theory === null && r.cp1Practical === null && r.cp2Theory === null && r.cp2Practical === null) return false
          return true
        }
        const scores: (number | null)[] = filters.cpRound === 'cp1' ? [r.cp1Theory, r.cp1Practical]
          : filters.cpRound === 'cp2' ? [r.cp2Theory, r.cp2Practical]
          : [r.cp1Theory, r.cp1Practical, r.cp2Theory, r.cp2Practical]
        const validScores = scores.filter((s): s is number => s !== null)
        if (validScores.length === 0) return false
        const avg = validScores.reduce((a, b) => a + b, 0) / validScores.length
        if (filters.scoreRange === 'below4' && avg >= 4) return false
        if (filters.scoreRange === 'from4' && avg < 4) return false
      }

      return true
    })
  }, [cpData, filters])

  if (loading) return <div className="state-msg">Đang tải dữ liệu...</div>
  if (error) return (
    <div className="state-msg error">
      Không tải được dữ liệu Checkpoint.<br />
      Hãy chạy <code>python main.py</code> để lấy data trước.
    </div>
  )
  if (cpData.length === 0) return (
    <div className="state-msg">
      Chưa có dữ liệu Checkpoint. Hãy chạy <code>python main.py</code> để lấy data.
    </div>
  )

  return (
    <div className="page">
      {/* ── Page header with dark banner ── */}
      <div className="cp-page-banner">
        <div>
          <h1 className="cp-page-banner-title">Quản lý CP</h1>
          <p className="cp-page-banner-sub">Checkpoint — Khối Coding</p>
        </div>
        <span className="cp-page-badge">{filtered.length} / {cpData.length} lớp</span>
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
          label="Checkpoint"
          options={[
            { value: 'cp1', label: 'Checkpoint 1' },
            { value: 'cp2', label: 'Checkpoint 2' },
          ]}
          value={filters.cpRound}
          onChange={(v) => update('cpRound', v)}
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
                <th>CP1 LT</th>
                <th>CP1 TH</th>
                <th>CP2 LT</th>
                <th>CP2 TH</th>
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
                  <td className="cr-td-bar"><CPBar score={r.cp1Theory} /></td>
                  <td className="cr-td-bar"><CPBar score={r.cp1Practical} /></td>
                  <td className="cr-td-bar"><CPBar score={r.cp2Theory} /></td>
                  <td className="cr-td-bar"><CPBar score={r.cp2Practical} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRecord && (
        <CPModal record={selectedRecord} onClose={() => setSelectedRecord(null)} />
      )}
    </div>
  )
}

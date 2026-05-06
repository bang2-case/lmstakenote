import { useState } from 'react'
import { useDemo } from '../hooks/useDemo'
import DatePickerInput from '../components/DatePickerInput'
import type { DemoClass } from '../hooks/useDemo'

// ── Helpers ────────────────────────────────────────────────────────────────

const BLOCK_COLOR: Record<string, string> = {
  Coding:   '#3b82f6',
  Robotics: '#ec4899',
  Art:      '#f59e0b',
}

// ── Block table ────────────────────────────────────────────────────────────

function BlockTable({ title, items, color }: { title: string; items: DemoClass[]; color: string }) {
  if (items.length === 0) return null
  return (
    <div className="demo-block-section">
      <div className="demo-block-header" style={{ borderLeftColor: color }}>
        <span className="demo-block-title" style={{ color }}>{title}</span>
        <span className="demo-block-count">{items.length} lớp</span>
      </div>
      <div className="cr-table-wrapper">
        <table className="cr-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>#</th>
              <th style={{ width: 60 }}>BA</th>
              <th>Tên lớp</th>
              <th>Cơ sở</th>
              <th>Time Demo</th>
              <th style={{ textAlign: 'center' }}>Sĩ số</th>
              <th>Ngày</th>
              <th>Thứ</th>
              <th>Giờ</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c, i) => (
              <tr key={c.id}>
                <td className="cr-td-num">{i + 1}</td>
                <td style={{ fontSize: 12, color: '#6b7280' }}>{c.area}</td>
                <td className="cr-td-name">{c.name}</td>
                <td>{c.centre}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{c.time_demo}</td>
                <td className="cr-td-center">{c.student_count}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{c.date}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{c.day_of_week}</td>
                <td style={{ whiteSpace: 'nowrap' }}>{c.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function DEMOPage() {
  const { classes, loading, exporting, error, exportResult, fetchClasses, exportSheet } = useDemo()
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const coding   = classes.filter(c => c.block === 'Coding')
  const robotics = classes.filter(c => c.block === 'Robotics')
  const art      = classes.filter(c => c.block === 'Art')

  // Dùng dateFrom (ngày bắt đầu) làm ngày lọc chính
  const activeDate = dateFrom

  const handleExport = () => {
    if (activeDate) {
      fetchClasses(activeDate, dateTo)
      exportSheet(activeDate, dateTo)
    }
  }

  return (
    <div className="page">
      {/* Banner — dùng page-banner giống các trang khác */}
      <div className="page-banner">
        <div>
          <h1 className="page-banner-title">Quản lý DEMO</h1>
          <p className="page-banner-sub">Lớp có buổi 14 · 7 cơ sở HCM</p>
        </div>
        {classes.length > 0 && (
          <div className="demo-stats-row">
            <div className="demo-stat">
              <span className="demo-stat-num" style={{ color: BLOCK_COLOR.Coding }}>{coding.length}</span>
              <span className="demo-stat-label">Coding</span>
            </div>
            <div className="demo-stat">
              <span className="demo-stat-num" style={{ color: BLOCK_COLOR.Robotics }}>{robotics.length}</span>
              <span className="demo-stat-label">Robotics</span>
            </div>
            <div className="demo-stat">
              <span className="demo-stat-num" style={{ color: BLOCK_COLOR.Art }}>{art.length}</span>
              <span className="demo-stat-label">Art</span>
            </div>
          </div>
        )}
        <span className="page-banner-badge">
          {classes.length > 0 ? `${classes.length} lớp` : '—'}
        </span>
      </div>

      {/* Controls — căn giữa */}
      <div className="demo-controls-center">
        <div className="demo-controls-inner">
          <DatePickerInput
            label="Ngày diễn ra"
            value={{ from: dateFrom, to: dateTo }}
            onChange={(from, to) => { setDateFrom(from); setDateTo(to) }}
          />
          <div className="demo-btn-group">
            <label className="filter-label">&nbsp;</label>
            <button
              className="btn-summary"
              onClick={handleExport}
              disabled={!activeDate || loading || exporting}
              style={{ minWidth: 120 }}
            >
              {loading || exporting ? '⏳ Đang xử lý...' : '📊 Export'}
            </button>
          </div>
        </div>
      </div>

      {/* Export result */}
      {exportResult && (
        <div className="demo-export-result">
          <span>✅ Đã xuất thành công tab <strong>{exportResult.tab_name}</strong></span>
          <span className="demo-export-counts">
            Coding: {exportResult.coding_count} · Robotics: {exportResult.robotics_count} · Art: {exportResult.art_count}
          </span>
          <a
            href={exportResult.url}
            target="_blank"
            rel="noopener noreferrer"
            className="demo-sheet-link"
          >
            Mở Google Sheet →
          </a>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="state-msg error" style={{ padding: '20px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Loading */}
      {(loading || exporting) && (
        <div className="state-msg">Đang xử lý dữ liệu...</div>
      )}

      {/* Empty state */}
      {!loading && !exporting && !error && classes.length === 0 && (
        <div className="state-msg" style={{ paddingTop: 40 }}>
          Chọn ngày và bấm "Export" để lọc và xuất danh sách.
        </div>
      )}

      {/* Results */}
      {!loading && !exporting && classes.length > 0 && (
        <div className="demo-results">
          <BlockTable title="CODING"   items={coding}   color={BLOCK_COLOR.Coding} />
          <BlockTable title="ROBOTICS" items={robotics} color={BLOCK_COLOR.Robotics} />
          <BlockTable title="ART"      items={art}      color={BLOCK_COLOR.Art} />
        </div>
      )}
    </div>
  )
}

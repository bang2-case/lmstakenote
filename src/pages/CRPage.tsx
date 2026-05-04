import { useState, useMemo } from 'react'
import { useClasses } from '../hooks/useClasses'
import SingleSelect from '../components/SingleSelect'
import type { ClassItem } from '../types'

const HCM4_CENTRES = ['Tên Lửa', 'Tây Thạnh', 'Lũy Bán Bích', 'Trường Chinh']

// Lớp chính quy:
// - Có 2 phần: TL-JSB01, TL-CSB01 → ✅
// - Có 3+ phần, phần giữa (index 1) là mã khối hợp lệ: TL-ROB-ARMB13, 01TC-KIND-X01 → ✅
// - Có 3+ phần, phần giữa khác: 01TC-THT-D30301 → ❌ đặc biệt
const VALID_BLOCK_CODES = new Set(['ROB', 'KIND', 'XART', 'C4K'])

function isRegularClass(name: string): boolean {
  // Bỏ phần trong ngoặc như (1:1), (ONL) trước khi xử lý
  const cleaned = name.replace(/\s*\(.*?\)/g, '').trim()
  const parts = cleaned.split('-')
  if (parts.length < 2) return false
  if (parts.length === 2) return true  // TL-JSB01 → chính quy
  // 3+ phần: kiểm tra phần giữa (index 1)
  return VALID_BLOCK_CODES.has(parts[1].toUpperCase())
}

interface CRFilters {
  centre: string
  block: string
  mentor: string
  rateFilter: string  // 'high' = >=80%, 'low' = <80%
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

export default function CRPage() {
  const { classes, loading, error } = useClasses()
  const [filters, setFilters] = useState<CRFilters>({ centre: '', block: '', mentor: '', rateFilter: '' })

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

  const resetFilters = () => setFilters({ centre: '', block: '', mentor: '', rateFilter: '' })

  // Áp dụng bộ lọc
  const filtered = useMemo(() => {
    return finishedClasses.filter((c) => {
      if (filters.centre && c.centre !== filters.centre) return false
      if (filters.block && c.block !== filters.block) return false
      if (filters.mentor && !c.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.rateFilter === 'high' && c.completionRate < 80) return false
      if (filters.rateFilter === 'low' && c.completionRate >= 80) return false
      return true
    })
  }, [finishedClasses, filters])

  // Tổng CR HCM4 — tính theo filtered (đã áp dụng bộ lọc khối/cơ sở/...)
  // Chỉ tính các cơ sở thuộc HCM4
  const hcm4Stats = useMemo(() => {
    const hcm4 = filtered.filter((c) =>
      HCM4_CENTRES.some((kw) => (c.centre || '').includes(kw))
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
          <div className="hcm4-label">Tổng CPR HCM4</div>
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
          label="Cơ sở"
          options={centres.map((c) => ({ value: c, label: c }))}
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
                <CRRow key={c.id} item={c} index={i + 1} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function CRRow({ item, index }: { item: ClassItem; index: number }) {
  return (
    <tr>
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

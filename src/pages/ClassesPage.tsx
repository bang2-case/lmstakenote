import { useState, useMemo } from 'react'
import { useClasses } from '../hooks/useClasses'
import ClassFiltersComponent from '../components/ClassFilters'
import ClassDetail from '../components/ClassDetail'
import type { ClassItem, ClassFilters } from '../types'

const STATUS_MAP: Record<string, string> = {
  PENDING: 'Pending',
  PRE_OPEN: 'Pre Open',
  OPEN: 'Open',
  RUNNING: 'Running',
  FINISHED: 'Finished',
  NEW: 'New',
  PREPARING: 'Preparing',
  ABANDONED: 'Abandoned',
  REJECT: 'Reject',
}

const STATUS_COLOR: Record<string, string> = {
  PENDING: 'status-pending',
  PRE_OPEN: 'status-pre-open',
  OPEN: 'status-open',
  RUNNING: 'status-running',
  FINISHED: 'status-finished',
  NEW: 'status-new',
  PREPARING: 'status-preparing',
  ABANDONED: 'status-abandoned',
  REJECT: 'status-abandoned',
}

function SummaryModal({ classes, onClose }: { classes: ClassItem[]; onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <h2 className="modal-title">
            Tổng hợp
            <span className="summary-count">{classes.length} lớp</span>
          </h2>
        </div>

        <div className="summary-table-wrapper">
          <table className="summary-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Tên lớp</th>
                <th>Cơ sở</th>
                <th>Khóa học</th>
                <th>Giáo viên</th>
                <th>Trạng thái</th>
                <th>Số buổi</th>
                <th>Học viên</th>
                <th>Nhận xét</th>
              </tr>
            </thead>
            <tbody>
              {classes.map((c, i) => (
                <tr key={c.id}>
                  <td>{i + 1}</td>
                  <td><span className="summary-name">{c.name}</span></td>
                  <td>{c.centre || '—'}</td>
                  <td>{c.course || '—'}</td>
                  <td>{c.teachers[0]?.name || '—'}</td>
                  <td>
                    <span className={`status-badge ${STATUS_COLOR[c.status] ?? ''}`}>
                      {STATUS_MAP[c.status] ?? c.status}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center' }}>{c.sessions ?? '—'}</td>
                  <td style={{ textAlign: 'center' }}>{c.studentCount}</td>
                  <td style={{ textAlign: 'center' }}>
                    {c.totalSlotsWithStudents > 0
                      ? `${c.commentPercentage}% (${c.slotsWithFullComments}/${c.totalSlotsWithStudents})`
                      : '—'}
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

function ClassCard({ item, onClick, hasUncommentedSlots }: { item: ClassItem; onClick: () => void; hasUncommentedSlots: boolean }) {
  const mainTeacher = item.teachers[0]?.name || '—'

  return (
    <div className={`card ${hasUncommentedSlots ? 'card-uncommented' : ''}`} onClick={onClick}>
      <div className="card-header">
        <h3 className="card-title">{item.name}</h3>
        <span className={`status-badge ${STATUS_COLOR[item.status] ?? ''}`}>
          {STATUS_MAP[item.status] ?? item.status}
        </span>
      </div>
      {item.course && <p className="card-meta">📘 {item.course}</p>}
      {item.centre && <p className="card-meta">🏢 {item.centre}</p>}
      <p className="card-meta">👨‍🏫 {mainTeacher}</p>
      {item.sessions != null && <p className="card-meta">📅 {item.sessions} buổi</p>}
      <p className="card-meta">👥 {item.studentCount} học viên</p>
      {item.totalSlotsWithStudents > 0 && (
        <p className="card-meta">💬 Nhận xét: {item.commentPercentage}% ({item.slotsWithFullComments}/{item.totalSlotsWithStudents} buổi)</p>
      )}
    </div>
  )
}

export default function ClassesPage() {
  const { classes, loading, error } = useClasses()
  const [filters, setFilters] = useState<ClassFilters>({
    centre: '',
    startDate: '',
    startDateTo: '',
    endDate: '',
    endDateTo: '',
    slot: '',
    slotTo: '',
    course: '',
    status: [],
    hasComments: '',
    mentor: '',
    block: [],
  })

  // Debug setFilters
  const handleFiltersChange = (newFilters: ClassFilters) => {
    setFilters(newFilters)
  }
  const [selectedClass, setSelectedClass] = useState<ClassItem | null>(null)
  const [showSummary, setShowSummary] = useState(false)

  // Extract unique values for filters
  const { centres, courses, statuses, mentors, blocks } = useMemo(() => {
    const centresSet = new Set<string>()
    const coursesSet = new Set<string>()
    const statusesSet = new Set<string>()
    const mentorsSet = new Set<string>()
    const blocksSet = new Set<string>()

    classes.forEach((c) => {
      if (c.centre) centresSet.add(c.centre)
      if (c.course) coursesSet.add(c.course)
      if (c.status) statusesSet.add(c.status)
      if (c.block) blocksSet.add(c.block)
      c.teachers.forEach((t) => mentorsSet.add(t.name))
    })

    return {
      centres: Array.from(centresSet).sort(),
      courses: Array.from(coursesSet).sort(),
      statuses: Array.from(statusesSet).sort(),
      mentors: Array.from(mentorsSet).sort(),
      blocks: Array.from(blocksSet).sort(),
    }
  }, [classes])

  // Apply filters
  const filteredClasses = useMemo(() => {
    return classes.filter((c) => {
      if (filters.centre && c.centre !== filters.centre) return false
      if (filters.course && c.course !== filters.course) return false
      if (filters.status.length > 0 && !filters.status.includes(c.status)) return false
      if (filters.mentor && !c.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.block.length > 0 && !filters.block.includes(c.block)) return false
      
      // Lọc ngày bắt đầu (startDate trong data)
      if (filters.startDate && c.startDate) {
        const classStartDate = new Date(c.startDate)
        const classStartDateStr = classStartDate.getFullYear() + '-' + 
                                 String(classStartDate.getMonth() + 1).padStart(2, '0') + '-' + 
                                 String(classStartDate.getDate()).padStart(2, '0')
        
        if (filters.startDateTo) {
          if (filters.startDate === filters.startDateTo) {
            // Same date selected - exact match
            if (classStartDateStr !== filters.startDate) return false
          } else {
            // Date range
            if (classStartDateStr < filters.startDate || classStartDateStr > filters.startDateTo) return false
          }
        } else {
          // Only start date selected - from this date onwards
          if (classStartDateStr < filters.startDate) return false
        }
      }
      
      // Lọc ngày kết thúc (endDate trong data)
      if (filters.endDate && c.endDate) {
        const classEndDate = new Date(c.endDate)
        const classEndDateStr = classEndDate.getFullYear() + '-' + 
                               String(classEndDate.getMonth() + 1).padStart(2, '0') + '-' + 
                               String(classEndDate.getDate()).padStart(2, '0')
        
        if (filters.endDateTo) {
          if (filters.endDate === filters.endDateTo) {
            // Same date selected - exact match
            if (classEndDateStr !== filters.endDate) return false
          } else {
            // Date range
            if (classEndDateStr < filters.endDate || classEndDateStr > filters.endDateTo) return false
          }
        } else {
          // Only end date selected - from this date onwards
          if (classEndDateStr < filters.endDate) return false
        }
      }

      // Lọc ngày diễn ra (slots) và nhận xét
      if (filters.slot || filters.slotTo || filters.hasComments) {
        let slotsInRange = c.slots
        
        // Filter slots by date range if specified
        // Only apply slot date filter if we have a complete range or single date
        if ((filters.slot && filters.slotTo) || (filters.slot && !filters.slotTo)) {
          slotsInRange = c.slots.filter((slot) => {
            // Convert slot date to local date string (YYYY-MM-DD format)
            const slotDate = new Date(slot.date)
            const slotDateStr = slotDate.getFullYear() + '-' + 
                               String(slotDate.getMonth() + 1).padStart(2, '0') + '-' + 
                               String(slotDate.getDate()).padStart(2, '0')
            
            // If both filters.slot and filters.slotTo exist
            if (filters.slot && filters.slotTo) {
              if (filters.slot === filters.slotTo) {
                // Same date selected - exact match
                return slotDateStr === filters.slot
              } else {
                // Date range - slot must be within range
                return slotDateStr >= filters.slot && slotDateStr <= filters.slotTo
              }
            } else if (filters.slot && !filters.slotTo) {
              // Only start date selected - from this date onwards
              return slotDateStr >= filters.slot
            } else if (!filters.slot && filters.slotTo) {
              // Only end date selected - up to this date (this shouldn't happen in normal flow)
              return slotDateStr <= filters.slotTo
            }
            
            // If no slot filters, include all slots
            return true
          })
          
          // If date filter is applied but no slots in range, exclude class
          if (slotsInRange.length === 0) {
            return false
          }
        }
        
        // Lọc nhận xét cho các slot (trong range nếu có)
        if (filters.hasComments) {
          const threshold = parseInt(filters.hasComments)
          
          if (threshold === 100) {
            // Đã nhận xét - tất cả slots phải đã nhận xét hoặc chưa bắt đầu
            const allCommented = slotsInRange.every(slot => 
              slot.commentStatus === 'Đã nhận xét' || slot.commentStatus === 'Chưa bắt đầu'
            )
            if (!allCommented) return false
          } else if (threshold === 0) {
            // Chưa nhận xét - có ít nhất 1 slot chưa nhận xét (không bao gồm "Chưa bắt đầu")
            const now = new Date()
            const hasUncommented = slotsInRange.some(slot => {
              const slotDate = new Date(slot.date)
              // Chỉ tính những slot đã diễn ra và chưa nhận xét
              return slotDate <= now && 
                     slot.commentStatus !== 'Đã nhận xét' && 
                     slot.commentStatus !== 'Chưa bắt đầu'
            })
            if (!hasUncommented) return false
          }
        }
      }

      return true
    })
  }, [classes, filters])

  // Check if class has uncommented slots (for card styling)
  const getHasUncommentedSlots = (classItem: ClassItem) => {
    const now = new Date()
    return classItem.slots.some(slot => {
      const slotDate = new Date(slot.date)
      return slotDate < now && slot.commentStatus !== 'Đã nhận xét'
    })
  }

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
      <div className="page-header">
        <h1>Danh sách lớp học</h1>
        <span className="count-badge">{filteredClasses.length} / {classes.length} lớp</span>
      </div>

      <ClassFiltersComponent
        filters={filters}
        onChange={handleFiltersChange}
        centres={centres}
        courses={courses}
        statuses={statuses}
        mentors={mentors}
        blocks={blocks}
        onSummary={() => setShowSummary(true)}
      />

      <div className="card-grid">
        {filteredClasses.map((c) => (
          <ClassCard 
            key={c.id} 
            item={c} 
            onClick={() => setSelectedClass(c)}
            hasUncommentedSlots={getHasUncommentedSlots(c)}
          />
        ))}
      </div>

      {selectedClass && (
        <ClassDetail classItem={selectedClass} onClose={() => setSelectedClass(null)} />
      )}

      {showSummary && (
        <SummaryModal classes={filteredClasses} onClose={() => setShowSummary(false)} />
      )}
    </div>
  )
}

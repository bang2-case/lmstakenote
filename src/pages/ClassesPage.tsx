import { useState, useMemo } from 'react'
import { useClasses } from '../hooks/useClasses'
import { useTP } from '../hooks/useTP'
import ClassFiltersComponent from '../components/ClassFilters'
import ClassDetail from '../components/ClassDetail'
import RefreshButton from '../components/RefreshButton'
import type { ClassItem, ClassFilters, Slot } from '../types'
import { centreMatchesArea } from '../utils/areas'

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

function getNextSessionLabel(slots: Slot[]) {
  const now = new Date()
  const sorted = [...slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const nextIndex = sorted.findIndex((slot) => new Date(slot.date).getTime() >= now.getTime())
  return nextIndex >= 0 ? `Buổi ${nextIndex + 1}` : '—'
}

function getUncommentedSessionLabel(slots: Slot[]) {
  const now = new Date()
  const sorted = [...slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const firstUncommented = sorted.findIndex((slot) => {
    const slotDate = new Date(slot.date)
    return slotDate < now && slot.commentStatus !== 'Đã nhận xét' && slot.commentStatus !== 'Chưa bắt đầu'
  })
  return firstUncommented >= 0 ? `Buổi ${firstUncommented + 1}` : '—'
}

async function copyText(text: string) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return
    }
  } catch (err) {
    // fallback to old-school copy
  }

  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  document.execCommand('copy')
  document.body.removeChild(textarea)
}

function SummaryModal({ classes, onClose }: { classes: ClassItem[]; onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content summary-modal" onClick={(e) => e.stopPropagation()}>

        <div className="summary-banner" style={{ paddingTop: '35px', paddingBottom: '35px' }}>
          <div>
            <h2 className="summary-banner-title">Tổng hợp</h2>
            <p className="summary-banner-sub">Danh sách lớp học</p>
          </div>
          <span className="summary-banner-badge">{classes.length} lớp</span>
        </div>

        <div className="summary-table-wrapper">
          <table className="summary-table">
            <thead>
              <tr>
                <th className="summary-fixed-col">#</th>
                <th className="summary-fixed-col">Tên lớp</th>
                <th>Giáo viên</th>
                <th>Số buổi</th>
                <th>Học viên</th>
                <th>Buổi kế tiếp</th>
                <th>Buổi chưa NX</th>
              </tr>
            </thead>
            <tbody>
              {classes.map((c, i) => (
                <tr key={c.id}>
                  <td>{i + 1}</td>
                  <td>
                    <span
                      className="summary-name summary-nowrap summary-copyable"
                      onClick={() => copyText(c.name)}
                      title="Bấm để copy tên lớp"
                    >
                      {c.name}
                    </span>
                  </td>
                  <td>{c.teachers[0]?.name || '—'}</td>
                  <td style={{ textAlign: 'center' }}>{c.sessions ?? '—'}</td>
                  <td style={{ textAlign: 'center' }}>{c.studentCount}</td>
                  <td style={{ textAlign: 'center' }}>{getNextSessionLabel(c.slots)}</td>
                  <td style={{ textAlign: 'center' }}>{getUncommentedSessionLabel(c.slots)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// Helper: tính trạng thái nhận xét của 1 lớp dựa trên endTime từng slot
// 'commented' | 'pending' (chưa quá hạn) | 'overdue' (đã quá hạn) | 'none'
function getCommentStatus(classItem: ClassItem): 'commented' | 'pending' | 'overdue' | 'none' {
  const now = new Date()
  const OVERDUE_MS = 48 * 60 * 60 * 1000 // 48h tính từ endTime buổi học

  const pastSlotsWithStudents = classItem.slots.filter(s => {
    const endTime = new Date(s.endTime || s.date)
    return endTime < now && s.studentsInSlot > 0
  })

  if (pastSlotsWithStudents.length === 0) return 'none'

  const uncommented = pastSlotsWithStudents.filter(s => s.commentStatus !== 'Đã nhận xét')

  if (uncommented.length === 0) return 'commented'

  const hasOverdue = uncommented.some(s => {
    const endTime = new Date(s.endTime || s.date)
    return now.getTime() - endTime.getTime() > OVERDUE_MS
  })

  return hasOverdue ? 'overdue' : 'pending'
}

function ClassCard({ item, onClick, commentStatus, hasPendingSurvey, pendingSurveyInfo }: {
  item: ClassItem;
  onClick: () => void;
  commentStatus: 'commented' | 'pending' | 'overdue' | 'none';
  hasPendingSurvey: boolean;
  pendingSurveyInfo?: { round: string; missing: number }[];
}) {
  const mainTeacher = item.teachers[0]?.name || '—'

  // Ưu tiên màu viền: pending survey > overdue > pending > commented
  let cardClass = ''
  if (hasPendingSurvey) {
    cardClass = 'card-pending-survey'
  } else if (commentStatus === 'overdue') {
    cardClass = 'card-overdue'
  } else if (commentStatus === 'pending') {
    cardClass = 'card-comment-pending'
  } else if (commentStatus === 'commented') {
    cardClass = 'card-commented'
  }

  // Tìm các buổi đã qua nhưng chưa nhận xét (dùng endTime)
  const now = new Date()
  const uncommentedSlots = item.slots
    .map((s, i) => ({ ...s, index: i }))
    .filter(s => {
      const endTime = new Date(s.endTime || s.date)
      return endTime < now && s.commentStatus !== 'Đã nhận xét' && s.studentsInSlot > 0
    })
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  return (
    <div className={`card ${cardClass}`} onClick={onClick}>
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

      {/* Trạng thái nhận xét */}
      {commentStatus === 'commented' && (
        <p className="card-meta" style={{ color: '#16a34a', fontWeight: 600 }}>
          ✅ Đã nhận xét đầy đủ
        </p>
      )}
      {(commentStatus === 'pending' || commentStatus === 'overdue') && uncommentedSlots.length > 0 && (
        <p className="card-meta" style={{ color: commentStatus === 'overdue' ? '#dc2626' : '#d97706', fontWeight: 600 }}>
          💬 Buổi chưa nhận xét: {uncommentedSlots.map(s => `Buổi ${s.index + 1}`).join(', ')}
        </p>
      )}

      {hasPendingSurvey && pendingSurveyInfo && pendingSurveyInfo.map(info => (
        <p key={info.round} className="card-meta" style={{ color: '#dc2626', fontWeight: 600 }}>
          📊 {info.round}: Còn thiếu {info.missing} học viên
        </p>
      ))}
    </div>
  )
}

export default function ClassesPage() {
  const { classes, loading, error } = useClasses()
  const { tpData } = useTP()
  const [filters, setFilters] = useState<ClassFilters>({
    area: '',
    centre: '',
    startDate: '',
    startDateTo: '',
    endDate: '',
    endDateTo: '',
    slot: '',
    slotTo: '',
    course: '',
    search: '',
    status: [],
    hasComments: '',
    mentor: '',
    tpRound: '',
    cpRound: '',
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
      if (filters.search && !c.name.toLowerCase().includes(filters.search.toLowerCase())) return false
      if (filters.area && !centreMatchesArea(c.centre, filters.area)) return false
      if (filters.centre && c.centre !== filters.centre) return false
      if (filters.course && c.course !== filters.course) return false
      if (filters.status.length > 0 && !filters.status.includes(c.status)) return false
      if (filters.mentor && !c.teachers.some((t) => t.name === filters.mentor)) return false
      if (filters.block.length > 0 && !filters.block.includes(c.block)) return false

      // Lọc TP Round
      if (filters.tpRound) {
        const now = new Date()
        const sortedSlots = [...c.slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
        const nextSlotIndex = sortedSlots.findIndex(s => new Date(s.date) > now)

        if (filters.tpRound === 'pending') {
          // "Chưa thao tác": lớp RUNNING, buổi TP đã qua, có học viên,
          // nhưng chưa có survey data (tp=null VÀ không có students nào có điểm)
          if (c.status !== 'RUNNING') return false

          const tpRecord = tpData.find(t => t.classId === c.id)

          const tp1Slot = sortedSlots[3]  // buổi 4 (index 3)
          const tp2Slot = sortedSlots[7]  // buổi 8 (index 7)
          const tp1Past = tp1Slot && new Date(tp1Slot.date) < now && tp1Slot.studentsInSlot > 0
          const tp2Past = tp2Slot && new Date(tp2Slot.date) < now && tp2Slot.studentsInSlot > 0

          // Nếu không có buổi TP nào đã qua → không phải pending
          if (!tp1Past && !tp2Past) return false

          // Kiểm tra TP1: buổi đã qua + có HV + chưa có survey data
          const tp1Pending = tp1Past && (() => {
            if (!tpRecord) return true  // không có record → chưa thao tác
            const hasSurveyData = tpRecord.tp1 !== null || (tpRecord.tp1_students || []).length > 0
            if (!hasSurveyData) return true  // chưa có data → chưa thao tác
            // Có data nhưng thiếu học viên (tính trên tổng HV lớp) → cũng là pending
            const studentsWithScore = (tpRecord.tp1_students || []).filter(s => s.score !== null && s.score !== undefined)
            return studentsWithScore.length < c.studentCount
          })()

          // Kiểm tra TP2: buổi đã qua + có HV + chưa có survey data
          const tp2Pending = tp2Past && (() => {
            if (!tpRecord) return true
            const hasSurveyData = tpRecord.tp2 !== null || (tpRecord.tp2_students || []).length > 0
            if (!hasSurveyData) return true
            const studentsWithScore = (tpRecord.tp2_students || []).filter(s => s.score !== null && s.score !== undefined)
            return studentsWithScore.length < c.studentCount
          })()

          if (!tp1Pending && !tp2Pending) return false
        } else {
          if (nextSlotIndex === -1) return false
          if (filters.tpRound === 'tp1') {
            if (nextSlotIndex !== 3) return false   // buổi 4 (index 3)
          } else if (filters.tpRound === 'tp2') {
            if (nextSlotIndex !== 7) return false   // buổi 8 (index 7)
          } else if (filters.tpRound === 'all') {
            if (nextSlotIndex !== 3 && nextSlotIndex !== 7) return false
          }
        }
      }

      // Lọc Checkpoint
      if (filters.cpRound) {
        const now = new Date()
        const sortedSlots = [...c.slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
        const nextSlotIndex = sortedSlots.findIndex(s => new Date(s.date) > now)
        if (nextSlotIndex === -1) return false
        // CP slot theo khối: Robotics → 4 & 8 (index 3 & 7), Coding → 5 & 9 (index 4 & 8)
        const isRobotics = c.block === 'Robotics'
        const cp1Index = isRobotics ? 3 : 4   // buổi 4 hoặc 5
        const cp2Index = isRobotics ? 7 : 8   // buổi 8 hoặc 9
        if (filters.cpRound === 'cp1') {
          if (nextSlotIndex !== cp1Index) return false
        } else if (filters.cpRound === 'cp2') {
          if (nextSlotIndex !== cp2Index) return false
        } else if (filters.cpRound === 'all') {
          if (nextSlotIndex !== cp1Index && nextSlotIndex !== cp2Index) return false
        }
      }
      
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
          const now = new Date()
          const OVERDUE_MS = 48 * 60 * 60 * 1000

          const pastSlots = slotsInRange.filter(slot => {
            const endTime = new Date(slot.endTime || slot.date)
            return endTime < now && slot.studentsInSlot > 0
          })

          if (pastSlots.length === 0) return false

          const uncommented = pastSlots.filter(s => s.commentStatus !== 'Đã nhận xét')

          if (filters.hasComments === 'commented') {
            if (uncommented.length > 0) return false
          } else if (filters.hasComments === 'pending') {
            // Chưa nhận xét + chưa quá hạn
            if (uncommented.length === 0) return false
            const hasOverdue = uncommented.some(s => {
              const endTime = new Date(s.endTime || s.date)
              return now.getTime() - endTime.getTime() > OVERDUE_MS
            })
            if (hasOverdue) return false
          } else if (filters.hasComments === 'overdue') {
            // Chưa nhận xét + đã quá hạn
            if (uncommented.length === 0) return false
            const hasOverdue = uncommented.some(s => {
              const endTime = new Date(s.endTime || s.date)
              return now.getTime() - endTime.getTime() > OVERDUE_MS
            })
            if (!hasOverdue) return false
          }
        }
      }

      return true
    })
  }, [classes, filters, tpData])

  // Check if class has pending survey (for card styling)
  // Trả về array để hiển thị cả TP1 và TP2 nếu cả hai đều thiếu
  const getPendingSurveyInfo = (classItem: ClassItem) => {
    const now = new Date()
    const sortedSlots = [...classItem.slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    
    const tpRecord = tpData.find(t => t.classId === classItem.id)

    const tp1Slot = sortedSlots[3]
    const tp2Slot = sortedSlots[7]
    const results: { round: string; missing: number }[] = []

    // TP1: buổi đã qua + có HV
    if (tp1Slot && new Date(tp1Slot.date) < now && tp1Slot.studentsInSlot > 0) {
      if (!tpRecord) {
        results.push({ round: 'TP 1', missing: classItem.studentCount })
      } else {
        const hasSurveyData = tpRecord.tp1 !== null || (tpRecord.tp1_students || []).length > 0
        if (!hasSurveyData) {
          results.push({ round: 'TP 1', missing: classItem.studentCount })
        } else {
          const studentsWithScore = (tpRecord.tp1_students || []).filter(s => s.score !== null && s.score !== undefined)
          const missing = classItem.studentCount - studentsWithScore.length
          if (missing > 0) results.push({ round: 'TP 1', missing })
        }
      }
    }

    // TP2: buổi đã qua + có HV
    if (tp2Slot && new Date(tp2Slot.date) < now && tp2Slot.studentsInSlot > 0) {
      if (!tpRecord) {
        results.push({ round: 'TP 2', missing: classItem.studentCount })
      } else {
        const hasSurveyData = tpRecord.tp2 !== null || (tpRecord.tp2_students || []).length > 0
        if (!hasSurveyData) {
          results.push({ round: 'TP 2', missing: classItem.studentCount })
        } else {
          const studentsWithScore = (tpRecord.tp2_students || []).filter(s => s.score !== null && s.score !== undefined)
          const missing = classItem.studentCount - studentsWithScore.length
          if (missing > 0) results.push({ round: 'TP 2', missing })
        }
      }
    }

    return results.length > 0 ? results : null
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
      <div className="page-banner">
        <div>
          <h1 className="page-banner-title">Danh sách lớp học</h1>
          <p className="page-banner-sub">Quản lý và theo dõi tất cả lớp học</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="page-banner-badge">{filteredClasses.length} / {classes.length} lớp</span>
          <RefreshButton module="classes" />
        </div>
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
        {filteredClasses.map((c) => {
          const pendingSurveyInfo = filters.tpRound === 'pending' ? getPendingSurveyInfo(c) : null
          return (
            <ClassCard 
              key={c.id} 
              item={c} 
              onClick={() => setSelectedClass(c)}
              commentStatus={getCommentStatus(c)}
              hasPendingSurvey={!!pendingSurveyInfo}
              pendingSurveyInfo={pendingSurveyInfo ?? undefined}
            />
          )
        })}
      </div>

      {selectedClass && (
        <ClassDetail 
          classItem={selectedClass} 
          tpRecord={tpData.find(t => t.classId === selectedClass.id) ?? null}
          onClose={() => setSelectedClass(null)} 
        />
      )}

      {showSummary && (
        <SummaryModal classes={filteredClasses} onClose={() => setShowSummary(false)} />
      )}
    </div>
  )
}

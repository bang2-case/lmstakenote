import type { ClassItem, TPRecord } from '../types'

interface Props {
  classItem: ClassItem
  tpRecord?: TPRecord | null
  onClose: () => void
}

const STATUS_LABEL: Record<string, string> = {
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

export default function ClassDetail({ classItem, tpRecord, onClose }: Props) {
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '—'
    const date = new Date(dateStr)
    return date.toLocaleDateString('vi-VN', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit' 
    })
  }

  const sortedSlots = [...classItem.slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  // Tính tên học viên thiếu khảo sát cho từng buổi TP
  const getMissingTpStudents = (slotIndex: number, round: 'tp1' | 'tp2'): string[] => {
    if (!tpRecord) return []
    const slot = sortedSlots[slotIndex]
    if (!slot) return []
    const now = new Date()
    if (new Date(slot.date) >= now) return []
    if (slot.studentsInSlot === 0) return []

    const students = round === 'tp1' ? (tpRecord.tp1_students || []) : (tpRecord.tp2_students || [])
    const roundScore = round === 'tp1' ? tpRecord.tp1 : tpRecord.tp2

    // Chưa fetch được survey data → không hiển thị
    const hasSurveyData = roundScore !== null || students.length > 0
    if (!hasSurveyData) return []

    const studentsWithScore = students.filter(s => s.score !== null && s.score !== undefined)
    const missing = slot.studentsInSlot - studentsWithScore.length
    if (missing <= 0) return []

    const doneNames = studentsWithScore.map(s => s.name)
    return doneNames.length > 0
      ? [`Đã có: ${doneNames.join(', ')} — Còn thiếu ${missing} học viên`]
      : [`Còn thiếu ${missing} học viên`]
  }

  const getSlotClass = (slot: any) => {
    const now = new Date()
    const slotDate = new Date(slot.date)
    const hoursSinceSlot = (now.getTime() - slotDate.getTime()) / (1000 * 60 * 60)
    
    // Chưa tới
    if (slotDate > now) {
      // Tìm buổi tiếp theo (buổi sắp tới gần nhất)
      const upcomingSlots = classItem.slots
        .filter(s => new Date(s.date) > now)
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      
      if (upcomingSlots.length > 0 && upcomingSlots[0].id === slot.id) {
        return 'slot-upcoming' // Buổi tiếp theo
      }
      return 'slot-future' // Các buổi sau
    }
    
    // Đã qua
    if (slot.commentStatus === 'Đã nhận xét') {
      return 'slot-completed'
    }
    
    // Chưa nhận xét
    if (hoursSinceSlot <= 48) {
      return 'slot-warning' // Trong vòng 48h - nhấp nháy vàng
    } else {
      return 'slot-danger' // Quá 48h - nhấp nháy đỏ
    }
  }

  const getSlotStatus = (slot: any) => {
    const now = new Date()
    const slotDate = new Date(slot.date)
    
    if (slotDate > now) {
      return 'Chưa bắt đầu'
    }
    
    return slot.commentStatus
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-banner">
          <div>
            <h2 className="modal-banner-title">{classItem.name}</h2>
            <p className="modal-banner-sub">Thông tin chi tiết lớp học</p>
          </div>
          <span className="modal-banner-badge">{classItem.slots.length} buổi</span>
        </div>

        <div className="modal-header">
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Trạng thái</span>
              <span className="detail-value">{STATUS_LABEL[classItem.status] || classItem.status}</span>
            </div>

            <div className="detail-item">
              <span className="detail-label">Khóa học</span>
              <span className="detail-value">{classItem.course || '—'}</span>
            </div>

            <div className="detail-item">
              <span className="detail-label">Cơ sở</span>
              <span className="detail-value">{classItem.centre || '—'}</span>
            </div>

            <div className="detail-item">
              <span className="detail-label">Số buổi</span>
              <span className="detail-value">{classItem.sessions || '—'}</span>
            </div>

            <div className="detail-item">
              <span className="detail-label">Số học viên</span>
              <span className="detail-value">{classItem.studentCount}</span>
            </div>

            {classItem.totalSlotsWithStudents > 0 && (
              <div className="detail-item">
                <span className="detail-label">Nhận xét</span>
                <span className="detail-value">
                  {classItem.commentPercentage}% ({classItem.slotsWithFullComments}/{classItem.totalSlotsWithStudents} buổi)
                </span>
              </div>
            )}

            <div className="detail-item">
              <span className="detail-label">Ngày bắt đầu</span>
              <span className="detail-value">{formatDate(classItem.startDate)}</span>
            </div>

            <div className="detail-item">
              <span className="detail-label">Ngày kết thúc</span>
              <span className="detail-value">{formatDate(classItem.endDate)}</span>
            </div>
          </div>

          {classItem.teachers.length > 0 && (
            <div className="detail-section">
              <h3>Giáo viên</h3>
              <div className="teacher-list">
                {classItem.teachers.map((t, i) => (
                  <div key={i} className="teacher-item">
                    <span className="teacher-name">{t.name}</span>
                    {t.role && <span className="teacher-role">{t.role}</span>}
                    {t.email && <span className="teacher-email">{t.email}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="modal-body">
          {classItem.slots.length > 0 && (
            <>
              <h3 className="schedule-title-fixed">Lịch học ({classItem.slots.length} buổi)</h3>
              <div className="slot-list-container">
                {sortedSlots.map((s, index) => {
                  // Kiểm tra đây có phải buổi TP không (buổi 4 = index 3, buổi 8 = index 7)
                  const isTP1Slot = index === 3
                  const isTP2Slot = index === 7
                  const missingTp = isTP1Slot
                    ? getMissingTpStudents(3, 'tp1')
                    : isTP2Slot
                    ? getMissingTpStudents(7, 'tp2')
                    : []

                  return (
                    <div key={s.id} className={`slot-item-detail ${getSlotClass(s)}`}>
                      <div className="slot-date">
                        Buổi {index + 1} - {formatDate(s.date)}
                        {(isTP1Slot || isTP2Slot) && (
                          <span style={{
                            marginLeft: 8,
                            fontSize: 11,
                            fontWeight: 700,
                            background: '#dbeafe',
                            color: '#1d4ed8',
                            padding: '1px 6px',
                            borderRadius: 4,
                          }}>
                            {isTP1Slot ? 'TP 1' : 'TP 2'}
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                        <div className="slot-status">{getSlotStatus(s)}</div>
                        {missingTp.length > 0 && (
                          <div style={{
                            fontSize: 11,
                            color: '#dc2626',
                            fontWeight: 600,
                            textAlign: 'right',
                            maxWidth: 220,
                            whiteSpace: 'normal',
                            wordBreak: 'break-word',
                          }}>
                            📊 {missingTp[0]}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

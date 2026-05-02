import type { ClassItem } from '../types'

interface Props {
  classItem: ClassItem
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

export default function ClassDetail({ classItem, onClose }: Props) {
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
        <button className="modal-close" onClick={onClose}>✕</button>
        
        <div className="modal-header">
          <h2 className="modal-title">{classItem.name}</h2>
          
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
                {sortedSlots.map((s, index) => (
                  <div key={s.id} className={`slot-item-detail ${getSlotClass(s)}`}>
                    <div className="slot-date">Buổi {index + 1} - {formatDate(s.date)}</div>
                    <div className="slot-status">
                      {getSlotStatus(s)}
                    </div>
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

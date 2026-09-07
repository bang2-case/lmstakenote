import { useEffect, useState } from 'react'
import type { ClassItem, TPRecord } from '../types'

interface Props {
  classItem: ClassItem
  tpRecord?: TPRecord | null
  onClose: () => void
}

type DuplicateModeKey = 'same_student' | 'any_student'

interface DuplicateSide {
  slotId: string
  sessionIndex: number
  slotDate: string
  studentId: string | null
  studentName: string
  comment: string
}

interface DuplicateMatch {
  id: string
  similarity: number
  commonText: string
  left: DuplicateSide
  right: DuplicateSide
}

interface DuplicateModeResult {
  totalPairs: number
  totalMatches: number
  returnedMatches: number
  hasMore: boolean
  matches: DuplicateMatch[]
}

interface CommentDuplicateReport {
  classId: string
  threshold: number
  totalComments: number
  modes: Record<DuplicateModeKey, DuplicateModeResult>
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
  const [duplicateReportMode, setDuplicateReportMode] = useState<DuplicateModeKey | null>(null)
  const [duplicateReport, setDuplicateReport] = useState<CommentDuplicateReport | null>(null)
  const [duplicateLoading, setDuplicateLoading] = useState(false)
  const [duplicateError, setDuplicateError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setDuplicateLoading(true)
    setDuplicateError(null)
    setDuplicateReport(null)

    fetch(`/api/classes/${encodeURIComponent(classItem.id)}/comment-duplicates`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: CommentDuplicateReport) => {
        if (alive) setDuplicateReport(data)
      })
      .catch((err) => {
        if (alive) setDuplicateError(err.message)
      })
      .finally(() => {
        if (alive) setDuplicateLoading(false)
      })

    return () => {
      alive = false
    }
  }, [classItem.id])

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

  // Tính thông tin TP survey cho buổi TP
  const getTpSurveyInfo = (slotIndex: number, round: 'tp1' | 'tp2'): {
    text: string
    type: 'none' | 'no_survey' | 'missing' | 'complete'
  } => {
    const slot = sortedSlots[slotIndex]
    if (!slot) return { text: '', type: 'none' }
    const now = new Date()
    if (new Date(slot.date) >= now) return { text: '', type: 'none' }

    // Tổng HV lớp (tính cả absent)
    const totalStudents = classItem.studentCount

    if (!tpRecord) {
      // Không có TP record → chưa có ai làm
      return {
        text: 'Chưa có học viên nào thực hiện khảo sát',
        type: 'no_survey',
      }
    }

    const students = round === 'tp1' ? (tpRecord.tp1_students || []) : (tpRecord.tp2_students || [])
    const roundScore = round === 'tp1' ? tpRecord.tp1 : tpRecord.tp2
    const hasSurveyData = roundScore !== null || students.length > 0

    if (!hasSurveyData) {
      return {
        text: 'Chưa có học viên nào thực hiện khảo sát',
        type: 'no_survey',
      }
    }

    const studentsWithScore = students.filter(s => s.score !== null && s.score !== undefined)
    const doneCount = studentsWithScore.length
    const missing = totalStudents - doneCount

    if (missing <= 0) {
      return {
        text: `Đã có: ${studentsWithScore.map(s => s.name).join(', ')} (${doneCount}/${totalStudents} HV)`,
        type: 'complete',
      }
    }

    const doneNames = studentsWithScore.map(s => s.name)
    return {
      text: doneNames.length > 0
        ? `Đã có: ${doneNames.join(', ')} — Còn thiếu ${missing}/${totalStudents} học viên`
        : `Còn thiếu ${missing}/${totalStudents} học viên`,
      type: 'missing',
    }
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

  const sameStudentResult = duplicateReport?.modes.same_student ?? null
  const anyStudentResult = duplicateReport?.modes.any_student ?? null
  const activeDuplicateResult = duplicateReportMode ? duplicateReport?.modes[duplicateReportMode] ?? null : null
  const activeDuplicateTitle = duplicateReportMode === 'same_student'
    ? 'Trùng nhận xét cùng học viên'
    : 'Trùng nhận xét khác học viên'

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

        <div className="modal-body class-detail-body">
          <section className="duplicate-section">
            <div className="duplicate-section-head">
              <div>
                <h3 className="duplicate-title">Kiểm tra trùng nhận xét</h3>
                <p className="duplicate-subtitle">
                  Ngưỡng hiển thị từ {duplicateReport?.threshold ?? 70}% trở lên. Bấm vào từng chế độ để xem báo cáo chi tiết.
                </p>
              </div>
            </div>

            {duplicateLoading && (
              <div className="duplicate-state">Đang kiểm tra nhận xét...</div>
            )}

            {!duplicateLoading && duplicateError && (
              <div className="duplicate-state duplicate-state-error">
                Chưa tải được dữ liệu trùng lặp. Hãy refresh dữ liệu lớp rồi thử lại.
              </div>
            )}

            {!duplicateLoading && !duplicateError && duplicateReport && sameStudentResult && anyStudentResult && (
              <>
                <div className="duplicate-stats">
                  <span>{duplicateReport.totalComments} nhận xét</span>
                  <span>{sameStudentResult.totalMatches + anyStudentResult.totalMatches} lượt cặp trùng</span>
                  <span>Đã so sánh {sameStudentResult.totalPairs + anyStudentResult.totalPairs} cặp</span>
                </div>

                {duplicateReport.totalComments === 0 ? (
                  <div className="duplicate-state">
                    Chưa có dữ liệu nhận xét chi tiết. Hãy refresh dữ liệu lớp để hệ thống lưu nội dung nhận xét mới nhất.
                  </div>
                ) : (
                  <div className="duplicate-mode-grid">
                    <button
                      type="button"
                      className="duplicate-mode-card"
                      onClick={() => setDuplicateReportMode('same_student')}
                    >
                      <span className="duplicate-mode-title">Cùng học viên</span>
                      <span className="duplicate-mode-count">{sameStudentResult.totalMatches} cặp trùng</span>
                      <span className="duplicate-mode-meta">{sameStudentResult.totalPairs} cặp đã so sánh</span>
                    </button>
                    <button
                      type="button"
                      className="duplicate-mode-card"
                      onClick={() => setDuplicateReportMode('any_student')}
                    >
                      <span className="duplicate-mode-title">Khác học viên</span>
                      <span className="duplicate-mode-count">{anyStudentResult.totalMatches} cặp trùng</span>
                      <span className="duplicate-mode-meta">{anyStudentResult.totalPairs} cặp đã so sánh</span>
                    </button>
                  </div>
                )}
              </>
            )}
          </section>

          {classItem.slots.length > 0 && (
            <>
              <h3 className="schedule-title-fixed">Lịch học ({classItem.slots.length} buổi)</h3>
              <div className="slot-list-container">
                {sortedSlots.map((s, index) => {
                  // Kiểm tra đây có phải buổi TP không (buổi 4 = index 3, buổi 8 = index 7)
                  const isTP1Slot = index === 3
                  const isTP2Slot = index === 7
                  const tpInfo = isTP1Slot
                    ? getTpSurveyInfo(3, 'tp1')
                    : isTP2Slot
                    ? getTpSurveyInfo(7, 'tp2')
                    : { text: '', type: 'none' as const }

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
                        {tpInfo.type !== 'none' && tpInfo.text && (
                          <div style={{
                            fontSize: 11,
                            color: tpInfo.type === 'no_survey' ? '#6b7280'
                                 : tpInfo.type === 'missing'   ? '#dc2626'
                                 : '#16a34a',
                            fontWeight: 600,
                            textAlign: 'right',
                            maxWidth: 260,
                            whiteSpace: 'normal',
                            wordBreak: 'break-word',
                          }}>
                            📊 {tpInfo.text}
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

        {duplicateReportMode && duplicateReport && activeDuplicateResult && (
          <div className="duplicate-report-overlay" onClick={() => setDuplicateReportMode(null)}>
            <div className="duplicate-report-modal" onClick={(e) => e.stopPropagation()}>
              <div className="duplicate-report-banner">
                <div>
                  <p className="duplicate-report-sub">{classItem.name}</p>
                  <h3 className="duplicate-report-title">{activeDuplicateTitle}</h3>
                </div>
                <button
                  type="button"
                  className="duplicate-report-close"
                  onClick={() => setDuplicateReportMode(null)}
                  aria-label="Đóng báo cáo"
                >
                  ×
                </button>
              </div>

              <div className="duplicate-report-summary">
                <span>{duplicateReport.totalComments} nhận xét</span>
                <span>{activeDuplicateResult.totalMatches} cặp trùng từ {duplicateReport.threshold}%</span>
                <span>{activeDuplicateResult.totalPairs} cặp đã so sánh</span>
              </div>

              {activeDuplicateResult.matches.length === 0 ? (
                <div className="duplicate-report-empty">
                  Không có cặp nhận xét nào trùng từ ngưỡng này.
                </div>
              ) : (
                <div className="duplicate-report-list">
                  {activeDuplicateResult.matches.map((match, index) => (
                    <article key={match.id} className="duplicate-report-item">
                      <div className="duplicate-report-item-head">
                        <div>
                          <span className="duplicate-report-index">#{index + 1}</span>
                          <span className="duplicate-report-pair">
                            Buổi {match.left.sessionIndex} ↔ Buổi {match.right.sessionIndex}
                          </span>
                        </div>
                        <span className="duplicate-report-percent">{match.similarity}% trùng</span>
                      </div>

                      <div className="duplicate-report-meta-grid">
                        <div>
                          <span className="duplicate-report-label">Nhận xét A</span>
                          <strong>{match.left.studentName || '—'}</strong>
                          <span>Buổi {match.left.sessionIndex} · {formatDate(match.left.slotDate)}</span>
                        </div>
                        <div>
                          <span className="duplicate-report-label">Nhận xét B</span>
                          <strong>{match.right.studentName || '—'}</strong>
                          <span>Buổi {match.right.sessionIndex} · {formatDate(match.right.slotDate)}</span>
                        </div>
                      </div>

                      {match.commonText && (
                        <div className="duplicate-report-common">
                          <span>Đoạn giống rõ nhất</span>
                          <p>{match.commonText}</p>
                        </div>
                      )}

                      <div className="duplicate-report-comments">
                        <div>
                          <span>Nhận xét A</span>
                          <p>{match.left.comment}</p>
                        </div>
                        <div>
                          <span>Nhận xét B</span>
                          <p>{match.right.comment}</p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}

              {activeDuplicateResult.hasMore && (
                <div className="duplicate-report-empty">
                  Đang hiển thị {activeDuplicateResult.returnedMatches}/{activeDuplicateResult.totalMatches} cặp có độ trùng cao nhất.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

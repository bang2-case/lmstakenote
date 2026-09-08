import { useEffect, useMemo, useState } from 'react'
import { useAssignments } from '../hooks/useAssignments'
import { useClasses } from '../hooks/useClasses'
import SingleSelect from '../components/SingleSelect'
import MultiSelect from '../components/MultiSelect'
import RefreshButton from '../components/RefreshButton'
import DatePickerInput from '../components/DatePickerInput'
import type {
  AssignmentClassRecord,
  AssignmentFetchError,
  AssignmentLesson,
  AssignmentStudent,
  AssignmentSubmission,
  ClassItem,
  Slot,
  Teacher,
} from '../types'
import { AREA_OPTIONS, centreMatchesArea, filterCentresByArea } from '../utils/areas'

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

interface AssignmentFilters {
  search: string
  area: string
  centre: string
  mentor: string
  block: string
  slot: string
  slotTo: string
  classStatus: string[]
  syncStatus: '' | 'synced' | 'missing' | 'mappingError' | 'fetchError' | 'outOfScope' | 'needsMarking' | 'lowSubmission'
  gradingStatus: '' | 'marked' | 'unmarked'
}

type AssignmentSyncState = 'synced' | 'missing' | 'mappingError' | 'fetchError' | 'outOfScope'

interface AssignmentRow {
  classId: string
  className: string
  centre: string | null
  block: string
  classStatus: string
  teachers: Teacher[]
  slots: Slot[]
  studentCount: number
  lessonCount: number
  submittedCount: number
  gradableSubmittedCount: number
  markedCount: number
  inProgressCount: number
  needsMarkingCount: number
  expectedCount: number
  gradingRate: number | null
  averageScore: number | null
  record: AssignmentClassRecord | null
  fetchError: AssignmentFetchError | null
  syncState: AssignmentSyncState
}

interface SlotStudent {
  id: string
  name: string
  status?: string
}

function isSubmitted(submission: AssignmentSubmission) {
  const status = (submission.status || '').toUpperCase()
  return status === 'SUBMITTED' || status === 'MARKED' || Boolean(submission.submittedAt) || (submission.submittedCount ?? 0) > 0
}

function isResubmitPending(submission: AssignmentSubmission) {
  const status = (submission.status || '').toUpperCase()
  return status === 'REDO' || status === 'RE_SUBMITTED'
}

function isGradableSubmission(submission: AssignmentSubmission) {
  return isSubmitted(submission) && !isResubmitPending(submission)
}

function isMarked(submission: AssignmentSubmission) {
  const status = (submission.status || '').toUpperCase()
  return status === 'MARKED' || Boolean(submission.markedAt) || Boolean(submission.markedBy)
}

function isHomeworkSubmission(submission: AssignmentSubmission) {
  const type = (submission.type || '').toUpperCase()
  const category = (submission.category || '').toUpperCase()
  return type === 'UPLOAD_FILE' || category.startsWith('PRACTICE_TASK')
}

function getHomeworkSubmissions(submissions: AssignmentSubmission[]) {
  return submissions.filter(isHomeworkSubmission)
}

function pct(value: number, total: number) {
  return total > 0 ? Math.round((value / total) * 100) : null
}

function fmtPct(value: number | null) {
  return value === null ? '—' : `${value}%`
}

function fmtScore(score: number | null) {
  if (score === null) return '—'
  return Number.isInteger(score) ? String(score) : score.toFixed(1)
}

function scoreOf(submission: AssignmentSubmission) {
  const score = Number(submission.score)
  return Number.isFinite(score) ? score : 0
}

function normalizeName(value: string | null | undefined) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function formatDate(value: string | null | undefined) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function toLocalDateStr(value: string | null | undefined) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return (
    date.getFullYear() +
    '-' +
    String(date.getMonth() + 1).padStart(2, '0') +
    '-' +
    String(date.getDate()).padStart(2, '0')
  )
}

function isSlotInDateRange(slot: Slot, from: string, to: string) {
  const slotDateStr = toLocalDateStr(slot.date)
  if (!slotDateStr) return false
  if (from && to) {
    return from === to ? slotDateStr === from : slotDateStr >= from && slotDateStr <= to
  }
  if (from) return slotDateStr >= from
  if (to) return slotDateStr <= to
  return true
}

function isAssignmentSyncTarget(classItem: ClassItem) {
  if (classItem.status === 'RUNNING') return true
  if (classItem.status !== 'FINISHED' || !classItem.endDate) return false
  const endDate = new Date(classItem.endDate)
  if (Number.isNaN(endDate.getTime())) return false
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 90)
  return endDate >= cutoff
}

function getSyncState(record: AssignmentClassRecord | null, fetchError: AssignmentFetchError | null, classItem: ClassItem): AssignmentSyncState {
  if (record) return 'synced'
  if (fetchError?.errorType === 'mapping') return 'mappingError'
  if (fetchError) return 'fetchError'
  if (!isAssignmentSyncTarget(classItem)) return 'outOfScope'
  return 'missing'
}

function ProgressCell({ value, total, tone, showCount = false }: {
  value: number
  total: number
  tone: 'green' | 'yellow' | 'red' | 'blue'
  showCount?: boolean
}) {
  const percent = pct(value, total)
  return (
    <div className="assignment-progress">
      <div className="assignment-progress-track">
        <div className={`assignment-progress-fill assignment-progress-${tone}`} style={{ width: `${percent ?? 0}%` }} />
      </div>
      <span className="assignment-progress-label">
        <strong>{fmtPct(percent)}</strong>
        {showCount && total > 0 && <small>{value}/{total}</small>}
      </span>
    </div>
  )
}

function StatusPill({ row }: { row: AssignmentRow }) {
  if (!row.record) {
    if (row.syncState === 'mappingError') return <span className="assignment-pill assignment-pill-red">Lỗi mapping Denise</span>
    if (row.syncState === 'fetchError') return <span className="assignment-pill assignment-pill-red">Tải lỗi</span>
    if (row.syncState === 'outOfScope') return <span className="assignment-pill assignment-pill-muted">Ngoài phạm vi</span>
    return <span className="assignment-pill assignment-pill-muted">Chưa đồng bộ</span>
  }
  if (row.expectedCount === 0) return <span className="assignment-pill assignment-pill-muted">Chưa có bài</span>
  if (row.needsMarkingCount > 0) return <span className="assignment-pill assignment-pill-red">Cần chấm</span>
  const submittedRate = pct(row.submittedCount, row.expectedCount) ?? 0
  if (submittedRate < 70) return <span className="assignment-pill assignment-pill-yellow">Nộp thấp</span>
  return <span className="assignment-pill assignment-pill-green">Ổn</span>
}

function buildRow(classItem: ClassItem, record: AssignmentClassRecord | null, fetchError: AssignmentFetchError | null): AssignmentRow {
  const syncState = getSyncState(record, fetchError, classItem)
  if (!record) {
    return {
      classId: classItem.id,
      className: classItem.name,
      centre: classItem.centre,
      block: classItem.block,
      classStatus: classItem.status,
      teachers: classItem.teachers,
      slots: classItem.slots || [],
      studentCount: classItem.studentCount,
      lessonCount: 0,
      submittedCount: 0,
      gradableSubmittedCount: 0,
      markedCount: 0,
      inProgressCount: 0,
      needsMarkingCount: 0,
      expectedCount: 0,
      gradingRate: null,
      averageScore: null,
      record: null,
      fetchError,
      syncState,
    }
  }

  const activeLessons = record.lessons.filter((lesson) => lesson.isActive)
  const homeworkSubmissions = getHomeworkSubmissions(record.submissions)
  const expectedCount = record.expectedCount ?? (homeworkSubmissions.length || record.students.length * activeLessons.length)
  const submitted = homeworkSubmissions.filter(isSubmitted)
  const gradableSubmitted = homeworkSubmissions.filter(isGradableSubmission)
  const marked = gradableSubmitted.filter(isMarked)
  const submittedCount = record.submittedCount ?? submitted.length
  const gradableSubmittedCount = record.gradableSubmittedCount ?? (
    record.submissions.length === 0 && record.submittedCount != null
      ? record.submittedCount
      : gradableSubmitted.length
  )
  const markedCount = record.markedCount ?? marked.length
  const scored = submitted.filter((submission) => scoreOf(submission) > 0)
  const averageScore = scored.length
    ? Math.round(scored.reduce((sum, submission) => sum + scoreOf(submission), 0) / scored.length)
    : null

  return {
    classId: classItem.id,
    className: record.className || classItem.name,
    centre: record.centre ?? classItem.centre,
    block: record.block || classItem.block,
    classStatus: record.status || classItem.status,
    teachers: record.teachers.length ? record.teachers : classItem.teachers,
    slots: classItem.slots || [],
    studentCount: record.studentCount ?? (record.students.length || classItem.studentCount),
    lessonCount: record.lessonCount ?? activeLessons.length,
    submittedCount,
    gradableSubmittedCount,
    markedCount,
    inProgressCount: record.inProgressCount ?? homeworkSubmissions.filter((submission) => submission.status === 'IN_PROGRESS').length,
    needsMarkingCount: record.needsMarkingCount ?? gradableSubmitted.filter((submission) => !isMarked(submission)).length,
    expectedCount,
    gradingRate: pct(markedCount, gradableSubmittedCount),
    averageScore: record.averageScore ?? averageScore,
    record,
    fetchError,
    syncState,
  }
}

function getLessonSubmissions(record: AssignmentClassRecord, lesson: AssignmentLesson, slot?: Slot) {
  const items = record.submissions.filter((submission) => submission.lessonId === lesson.id)
  const hasSessionScopedData = items.some((submission) => Boolean(submission.classSessionId))
  if (slot && hasSessionScopedData) {
    return items.filter((submission) => submission.classSessionId === slot.id)
  }
  return items
}

function findStudent(record: AssignmentClassRecord, slotStudent: SlotStudent) {
  const byId = new Map<string, AssignmentStudent>()
  const byName = new Map<string, AssignmentStudent>()
  record.students.forEach((student) => {
    if (student.id) byId.set(student.id, student)
    if (student.studentUid) byId.set(student.studentUid, student)
    byName.set(normalizeName(student.displayName), student)
  })

  return byId.get(slotStudent.id) || byName.get(normalizeName(slotStudent.name)) || {
    id: slotStudent.id,
    displayName: slotStudent.name || 'Không rõ học viên',
    studentUid: slotStudent.id || slotStudent.name,
  }
}

function getStudentSubmissions(student: AssignmentStudent, submissions: AssignmentSubmission[]) {
  const ids = new Set([student.id, student.studentUid].filter(Boolean))
  return submissions.filter((submission) => (
    ids.has(submission.studentUid) ||
    ids.has(submission.studentOriginalId || '')
  ))
}

function studentKey(student: AssignmentStudent) {
  return student.id || student.studentUid || normalizeName(student.displayName)
}

function mergeSessionStudents(record: AssignmentClassRecord, slotStudents: SlotStudent[]) {
  const orderedStudents = slotStudents.map((student) => findStudent(record, student))
  const seen = new Set(orderedStudents.map(studentKey))

  record.students.forEach((student) => {
    const key = studentKey(student)
    if (!seen.has(key)) {
      orderedStudents.push(student)
      seen.add(key)
    }
  })

  return orderedStudents
}

function getSessionSlot(row: AssignmentRow, record: AssignmentClassRecord, lesson: AssignmentLesson) {
  const byClassSessionId = record.submissions.find((submission) => (
    submission.lessonId === lesson.id && submission.classSessionId
  ))?.classSessionId
  if (byClassSessionId) {
    const exact = row.slots.find((slot) => slot.id === byClassSessionId)
    if (exact) return exact
  }

  const orderedSlots = [...row.slots].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
  const displayOrder = Number(lesson.displayOrder || 0)
  return displayOrder > 0 ? orderedSlots[displayOrder - 1] : undefined
}

function AssignmentsModal({ row, onClose }: { row: AssignmentRow; onClose: () => void }) {
  const hasInlineDetail = Boolean(row.record && (
    row.record.students.length > 0 ||
    row.record.lessons.length > 0 ||
    row.record.submissions.length > 0
  ))
  const [detail, setDetail] = useState<AssignmentClassRecord | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [slotStudentsBySlotId, setSlotStudentsBySlotId] = useState<Record<string, SlotStudent[]>>({})
  const record = detail ?? (hasInlineDetail ? row.record : null)
  const activeLessons = record
    ? record.lessons.filter((lesson) => lesson.isActive).sort((a, b) => a.displayOrder - b.displayOrder)
    : []

  useEffect(() => {
    let cancelled = false
    setDetail(null)
    setDetailError(null)

    if (!row.record || hasInlineDetail) {
      setDetailLoading(false)
      return () => { cancelled = true }
    }

    setDetailLoading(true)
    fetch(`/api/assignments/${row.classId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: AssignmentClassRecord) => {
        if (!cancelled) setDetail(data)
      })
      .catch((error) => {
        if (!cancelled) setDetailError(error.message)
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })

    return () => { cancelled = true }
  }, [row.classId, row.record, hasInlineDetail])

  useEffect(() => {
    let cancelled = false
    setSlotStudentsBySlotId({})

    if (!row.record || row.slots.length === 0) {
      return () => { cancelled = true }
    }

    fetch(`/api/classes/${row.classId}/slot-students`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: Record<string, SlotStudent[]>) => {
        if (!cancelled) setSlotStudentsBySlotId(data || {})
      })
      .catch(() => {
        if (!cancelled) setSlotStudentsBySlotId({})
      })

    return () => { cancelled = true }
  }, [row.classId, row.record, row.slots.length])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="assignment-modal-wrap" onClick={(e) => e.stopPropagation()}>
        <div className="assignment-modal-banner">
          <div className="assignment-modal-banner-text">
            <p className="assignment-modal-banner-sub">
              {row.centre || '—'} · {(STATUS_MAP[row.classStatus] ?? row.classStatus) || '—'} · {row.teachers[0]?.name || '—'}
            </p>
            <h2 className="assignment-modal-banner-title">{row.className}</h2>
          </div>
          <div className="assignment-modal-side">
            <div className="assignment-modal-kpis">
              <div className="assignment-modal-kpi">
                <span>{fmtPct(pct(row.submittedCount, row.expectedCount))}</span>
                <small>Đã nộp</small>
              </div>
              <div className="assignment-modal-kpi">
                <span>{fmtPct(pct(row.markedCount, row.gradableSubmittedCount))}</span>
                <small>Đã chấm</small>
              </div>
            </div>
            <button className="assignment-modal-close" type="button" onClick={onClose} aria-label="Đóng">×</button>
          </div>
        </div>

        {!row.record ? (
          <div className="assignment-modal-empty">
            {row.syncState === 'mappingError'
              ? `LMS chưa map course của lớp này trên Denise: ${row.fetchError?.message || 'không rõ lỗi'}`
              : row.syncState === 'fetchError'
                ? `Lần tải gần nhất bị lỗi: ${row.fetchError?.message || 'không rõ lỗi'}`
                : row.syncState === 'outOfScope'
                  ? 'Lớp này nằm ngoài phạm vi đồng bộ bài tập hiện tại.'
                  : 'Chưa có dữ liệu bài tập cho lớp này. Hãy bấm tải dữ liệu để đồng bộ từ LMS.'}
          </div>
        ) : detailLoading ? (
          <div className="assignment-modal-empty">
            Đang tải chi tiết bài tập của lớp...
          </div>
        ) : detailError && !record ? (
          <div className="assignment-modal-empty">
            Không tải được chi tiết bài tập của lớp này.
          </div>
        ) : !record ? (
          <div className="assignment-modal-empty">
            Chưa có dữ liệu chi tiết bài tập cho lớp này.
          </div>
        ) : activeLessons.length === 0 ? (
          <div className="assignment-modal-empty">
            LMS chưa trả về lesson/buổi học có bài tập cho lớp này.
          </div>
        ) : (
          <div className="assignment-session-list">
            {activeLessons.map((lesson, index) => {
              const slot = getSessionSlot(row, record, lesson)
              const lessonSubmissions = getLessonSubmissions(record, lesson, slot)
              const studentsForSlot = slot
                ? (slotStudentsBySlotId[slot.id] ?? slot.students ?? [])
                : []
              const sessionStudents = studentsForSlot.length
                ? mergeSessionStudents(record, studentsForSlot)
                : record.students
              const sessionRows = sessionStudents.map((student) => {
                const studentSubmissions = getHomeworkSubmissions(getStudentSubmissions(student, lessonSubmissions))
                const submittedItems = studentSubmissions.filter(isSubmitted)
                const gradableItems = submittedItems.filter(isGradableSubmission)
                const markedItems = gradableItems.filter(isMarked)
                const scoredItems = submittedItems.filter((submission) => scoreOf(submission) > 0)
                const avgScore = scoredItems.length
                  ? scoredItems.reduce((sum, submission) => sum + scoreOf(submission), 0) / scoredItems.length
                  : null
                return {
                  student,
                  submitted: submittedItems.length > 0,
                  resubmitPending: submittedItems.some(isResubmitPending),
                  gradable: gradableItems.length > 0,
                  marked: gradableItems.length > 0 && markedItems.length === gradableItems.length,
                  score: avgScore,
                  submissionCount: submittedItems.length,
                  types: Array.from(new Set(submittedItems.map((submission) => submission.type).filter(Boolean))),
                }
              })
              const submittedStudents = sessionRows.filter((item) => item.submitted).length
              const gradableStudents = sessionRows.filter((item) => item.gradable).length
              const markedStudents = sessionRows.filter((item) => item.marked).length
              const sessionGradingRate = pct(markedStudents, gradableStudents)
              const submittedAssignmentCount = sessionRows.reduce((sum, item) => sum + item.submissionCount, 0)
              const expectedAssignmentCount = sessionRows.length

              return (
                <section key={lesson.id} className="assignment-session-card">
                  <div className="assignment-session-head">
                    <div className="assignment-lesson-main">
                      <span className="assignment-lesson-order">#{lesson.displayOrder || index + 1}</span>
                      <div>
                        <h3>{lesson.name}</h3>
                        <p>
                          {slot ? `Buổi ${lesson.displayOrder || index + 1} · ${formatDate(slot.date)}` : `Buổi ${lesson.displayOrder || index + 1} · Chưa khớp lịch`}
                          {' · '}
                          {lesson.type}
                        </p>
                      </div>
                    </div>
                    <div className="assignment-lesson-stats">
                      <span>HV nộp <strong>{submittedStudents}/{sessionRows.length}</strong></span>
                      <span>HV đã chấm <strong>{markedStudents}/{gradableStudents}</strong></span>
                      <span>Tỉ lệ chấm <strong>{fmtPct(sessionGradingRate)}</strong></span>
                      <span>Lượt bài <strong>{submittedAssignmentCount}/{expectedAssignmentCount}</strong></span>
                    </div>
                  </div>

                  <div className="assignment-student-table-wrap">
                    <table className="assignment-student-table">
                      <thead>
                        <tr>
                          <th>Học viên</th>
                          <th>Nộp bài</th>
                          <th>Chấm bài</th>
                          <th>Lượt bài</th>
                          <th>Điểm</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessionRows.map((item) => (
                          <tr key={`${lesson.id}-${item.student.studentUid || item.student.id}`}>
                            <td className="assignment-student-name" data-label="Học viên">{item.student.displayName}</td>
                            <td data-label="Nộp bài">
                              <span className={`assignment-student-status ${item.submitted ? 'assignment-status-done' : 'assignment-status-missing'}`}>
                                {item.submitted ? 'Đã nộp' : 'Chưa nộp'}
                              </span>
                            </td>
                            <td data-label="Chấm bài">
                              <span className={`assignment-student-status ${item.marked ? 'assignment-status-marked' : item.resubmitPending ? 'assignment-status-neutral' : item.gradable ? 'assignment-status-unmarked' : 'assignment-status-neutral'}`}>
                                {!item.submitted ? '—' : item.resubmitPending ? 'Cần nộp lại' : item.marked ? 'Đã chấm' : item.gradable ? 'Chưa chấm' : '—'}
                              </span>
                            </td>
                            <td data-label="Lượt bài">{item.submissionCount || '—'}{item.types.length ? ` · ${item.types.join(', ')}` : ''}</td>
                            <td data-label="Điểm">{fmtScore(item.score)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function AssignmentsPage() {
  const { classes, loading: classesLoading, error: classesError } = useClasses({ includeSlots: false })
  const { assignmentData, assignmentErrors, loading: assignmentsLoading, error: assignmentsError } = useAssignments()
  const [filters, setFilters] = useState<AssignmentFilters>({
    search: '',
    area: '',
    centre: '',
    mentor: '',
    block: '',
    slot: '',
    slotTo: '',
    classStatus: [],
    syncStatus: '',
    gradingStatus: '',
  })
  const [selectedRow, setSelectedRow] = useState<AssignmentRow | null>(null)

  const recordsByClassId = useMemo(() => {
    const map = new Map<string, AssignmentClassRecord>()
    assignmentData.forEach((record) => map.set(record.classId, record))
    return map
  }, [assignmentData])

  const errorsByClassId = useMemo(() => {
    const map = new Map<string, AssignmentFetchError>()
    assignmentErrors.forEach((fetchError) => map.set(fetchError.classId, fetchError))
    return map
  }, [assignmentErrors])

  const rows = useMemo(
    () => classes.map((classItem) => buildRow(
      classItem,
      recordsByClassId.get(classItem.id) ?? null,
      errorsByClassId.get(classItem.id) ?? null
    )),
    [classes, errorsByClassId, recordsByClassId]
  )

  const { centres, mentors, blocks, classStatuses } = useMemo(() => {
    const cs = new Set<string>()
    const ms = new Set<string>()
    const bs = new Set<string>()
    const statuses = new Set<string>()
    rows.forEach((row) => {
      if (row.centre) cs.add(row.centre)
      if (row.block) bs.add(row.block)
      if (row.classStatus) statuses.add(row.classStatus)
      row.teachers.forEach((teacher) => ms.add(teacher.name))
    })
    return {
      centres: Array.from(cs).sort(),
      mentors: Array.from(ms).sort(),
      blocks: Array.from(bs).sort(),
      classStatuses: Array.from(statuses).sort((a, b) => (STATUS_MAP[a] ?? a).localeCompare(STATUS_MAP[b] ?? b)),
    }
  }, [rows])

  const centreOptions = useMemo(() => filterCentresByArea(centres, filters.area), [centres, filters.area])

  const update = (key: keyof AssignmentFilters, value: string) =>
    setFilters((current) => ({ ...current, [key]: value }))

  const updateArea = (area: string) =>
    setFilters((current) => ({
      ...current,
      area,
      centre: area && !centreMatchesArea(current.centre, area) ? '' : current.centre,
    }))

  const resetFilters = () =>
    setFilters({
      search: '',
      area: '',
      centre: '',
      mentor: '',
      block: '',
      slot: '',
      slotTo: '',
      classStatus: [],
      syncStatus: '',
      gradingStatus: '',
    })

  const filtered = useMemo(() => {
    return rows.filter((row) => {
      if (filters.search && !row.className.toLowerCase().includes(filters.search.toLowerCase())) return false
      if (filters.area && !centreMatchesArea(row.centre, filters.area)) return false
      if (filters.centre && row.centre !== filters.centre) return false
      if (filters.mentor && !row.teachers.some((teacher) => teacher.name === filters.mentor)) return false
      if (filters.block && row.block !== filters.block) return false
      if ((filters.slot || filters.slotTo) && !row.slots.some((slot) => isSlotInDateRange(slot, filters.slot, filters.slotTo))) return false
      if (filters.classStatus.length > 0 && !filters.classStatus.includes(row.classStatus)) return false
      if (filters.syncStatus === 'synced' && !row.record) return false
      if (filters.syncStatus === 'missing' && row.syncState !== 'missing') return false
      if (filters.syncStatus === 'mappingError' && row.syncState !== 'mappingError') return false
      if (filters.syncStatus === 'fetchError' && row.syncState !== 'fetchError') return false
      if (filters.syncStatus === 'outOfScope' && row.syncState !== 'outOfScope') return false
      if (filters.syncStatus === 'needsMarking' && row.needsMarkingCount === 0) return false
      if (filters.syncStatus === 'lowSubmission' && (!row.record || row.expectedCount === 0 || (pct(row.submittedCount, row.expectedCount) ?? 100) >= 70)) return false
      if (filters.gradingStatus === 'marked' && (!row.record || row.gradableSubmittedCount === 0 || row.needsMarkingCount > 0)) return false
      if (filters.gradingStatus === 'unmarked' && (!row.record || row.needsMarkingCount === 0)) return false
      return true
    })
  }, [filters, rows])

  const stats = useMemo(() => ({
    synced: filtered.filter((row) => row.record).length,
    needsMarking: filtered.filter((row) => row.needsMarkingCount > 0).length,
    lowSubmission: filtered.filter((row) => row.record && row.expectedCount > 0 && (pct(row.submittedCount, row.expectedCount) ?? 0) < 70).length,
    gradingRate: pct(
      filtered.reduce((sum, row) => sum + (row.record ? row.markedCount : 0), 0),
      filtered.reduce((sum, row) => sum + (row.record ? row.gradableSubmittedCount : 0), 0)
    ),
  }), [filtered])

  if (classesLoading) return <div className="state-msg">Đang tải dữ liệu...</div>
  if (classesError) return (
    <div className="state-msg error">
      Không tải được dữ liệu lớp học.<br />
      Hãy chạy <code>python main.py</code> để lấy data trước.
    </div>
  )

  return (
    <div className="page">
      <div className="assignment-page-banner">
        <div>
          <h1 className="assignment-page-banner-title">Quản lý bài tập</h1>
          <p className="assignment-page-banner-sub">Theo dõi tình trạng nộp bài và chấm bài theo lớp</p>
        </div>
        <div className="assignment-stats-row">
          <div className="assignment-stat">
            <span className="assignment-stat-num">{stats.synced}</span>
            <span className="assignment-stat-label">Có dữ liệu</span>
          </div>
          <div className="assignment-stat">
            <span className="assignment-stat-num">{stats.needsMarking}</span>
            <span className="assignment-stat-label">Cần chấm</span>
          </div>
          <div className="assignment-stat">
            <span className="assignment-stat-num">{stats.lowSubmission}</span>
            <span className="assignment-stat-label">Nộp thấp</span>
          </div>
          <div className="assignment-stat assignment-stat-wide">
            <span className="assignment-stat-num">{fmtPct(stats.gradingRate)}</span>
            <span className="assignment-stat-label">Chấm / đang lọc</span>
          </div>
          <span className="assignment-page-badge">{filtered.length} / {rows.length} lớp</span>
          <RefreshButton module="assignments" />
        </div>
      </div>

      {assignmentsLoading && (
        <div className="assignment-sync-note">Đang kiểm tra dữ liệu bài tập...</div>
      )}
      {assignmentsError && !assignmentsLoading && (
        <div className="assignment-sync-note assignment-sync-note-warn">
          Chưa đọc được dữ liệu bài tập từ server. Hãy bấm tải dữ liệu để đồng bộ từ LMS.
        </div>
      )}

      <div className="filters-container">
        <div className="filter-group">
          <label className="filter-label">Tìm lớp</label>
          <input
            type="text"
            placeholder="Nhập tên lớp..."
            value={filters.search}
            onChange={(event) => update('search', event.target.value)}
          />
        </div>
        <SingleSelect
          label="Khu vực"
          options={AREA_OPTIONS}
          value={filters.area}
          onChange={updateArea}
        />
        <SingleSelect
          label="Cơ sở"
          options={centreOptions.map((centre) => ({ value: centre, label: centre }))}
          value={filters.centre}
          onChange={(value) => update('centre', value)}
        />
        <SingleSelect
          label="Khối"
          options={blocks.map((block) => ({ value: block, label: block }))}
          value={filters.block}
          onChange={(value) => update('block', value)}
        />
        <DatePickerInput
          label="Ngày diễn ra"
          value={{ from: filters.slot, to: filters.slotTo }}
          onChange={(from, to) => setFilters((current) => ({ ...current, slot: from, slotTo: to }))}
        />
        <MultiSelect
          label="Trạng thái lớp"
          options={classStatuses}
          selected={filters.classStatus}
          onChange={(value) => setFilters((current) => ({ ...current, classStatus: value }))}
          placeholder="Tất cả"
          renderOption={(status) => STATUS_MAP[status] ?? status}
        />
        <SingleSelect
          label="Giáo viên"
          options={mentors.map((mentor) => ({ value: mentor, label: mentor }))}
          value={filters.mentor}
          onChange={(value) => update('mentor', value)}
        />
        <SingleSelect
          label="Dữ liệu bài tập"
          options={[
            { value: 'synced', label: 'Có dữ liệu bài tập' },
            { value: 'missing', label: 'Chưa đồng bộ' },
            { value: 'mappingError', label: 'Lỗi mapping Denise' },
            { value: 'fetchError', label: 'Tải lỗi' },
            { value: 'outOfScope', label: 'Ngoài phạm vi' },
            { value: 'needsMarking', label: 'Cần chấm bài' },
            { value: 'lowSubmission', label: 'Tỉ lệ nộp thấp' },
          ]}
          value={filters.syncStatus}
          onChange={(value) => update('syncStatus', value)}
        />
        <SingleSelect
          label="Chấm bài"
          options={[
            { value: 'marked', label: 'Đã chấm' },
            { value: 'unmarked', label: 'Chưa chấm' },
          ]}
          value={filters.gradingStatus}
          onChange={(value) => update('gradingStatus', value)}
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
          <table className="cr-table assignment-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Tên lớp</th>
                <th>Cơ sở</th>
                <th>Khối</th>
                <th>Trạng thái lớp</th>
                <th>Giáo viên</th>
                <th>Bài học</th>
                <th>Đã nộp</th>
                <th>Cần chấm</th>
                <th>Điểm TB</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, index) => (
                <tr key={row.classId} onClick={() => setSelectedRow(row)} style={{ cursor: 'pointer' }}>
                  <td className="cr-td-num">{index + 1}</td>
                  <td className="cr-td-name">{row.className}</td>
                  <td>{row.centre || '—'}</td>
                  <td>{row.block || '—'}</td>
                  <td>
                    <span className={`status-badge ${STATUS_COLOR[row.classStatus] ?? ''}`}>
                      {(STATUS_MAP[row.classStatus] ?? row.classStatus) || '—'}
                    </span>
                  </td>
                  <td>{row.teachers[0]?.name || '—'}</td>
                  <td>{row.record ? `${row.lessonCount} bài` : '—'}</td>
                  <td className="assignment-td-progress">
                    <ProgressCell value={row.submittedCount} total={row.expectedCount} tone="blue" showCount />
                  </td>
                  <td className={row.needsMarkingCount > 0 ? 'assignment-td-alert' : ''}>
                    {row.record ? row.needsMarkingCount : '—'}
                  </td>
                  <td>{fmtScore(row.averageScore)}</td>
                  <td><StatusPill row={row} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedRow && (
        <AssignmentsModal row={selectedRow} onClose={() => setSelectedRow(null)} />
      )}
    </div>
  )
}

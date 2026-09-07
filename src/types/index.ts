export interface Teacher {
  name: string
  email?: string
  role?: string
}

export interface Slot {
  id: string
  date: string
  startTime: string
  endTime: string
  commentStatus: string
  studentsInSlot: number
  studentsWithComment: number
  students?: { id: string; name: string; status?: string }[]
}

export interface CompletionInfo {
  status: string | null
  reason?: string | null
  description?: string | null
  note?: string | null
}

export interface StudentCustomer {
  _id?: string | null
  fullName?: string | null
  phoneNumber?: string | null
  email?: string | null
  facebook?: string | null
  zalo?: string | null
}

export interface PreviousClass {
  id?: string | null
  name?: string | null
  startDate?: string | null
}

export interface CRStudent {
  id: string
  classId?: string
  studentId?: string
  learningMediumId?: string | null
  note?: string | null
  activeInClass?: boolean
  completed?: boolean
  completionInfo?: CompletionInfo | null
  retentionDate?: string | null
  grade?: string | number | null | { averageScore?: string | null }
  isTransfer?: boolean
  transfers?: { classFrom?: string | null; classTo?: string | null; dateFrom?: string | null; dateTo?: string | null }[]
  previousClass?: PreviousClass | null
  attended?: boolean
  student: {
    id: string
    fullName: string
    status?: string | null
    waitingStatus?: string | null
    phoneNumber?: string | null
    email?: string | null
    gender?: string | null
    dob?: string | null
    address?: string | null
    imageUrl?: string | null
    facebook?: string | null
    zalo?: string | null
    school?: string | null
    contactPhoneNumber?: string | null
    customer?: StudentCustomer | null
    studentId?: string | null
    isVip?: boolean
  }
}

export interface ClassItem {
  id: string
  name: string
  status: string
  course: string | null
  centre: string | null
  teachers: Teacher[]
  sessions: number | null
  createdAt: string
  startDate?: string
  endDate?: string
  level?: string
  block: string
  slots: Slot[]
  students?: CRStudent[]
  studentCount: number
  attendedCount: number
  completedCount: number
  completionRate: number
  commentPercentage: number
  totalSlotsWithStudents: number
  slotsWithFullComments: number
}

export interface Mentor {
  id: string
  name: string
  email?: string
  phone?: string
}

export interface TeacherItem {
  id: string
  fullName: string
  code: string
  username: string
  email: string | null
  personalEmail: string | null
  phoneNumber: string | null
  gender: string | null
  dob: string | null
  address: string | null
  isActive: boolean
  teacherPoint: number
  joinedDate: string | null
  courseLines: string[]
  blocks: string[]
  centres: string[]
}

export interface ClassFilters {
  area: string
  centre: string
  startDate: string
  startDateTo: string
  endDate: string
  endDateTo: string
  slot: string
  slotTo: string
  course: string
  search: string
  status: string[]    // multi-select
  hasComments: string
  mentor: string
  tpRound: string
  cpRound: string
  block: string[]     // multi-select
}

export interface TPStudentDetail {
  name: string
  score: number | null
  textAnswers: { questionId: string; value: string }[]
}

export interface TPRecord {
  classId: string
  className: string
  centre: string | null
  block: string
  teachers: Teacher[]
  tp1: number | null
  tp2: number | null
  tp1_students: TPStudentDetail[]
  tp2_students: TPStudentDetail[]
}

export interface CPStudentDetail {
  name: string
  theoryScore: number | null
  practicalScore: number | null
}

export interface CPRecord {
  classId: string
  className: string
  centre: string | null
  block: string
  teachers: Teacher[]
  cp1Theory: number | null
  cp1Practical: number | null
  cp2Theory: number | null
  cp2Practical: number | null
  cp1_students: CPStudentDetail[]
  cp2_students: CPStudentDetail[]
}

export interface AssignmentStudent {
  id: string
  displayName: string
  studentUid: string
}

export interface AssignmentLesson {
  id: string
  name: string
  type: string
  isActive: boolean
  learningCourseId?: string
  displayOrder: number
}

export interface AssignmentSubmission {
  id: string
  type: string
  note: string
  score: number
  status: 'IN_PROGRESS' | 'SUBMITTED' | 'MARKED' | string
  category: string
  classId: string
  lessonId: string
  learningCourseId: string
  studentUid: string
  studentOriginalId?: string
  classSessionId?: string
  markedAt: string
  markedBy: string
  createdAt: string
  submittedAt: string
  submittedCount: number
  content?: {
    type: string
    attachments: string[]
    totalQuiz: number
    submitQuiz: number
    correctAnswer: number
  }
}

export interface AssignmentClassRecord {
  classId: string
  className: string
  centre: string | null
  block: string
  status?: string
  studentCount?: number
  lessonCount?: number
  expectedCount?: number
  submittedCount?: number
  gradableSubmittedCount?: number
  markedCount?: number
  inProgressCount?: number
  needsMarkingCount?: number
  averageScore?: number | null
  teachers: Teacher[]
  students: AssignmentStudent[]
  lessons: AssignmentLesson[]
  submissions: AssignmentSubmission[]
}

export interface AssignmentFetchError {
  classId: string
  className: string
  centre: string | null
  block: string
  status: string
  errorType: 'mapping' | 'http' | 'network' | 'lms_error' | string
  message: string
  fetchedAt: string
}

export interface AssignmentPayload {
  records: AssignmentClassRecord[]
  errors: AssignmentFetchError[]
}

// ── Office Hours ──────────────────────────────────────────────────────────

export interface OHAppointment {
  id: string
  title: string
  candidate: { id: string; fullName: string } | null
  courses: { id: string; name: string; shortName: string }[]
  status: 'WAITING' | 'CANCLED' | 'FAIL' | 'PASSED' | string
  note: string | null
}

export interface OHRecord {
  id: string
  courses: { id: string; name: string; shortName: string }[]
  courseLines: { id: string; name: string }[]
  startTime: string   // ISO string
  endTime: string     // ISO string
  status: string      // OH-level status (APPROVED, etc.)
  centre: { id: string; name: string; shortName: string } | null
  teacher: { id: string; fullName: string; username: string; email: string } | null
  note: string | null         // note của tư vấn book
  managerNote: string | null
  type: string
  studentCount: number
  createdBy: { username: string } | null
  appointments: OHAppointment[]
}

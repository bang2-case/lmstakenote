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

export interface ClassFilters {
  centre: string
  startDate: string
  startDateTo: string
  endDate: string
  endDateTo: string
  slot: string
  slotTo: string
  course: string
  status: string
  hasComments: string
  mentor: string
  block: string
}

import { useMemo, useState } from 'react'

type TfEntry = {
  id: string
  dayIndex: number
  slotId: string
  className: string
  startTime: string
  endTime: string
  session: string
  studentCount: number
}

type TfTab = {
  id: string
  name: string
  entries: TfEntry[]
}

type TfForm = {
  className: string
  slotId: string
  startTime: string
  endTime: string
  session: string
  studentCount: string
}

type ModalState = {
  tabId: string
  dayIndex: number
  slotId: string
  entryId?: string
} | null

const STORAGE_KEY = 'lms-takenote-tf-schedule-v1'

const DAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']

const SLOT_GROUPS = [
  {
    id: 'morning',
    label: 'Sáng',
    slots: [
      { id: 'morning-8-10', label: '8h - 10h', start: '08:00', end: '10:00' },
      { id: 'morning-10-12', label: '10h - 12h', start: '10:00', end: '12:00' },
    ],
  },
  {
    id: 'noon',
    label: 'Trưa',
    slots: [
      { id: 'noon-14-16', label: '14h - 16h', start: '14:00', end: '16:00' },
    ],
  },
  {
    id: 'afternoon',
    label: 'Chiều',
    slots: [
      { id: 'afternoon-16-18', label: '16h - 18h', start: '16:00', end: '18:00' },
    ],
  },
  {
    id: 'evening',
    label: 'Tối',
    slots: [
      { id: 'evening-18-20', label: '18h - 20h', start: '18:00', end: '20:00' },
    ],
  },
]

const ALL_SLOTS = SLOT_GROUPS.flatMap((group) => group.slots)

function createId(prefix: string) {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function defaultTabs(): TfTab[] {
  return [
    { id: createId('tf-tab'), name: 'Nhân viên 1', entries: [] },
    { id: createId('tf-tab'), name: 'Nhân viên 2', entries: [] },
  ]
}

function loadTabs(): TfTab[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultTabs()
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length === 0) return defaultTabs()
    return parsed.map((tab: Partial<TfTab>, index: number) => {
      const savedName = typeof tab.name === 'string' ? tab.name.trim() : ''
      const migratedName = savedName === `Tab ${index + 1}` ? `Nhân viên ${index + 1}` : savedName
      return {
        id: typeof tab.id === 'string' ? tab.id : createId('tf-tab'),
        name: migratedName || `Nhân viên ${index + 1}`,
        entries: Array.isArray(tab.entries) ? tab.entries : [],
      }
    })
  } catch {
    return defaultTabs()
  }
}

function persistTabs(nextTabs: TfTab[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(nextTabs))
}

function getMonday(date: Date) {
  const d = new Date(date)
  d.setHours(0, 0, 0, 0)
  const dayFromMonday = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - dayFromMonday)
  return d
}

function addDays(date: Date, amount: number) {
  const d = new Date(date)
  d.setDate(d.getDate() + amount)
  return d
}

function formatDate(date: Date) {
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })
}

function formatFullDate(date: Date) {
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatTimeRange(entry: Pick<TfEntry, 'startTime' | 'endTime'>) {
  const normalize = (value: string) => value.replace(':', 'h')
  return `${normalize(entry.startTime)} - ${normalize(entry.endTime)}`
}

function makeEmptyForm(slotId: string): TfForm {
  const slot = ALL_SLOTS.find((item) => item.id === slotId) ?? ALL_SLOTS[0]
  return {
    className: '',
    slotId: slot.id,
    startTime: slot.start,
    endTime: slot.end,
    session: '',
    studentCount: '',
  }
}

function formFromEntry(entry: TfEntry): TfForm {
  return {
    className: entry.className,
    slotId: entry.slotId,
    startTime: entry.startTime,
    endTime: entry.endTime,
    session: entry.session,
    studentCount: String(entry.studentCount || ''),
  }
}

export default function TFSchedulePage() {
  const [tabs, setTabs] = useState<TfTab[]>(loadTabs)
  const [activeTabId, setActiveTabId] = useState(() => tabs[0]?.id ?? '')
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()))
  const [modal, setModal] = useState<ModalState>(null)
  const [form, setForm] = useState<TfForm>(() => makeEmptyForm(ALL_SLOTS[0].id))
  const [tabManagerOpen, setTabManagerOpen] = useState(false)
  const [newEmployeeName, setNewEmployeeName] = useState('')

  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0]
  const weekDays = useMemo(
    () => DAYS.map((label, index) => ({ label, date: addDays(weekStart, index) })),
    [weekStart]
  )

  const updateTabs = (updater: (current: TfTab[]) => TfTab[]) => {
    setTabs((current) => {
      const next = updater(current)
      persistTabs(next)
      return next
    })
  }

  const updateTabName = (tabId: string, name: string) => {
    updateTabs((current) =>
      current.map((tab) => (tab.id === tabId ? { ...tab, name } : tab))
    )
  }

  const commitTabName = (tabId: string, index: number) => {
    updateTabs((current) =>
      current.map((tab) =>
        tab.id === tabId
          ? { ...tab, name: tab.name.trim() || `Nhân viên ${index + 1}` }
          : tab
      )
    )
  }

  const addTab = (name?: string) => {
    const cleanedName = name?.trim()
    const nextTab = { id: createId('tf-tab'), name: cleanedName || `Nhân viên ${tabs.length + 1}`, entries: [] }
    updateTabs((current) => [...current, nextTab])
    setActiveTabId(nextTab.id)
    setNewEmployeeName('')
  }

  const deleteTab = (tabId: string) => {
    updateTabs((current) => {
      if (current.length <= 1) return current
      const next = current.filter((tab) => tab.id !== tabId)
      if (activeTabId === tabId) {
        setActiveTabId(next[0]?.id ?? '')
      }
      return next
    })
  }

  const openModal = (dayIndex: number, slotId: string, entry?: TfEntry) => {
    if (!activeTab) return
    setModal({ tabId: activeTab.id, dayIndex, slotId, entryId: entry?.id })
    setForm(entry ? formFromEntry(entry) : makeEmptyForm(slotId))
  }

  const closeModal = () => {
    setModal(null)
    setForm(makeEmptyForm(ALL_SLOTS[0].id))
  }

  const saveEntry = () => {
    if (!modal || !form.className.trim()) return
    const entry: TfEntry = {
      id: modal.entryId ?? createId('tf-entry'),
      dayIndex: modal.dayIndex,
      slotId: form.slotId,
      className: form.className.trim(),
      startTime: form.startTime,
      endTime: form.endTime,
      session: form.session.trim(),
      studentCount: Number(form.studentCount) || 0,
    }

    updateTabs((current) =>
      current.map((tab) => {
        if (tab.id !== modal.tabId) return tab
        const entries = modal.entryId
          ? tab.entries.map((item) => (item.id === modal.entryId ? entry : item))
          : [...tab.entries, entry]
        return { ...tab, entries }
      })
    )
    closeModal()
  }

  const deleteEntry = () => {
    if (!modal?.entryId) return
    updateTabs((current) =>
      current.map((tab) =>
        tab.id === modal.tabId
          ? { ...tab, entries: tab.entries.filter((entry) => entry.id !== modal.entryId) }
          : tab
      )
    )
    closeModal()
  }

  const entriesForCell = (dayIndex: number, slotId: string) =>
    (activeTab?.entries ?? []).filter((entry) => entry.dayIndex === dayIndex && entry.slotId === slotId)

  return (
    <div className="page tf-page">
      <div className="page-banner tf-page-banner">
        <div>
          <h1 className="page-banner-title">Lịch làm TF</h1>
          <p className="page-banner-sub">
            Tuần {formatFullDate(weekDays[0].date)} - {formatFullDate(weekDays[6].date)}
          </p>
        </div>
        <div className="tf-week-controls" aria-label="Điều hướng tuần">
          <button type="button" className="tf-icon-button" onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Tuần trước">
            ‹
          </button>
          <button type="button" className="tf-today-button" onClick={() => setWeekStart(getMonday(new Date()))}>
            Hôm nay
          </button>
          <button type="button" className="tf-icon-button" onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Tuần sau">
            ›
          </button>
        </div>
      </div>

      <div className="tf-tab-row">
        <div className="tf-tabs" role="tablist" aria-label="Lịch TF theo nhân viên">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`tf-tab ${activeTab?.id === tab.id ? 'tf-tab-active' : ''}`}
              onClick={() => setActiveTabId(tab.id)}
              role="tab"
              aria-selected={activeTab?.id === tab.id}
            >
              <span>{tab.name || 'Chưa đặt tên'}</span>
            </button>
          ))}
        </div>
        <button type="button" className="tf-add-tab" onClick={() => setTabManagerOpen(true)} aria-label="Quản lý lịch nhân viên">
          +
        </button>
      </div>

      <div className="tf-schedule-shell">
        <div className="tf-schedule-grid">
          <div className="tf-corner-cell">Khung giờ</div>
          {weekDays.map((day) => (
            <div key={`${day.label}-${day.date.toISOString()}`} className="tf-day-head">
              <span>{day.label}</span>
              <strong>{formatDate(day.date)}</strong>
            </div>
          ))}

          {SLOT_GROUPS.map((group) =>
            group.slots.map((slot) => (
              <div key={slot.id} className="tf-slot-row">
                <div className="tf-slot-label">
                  <span className={`tf-slot-period tf-period-${group.id}`}>{group.label}</span>
                  <strong>{slot.label}</strong>
                </div>
                {weekDays.map((day, dayIndex) => {
                  const entries = entriesForCell(dayIndex, slot.id)
                  return (
                    <div
                      key={`${slot.id}-${day.label}`}
                      className="tf-schedule-cell"
                      role="button"
                      tabIndex={0}
                      onClick={() => openModal(dayIndex, slot.id)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          openModal(dayIndex, slot.id)
                        }
                      }}
                    >
                      {entries.map((entry) => (
                        <span
                          key={entry.id}
                          role="button"
                          tabIndex={0}
                          className="tf-class-card"
                          onClick={(event) => {
                            event.stopPropagation()
                            openModal(dayIndex, slot.id, entry)
                          }}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter' || event.key === ' ') {
                              event.preventDefault()
                              event.stopPropagation()
                              openModal(dayIndex, slot.id, entry)
                            }
                          }}
                        >
                          <span className="tf-class-card-top">
                            <strong>{entry.className}</strong>
                            <small>{formatTimeRange(entry)}</small>
                          </span>
                          <span className="tf-class-card-teacher">{activeTab?.name}</span>
                          <span className="tf-class-card-meta">
                            {entry.session && <small>{entry.session}</small>}
                            <small>{entry.studentCount} HV</small>
                          </span>
                        </span>
                      ))}
                    </div>
                  )
                })}
              </div>
            ))
          )}
        </div>
      </div>

      {modal && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content tf-modal" onClick={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" onClick={closeModal} aria-label="Đóng">
              ×
            </button>
            <div className="modal-banner">
              <div>
                <h2 className="modal-banner-title">{modal.entryId ? 'Sửa lớp' : 'Thêm lớp'}</h2>
                <p className="modal-banner-sub">
                  {weekDays[modal.dayIndex].label}, {formatFullDate(weekDays[modal.dayIndex].date)}
                </p>
              </div>
            </div>
            <div className="modal-body tf-modal-body">
              <label className="tf-field">
                <span>Tên giáo viên</span>
                <input value={tabs.find((tab) => tab.id === modal.tabId)?.name ?? ''} readOnly />
              </label>
              <label className="tf-field">
                <span>Tên lớp</span>
                <input
                  value={form.className}
                  onChange={(event) => setForm((current) => ({ ...current, className: event.target.value }))}
                  autoFocus
                />
              </label>
              <div className="tf-time-pair">
                <label className="tf-field">
                  <span>Bắt đầu</span>
                  <input
                    type="time"
                    value={form.startTime}
                    onChange={(event) => setForm((current) => ({ ...current, startTime: event.target.value }))}
                  />
                </label>
                <label className="tf-field">
                  <span>Kết thúc</span>
                  <input
                    type="time"
                    value={form.endTime}
                    onChange={(event) => setForm((current) => ({ ...current, endTime: event.target.value }))}
                  />
                </label>
              </div>
              <div className="tf-time-pair">
                <label className="tf-field">
                  <span>Buổi</span>
                  <input
                    value={form.session}
                    onChange={(event) => setForm((current) => ({ ...current, session: event.target.value }))}
                    placeholder="Ví dụ: Buổi 4"
                  />
                </label>
                <label className="tf-field">
                  <span>Số lượng học viên</span>
                  <input
                    type="number"
                    min="0"
                    value={form.studentCount}
                    onChange={(event) => setForm((current) => ({ ...current, studentCount: event.target.value }))}
                  />
                </label>
              </div>
              <div className="tf-modal-actions">
                {modal.entryId && (
                  <button type="button" className="tf-danger-button" onClick={deleteEntry}>
                    Xóa
                  </button>
                )}
                <button type="button" className="btn-reset" onClick={closeModal}>
                  Hủy
                </button>
                <button type="button" className="btn-summary" onClick={saveEntry} disabled={!form.className.trim()}>
                  Lưu
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {tabManagerOpen && (
        <div className="modal-overlay" onClick={() => setTabManagerOpen(false)}>
          <div className="modal-content tf-modal" onClick={(event) => event.stopPropagation()}>
            <button className="modal-close" type="button" onClick={() => setTabManagerOpen(false)} aria-label="Đóng">
              ×
            </button>
            <div className="modal-banner">
              <div>
                <h2 className="modal-banner-title">Quản lý lịch nhân viên</h2>
                <p className="modal-banner-sub">Thêm, đổi tên hoặc xóa tab lịch TF</p>
              </div>
            </div>
            <div className="modal-body tf-modal-body">
              <div className="tf-manager-list">
                {tabs.map((tab, index) => (
                  <div key={tab.id} className="tf-manager-row">
                    <label className="tf-field">
                      <span>Nhân viên {index + 1}</span>
                      <input
                        value={tab.name}
                        onChange={(event) => updateTabName(tab.id, event.target.value)}
                        onBlur={() => commitTabName(tab.id, index)}
                      />
                    </label>
                    <button
                      type="button"
                      className="tf-danger-button"
                      onClick={() => deleteTab(tab.id)}
                      disabled={tabs.length <= 1}
                    >
                      Xóa
                    </button>
                  </div>
                ))}
              </div>
              <div className="tf-add-employee-row">
                <label className="tf-field">
                  <span>Thêm nhân viên</span>
                  <input
                    value={newEmployeeName}
                    onChange={(event) => setNewEmployeeName(event.target.value)}
                    placeholder={`Nhân viên ${tabs.length + 1}`}
                  />
                </label>
                <button type="button" className="btn-summary" onClick={() => addTab(newEmployeeName)}>
                  Thêm
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

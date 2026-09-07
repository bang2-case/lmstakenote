import { useState } from 'react'
import SidebarStatus from './SidebarStatus'

// Pages
export type Page = 'classes' | 'mentors' | 'cr' | 'tp' | 'cp' | 'assignments' | 'oh' | 'demo'

interface SidebarProps {
  activePage: Page
  onNavigate: (page: Page) => void
  isOpen?: boolean
  onClose?: () => void
}

// ── SVG Icons ──────────────────────────────────────────────────────────────
function IconChalkboardUser() {
  return (
    <svg width="18" height="18" viewBox="0 0 640 512" fill="currentColor" aria-hidden="true">
      <path d="M64 64C46.3 64 32 78.3 32 96V384c0 17.7 14.3 32 32 32H256V384H96V128H544V256h64V96c0-17.7-14.3-32-32-32H64zM384 320a80 80 0 1 0 0-160 80 80 0 1 0 0 160zm-96 64c0-35.3 28.7-64 64-64h64c35.3 0 64 28.7 64 64v64H288V384zM0 480c0-35.3 28.7-64 64-64h64v64H0zm576 0v-64h64c35.3 0 64 28.7 64 64H576z"/>
    </svg>
  )
}

function IconIdCard() {
  return (
    <svg width="18" height="18" viewBox="0 0 576 512" fill="currentColor" aria-hidden="true">
      <path d="M528 32H48C21.5 32 0 53.5 0 80v352c0 26.5 21.5 48 48 48h480c26.5 0 48-21.5 48-48V80c0-26.5-21.5-48-48-48zM208 256c-35.3 0-64-28.7-64-64s28.7-64 64-64 64 28.7 64 64-28.7 64-64 64zm-96 128c0-35.3 28.7-64 64-64h64c35.3 0 64 28.7 64 64v16H112v-16zm272-96h96c8.8 0 16 7.2 16 16s-7.2 16-16 16h-96c-8.8 0-16-7.2-16-16s7.2-16 16-16zm0-64h96c8.8 0 16 7.2 16 16s-7.2 16-16 16h-96c-8.8 0-16-7.2-16-16s7.2-16 16-16zm0 128h96c8.8 0 16 7.2 16 16s-7.2 16-16 16h-96c-8.8 0-16-7.2-16-16s7.2-16 16-16z"/>
    </svg>
  )
}

function IconStarHalfStroke() {
  return (
    <svg width="18" height="18" viewBox="0 0 576 512" fill="currentColor" aria-hidden="true">
      <path d="M288 376.4l.1-.1 26.4 14.1 85.2 45.5-16.5-97.6-4.8-28.7 20.7-20.5 70.1-69.3-96.1-14.2-28.6-4.2-12.9-26.6L288 86.5V376.4zm175.1 98.3c2 12-3 24.2-12.9 31.3s-23 8-33.8 2.3L288 439.8 159.6 508.3C148.8 514 135.9 513.1 126 506s-14.9-19.3-12.9-31.3L137.8 329 33.6 225.9c-8.6-8.5-11.7-21.2-7.9-32.8s13.7-19.9 25.7-21.7L195 150.3 259.4 18c5.4-11 16.5-18 28.6-18s23.2 7 28.6 18L381 150.3l153.6 21.1c12 1.8 22 10.2 25.7 21.7s.7 24.3-7.9 32.8L448.2 329l24.9 145.7z"/>
    </svg>
  )
}

function IconFilePen() {
  return (
    <svg width="18" height="18" viewBox="0 0 576 512" fill="currentColor" aria-hidden="true">
      <path d="M0 64C0 28.7 28.7 0 64 0H224V128c0 17.7 14.3 32 32 32H384v38.6C310.1 219.5 256 287.4 256 368c0 59.1 29.1 111.3 73.7 143.3c-3.2 .5-6.4 .7-9.7 .7H64c-35.3 0-64-28.7-64-64V64zm384 64H256V0L384 128zM288 368a144 144 0 1 1 288 0 144 144 0 1 1 -288 0zm211.3-43.3c-6.2-6.2-16.4-6.2-22.6 0L416 385.4l-28.7-28.7c-6.2-6.2-16.4-6.2-22.6 0s-6.2 16.4 0 22.6l40 40c6.2 6.2 16.4 6.2 22.6 0l72-72c6.2-6.2 6.2-16.4 0-22.6z"/>
    </svg>
  )
}

function IconProgressCheck() {
  return (
    <svg width="18" height="18" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true">
      <path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zM369 209L241 337c-9.4 9.4-24.6 9.4-33.9 0l-64-64c-9.4-9.4-9.4-24.6 0-33.9s24.6-9.4 33.9 0l47 47L335 175c9.4-9.4 24.6-9.4 33.9 0s9.4 24.6 0 33.9z"/>
    </svg>
  )
}

function IconClipboardList() {
  return (
    <svg width="18" height="18" viewBox="0 0 384 512" fill="currentColor" aria-hidden="true">
      <path d="M192 0c-41.8 0-77.4 26.7-90.5 64H64C28.7 64 0 92.7 0 128v320c0 35.3 28.7 64 64 64h256c35.3 0 64-28.7 64-64V128c0-35.3-28.7-64-64-64h-37.5C269.4 26.7 233.8 0 192 0zm0 64a32 32 0 1 1 0 64 32 32 0 1 1 0-64zM112 256h160c8.8 0 16 7.2 16 16s-7.2 16-16 16H112c-8.8 0-16-7.2-16-16s7.2-16 16-16zm0 96h160c8.8 0 16 7.2 16 16s-7.2 16-16 16H112c-8.8 0-16-7.2-16-16s7.2-16 16-16z"/>
    </svg>
  )
}

function IconSeedling() {
  return (
    <svg width="18" height="18" viewBox="0 0 512 512" fill="currentColor" aria-hidden="true">
      <path d="M512 32c0 113.6-84.6 207.5-194.2 222c-7.1-53.4-30.6-101.6-65.3-139.3C290.8 46.3 364 0 448 0h64zm-255.9 0c0 .1 0 .1 0 0zM288 96c0 88.4-71.6 160-160 160H112C50.1 256 0 206 0 144v-16C0 70.1 50.1 20 112 20h16c88.4 0 160 71.6 160 160zm-160 0c0-17.7-14.3-32-32-32s-32 14.3-32 32 14.3 32 32 32 32-14.3 32-32zM224 416c0 53-43 96-96 96s-96-43-96-96 43-96 96-96 96 43 96 96zm-96-32c-17.7 0-32 14.3-32 32s14.3 32 32 32 32-14.3 32-32-14.3-32-32-32z"/>
    </svg>
  )
}

function IconDemo() {
  return (
    <svg width="18" height="18" viewBox="0 0 576 512" fill="currentColor" aria-hidden="true">
      <path d="M0 80C0 53.5 21.5 32 48 32h96c26.5 0 48 21.5 48 48V96H384V80c0-26.5 21.5-48 48-48h96c26.5 0 48 21.5 48 48v96c0 26.5-21.5 48-48 48H432c-26.5 0-48-21.5-48-48v-16H192v16c0 26.5-21.5 48-48 48H48C21.5 224 0 202.5 0 176V80zM192 352v-16H48c-26.5 0-48-21.5-48-48V192h64v80h128v-16c0-26.5 21.5-48 48-48h96c26.5 0 48 21.5 48 48v16h128V192h64v96c0 26.5-21.5 48-48 48H384v16c0 26.5-21.5 48-48 48H240c-26.5 0-48-21.5-48-48z"/>
    </svg>
  )
}

function IconChevron({ open }: { open: boolean }) {
  return (
    <svg
      width="12" height="12" viewBox="0 0 320 512" fill="currentColor" aria-hidden="true"
      style={{ transition: 'transform 0.2s', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', flexShrink: 0 }}
    >
      <path d="M278.6 233.4c12.5 12.5 12.5 32.8 0 45.3l-160 160c-12.5 12.5-32.8 12.5-45.3 0s-12.5-32.8 0-45.3L210.7 256 73.4 118.6c-12.5-12.5-12.5-32.8 0-45.3s32.8-12.5 45.3 0l160 160z"/>
    </svg>
  )
}

// ── Nav structure ──────────────────────────────────────────────────────────
type NavItem =
  | { type: 'item'; key: Page; label: string; icon: React.ReactNode }
  | { type: 'group'; label: string; children: { key: Page; label: string; icon: React.ReactNode }[] }

const navStructure: NavItem[] = [
  {
    type: 'item',
    key: 'classes',
    label: 'Quản lý lớp học',
    icon: <IconChalkboardUser />,
  },
  {
    type: 'item',
    key: 'mentors',
    label: 'Quản lý giáo viên',
    icon: <IconIdCard />,
  },
  {
    type: 'group',
    label: 'Quản lý chất lượng',
    children: [
      { key: 'tp',  label: 'Quản lý TP',  icon: <IconStarHalfStroke /> },
      { key: 'cp',  label: 'Quản lý CP',  icon: <IconFilePen /> },
      { key: 'assignments', label: 'Quản lý bài tập', icon: <IconClipboardList /> },
      { key: 'cr',  label: 'Quản lý CPR', icon: <IconProgressCheck /> },
    ],
  },
  {
    type: 'item',
    key: 'oh',
    label: 'Quản lý OH',
    icon: <IconSeedling />,
  },
  {
    type: 'item',
    key: 'demo',
    label: 'Quản lý DEMO',
    icon: <IconDemo />,
  },
]

export default function Sidebar({ activePage, onNavigate, isOpen, onClose }: SidebarProps) {
  const isGroupActive = (children: { key: Page }[]) =>
    children.some((c) => c.key === activePage)

  // Groups start open if a child is active, otherwise closed
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    navStructure.forEach((item) => {
      if (item.type === 'group') {
        init[item.label] = item.children.some((c) => c.key === activePage)
      }
    })
    return init
  })

  const toggleGroup = (label: string) =>
    setOpenGroups((prev) => ({ ...prev, [label]: !prev[label] }))

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
      <button className="sidebar-close" onClick={onClose} aria-label="Đóng menu">✕</button>
      <div className="sidebar-logo">
        <img src="/image/logo_white.svg" alt="Logo" className="logo-image" />
      </div>
      <nav className="sidebar-nav">
        {navStructure.map((item) => {
          if (item.type === 'item') {
            return (
              <button
                key={item.key}
                className={`nav-item ${activePage === item.key ? 'active' : ''}`}
                onClick={() => onNavigate(item.key)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            )
          }

          // Collapsible group
          const isOpen = openGroups[item.label] ?? false
          const hasActive = isGroupActive(item.children)
          return (
            <div key={item.label} className={`nav-group ${hasActive ? 'nav-group-active' : ''}`}>
              <button
                className={`nav-group-toggle ${hasActive ? 'nav-group-toggle-active' : ''}`}
                onClick={() => toggleGroup(item.label)}
                aria-expanded={isOpen}
              >
                <span className="nav-group-toggle-label">{item.label}</span>
                <IconChevron open={isOpen} />
              </button>
              <div className={`nav-group-children ${isOpen ? 'nav-group-children-open' : ''}`}>
                <div>
                  {item.children.map((child) => (
                    <button
                      key={child.key}
                      className={`nav-item nav-item-child ${activePage === child.key ? 'active' : ''}`}
                      onClick={() => onNavigate(child.key)}
                    >
                      <span className="nav-icon">{child.icon}</span>
                      <span className="nav-label">{child.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </nav>
      <div className="sidebar-bottom">
        <SidebarStatus />
      </div>
    </aside>
  )
}

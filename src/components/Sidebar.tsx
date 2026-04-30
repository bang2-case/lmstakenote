type Page = 'classes' | 'mentors' | 'cr' | 'tp'

interface SidebarProps {
  activePage: Page
  onNavigate: (page: Page) => void
  isOpen?: boolean
  onClose?: () => void
}

const navItems: { key: Page; label: string; icon: string }[] = [
  { key: 'classes', label: 'Quản lý lớp học', icon: '🚩' },
  { key: 'tp',      label: 'Quản lý TP',       icon: '⭐' },
  { key: 'mentors', label: 'Quản lý giáo viên', icon: '🎓' },
  { key: 'cr',      label: 'Quản lý CR',        icon: '📊' },
]

export default function Sidebar({ activePage, onNavigate, isOpen, onClose }: SidebarProps) {
  return (
    <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
      <button className="sidebar-close" onClick={onClose} aria-label="Đóng menu">✕</button>
      <div className="sidebar-logo">
        <img src="/image/logo_white.svg" alt="Logo" className="logo-image" />
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.key}
            className={`nav-item ${activePage === item.key ? 'active' : ''}`}
            onClick={() => onNavigate(item.key)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  )
}

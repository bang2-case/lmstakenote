type Page = 'classes' | 'mentors'

interface SidebarProps {
  activePage: Page
  onNavigate: (page: Page) => void
}

const navItems: { key: Page; label: string; icon: string }[] = [
  { key: 'classes', label: 'Quản lý lớp học', icon: '🚩' },
  { key: 'mentors', label: 'Quản lý giáo viên', icon: '🎓' },
]

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="sidebar">
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

import { useState } from 'react'
import Sidebar, { type Page } from './components/Sidebar'
import ClassesPage from './pages/ClassesPage'
import MentorsPage from './pages/MentorsPage'
import CRPage from './pages/CRPage'
import TPPage from './pages/TPPage'
import CPPage from './pages/CPPage'
import OHPage from './pages/OHPage'
import './App.css'

export default function App() {
  const [activePage, setActivePage] = useState<Page>('classes')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleNavigate = (page: Page) => {
    setActivePage(page)
    setSidebarOpen(false)
  }

  return (
    <div className="app-layout">
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}
      <header className="mobile-topbar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)} aria-label="Mở menu">
          <span /><span /><span />
        </button>
        <span className="mobile-title">LMS TakeNote</span>
      </header>
      <Sidebar
        activePage={activePage}
        onNavigate={handleNavigate}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <main className="main-content">
        {activePage === 'classes' && <ClassesPage />}
        {activePage === 'mentors' && <MentorsPage />}
        {activePage === 'cr'      && <CRPage />}
        {activePage === 'tp'      && <TPPage />}
        {activePage === 'cp'      && <CPPage />}
        {activePage === 'oh'      && <OHPage />}
      </main>
    </div>
  )
}

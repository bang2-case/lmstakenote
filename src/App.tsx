import { useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import Sidebar, { type Page } from './components/Sidebar'
import ClassesPage from './pages/ClassesPage'
import MentorsPage from './pages/MentorsPage'
import CRPage from './pages/CRPage'
import TPPage from './pages/TPPage'
import CPPage from './pages/CPPage'
import OHPage from './pages/OHPage'
import DEMOPage from './pages/DEMOPage'
import './App.css'

const pageRoutes: Record<Page, string> = {
  classes: '/classes',
  mentors: '/mentors',
  cr: '/cr',
  tp: '/tp',
  cp: '/cp',
  oh: '/oh',
  demo: '/demo',
}

const routePages = Object.fromEntries(
  Object.entries(pageRoutes).map(([page, path]) => [path, page])
) as Record<string, Page>

export default function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const activePage = routePages[location.pathname] ?? 'classes'
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const handleNavigate = (page: Page) => {
    navigate(pageRoutes[page])
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
        <Routes>
          <Route path="/" element={<Navigate to="/classes" replace />} />
          <Route path="/classes" element={<ClassesPage />} />
          <Route path="/mentors" element={<MentorsPage />} />
          <Route path="/cr" element={<CRPage />} />
          <Route path="/tp" element={<TPPage />} />
          <Route path="/cp" element={<CPPage />} />
          <Route path="/oh" element={<OHPage />} />
          <Route path="/demo" element={<DEMOPage />} />
          <Route path="*" element={<Navigate to="/classes" replace />} />
        </Routes>
      </main>
    </div>
  )
}

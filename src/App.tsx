import { useState } from 'react'
import Sidebar from './components/Sidebar'
import ClassesPage from './pages/ClassesPage'
import MentorsPage from './pages/MentorsPage'
import './App.css'

type Page = 'classes' | 'mentors'

export default function App() {
  const [activePage, setActivePage] = useState<Page>('classes')

  return (
    <div className="app-layout">
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <main className="main-content">
        {activePage === 'classes' && <ClassesPage />}
        {activePage === 'mentors' && <MentorsPage />}
      </main>
    </div>
  )
}

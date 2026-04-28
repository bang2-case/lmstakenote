import type { Mentor } from '../types'

// Mock data - sẽ được thay bằng API sau
const MOCK_MENTORS: Mentor[] = [
  { id: '1', name: 'Nguyễn Văn A', email: 'a@mindx.com.vn', phone: '0901234567' },
  { id: '2', name: 'Trần Thị B', email: 'b@mindx.com.vn', phone: '0912345678' },
  { id: '3', name: 'Lê Văn C', email: 'c@mindx.com.vn', phone: '0923456789' },
]

function MentorCard({ mentor }: { mentor: Mentor }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="mentor-avatar">{mentor.name.charAt(0)}</div>
        <h3 className="card-title">{mentor.name}</h3>
      </div>
      {mentor.email && <p className="card-meta">✉️ {mentor.email}</p>}
      {mentor.phone && <p className="card-meta">📞 {mentor.phone}</p>}
    </div>
  )
}

export default function MentorsPage() {
  return (
    <div className="page">
      <div className="page-header">
        <h1>Danh sách Mentor</h1>
        <span className="count-badge">{MOCK_MENTORS.length} mentor</span>
      </div>
      <div className="card-grid">
        {MOCK_MENTORS.map((m) => (
          <MentorCard key={m.id} mentor={m} />
        ))}
      </div>
    </div>
  )
}

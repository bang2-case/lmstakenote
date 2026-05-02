import { useState } from 'react'
import { useServerStatus } from '../hooks/useServerStatus'

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

export default function SidebarStatus() {
  const { connected, fetchState, tokenInfo, triggerRefresh } = useServerStatus()
  const [showLog, setShowLog] = useState(false)
  const [log, setLog] = useState('')

  const tokenExpired  = tokenInfo && !tokenInfo.valid
  const tokenExpiring = tokenInfo && tokenInfo.valid && tokenInfo.remaining_minutes <= 15

  const handleShowLog = async () => {
    try {
      const r = await fetch('/api/fetch-log')
      const d = await r.json()
      setLog(d.log || 'Không có log')
      setShowLog(true)
    } catch {
      setLog('Không thể lấy log')
      setShowLog(true)
    }
  }

  return (
    <div className="sidebar-status">
      {/* Token warning */}
      {tokenExpired && (
        <div className="sidebar-status-alert sidebar-status-alert-error">
          ⚠ Token hết hạn
        </div>
      )}
      {tokenExpiring && !tokenExpired && (
        <div className="sidebar-status-alert sidebar-status-alert-warn">
          ⏱ Token còn {tokenInfo!.remaining_minutes} phút
        </div>
      )}

      {/* Status row */}
      <div className="sidebar-status-row">
        <span className={`sidebar-status-dot ${connected ? 'dot-on' : 'dot-off'}`} />
        <span className="sidebar-status-text">
          {fetchState.is_fetching
            ? 'Đang cập nhật...'
            : fetchState.last_fetch
            ? `Cập nhật ${formatTime(fetchState.last_fetch)}`
            : fetchState.last_status === 'error'
            ? (
              <span
                style={{ cursor: 'pointer', textDecoration: 'underline' }}
                onClick={handleShowLog}
                title="Bấm để xem chi tiết lỗi"
              >
                Lỗi fetch ⓘ
              </span>
            )
            : 'Chưa cập nhật'}
        </span>
      </div>

      {/* Refresh button */}
      <button
        className="sidebar-status-btn"
        onClick={triggerRefresh}
        disabled={fetchState.is_fetching || !connected}
        title="Cập nhật dữ liệu ngay"
      >
        {fetchState.is_fetching ? '⏳ Đang tải...' : '↻ Cập nhật'}
      </button>

      {/* Log modal */}
      {showLog && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 20
          }}
          onClick={() => setShowLog(false)}
        >
          <div
            style={{
              background: '#1f2937', color: '#e5e7eb', borderRadius: 10,
              padding: 20, maxWidth: 700, width: '100%', maxHeight: '80vh',
              overflow: 'auto', fontFamily: 'monospace', fontSize: 12,
              whiteSpace: 'pre-wrap', wordBreak: 'break-all'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <strong style={{ color: '#f87171' }}>Fetch Error Log</strong>
              <button
                onClick={() => setShowLog(false)}
                style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: 16 }}
              >✕</button>
            </div>
            {log || 'Không có log'}
          </div>
        </div>
      )}
    </div>
  )
}

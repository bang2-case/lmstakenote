import { useServerStatus } from '../hooks/useServerStatus'

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

export default function StatusBar() {
  const { connected, fetchState, tokenInfo, triggerRefresh } = useServerStatus()

  const tokenExpiring = tokenInfo && tokenInfo.valid && tokenInfo.remaining_minutes <= 15
  const tokenExpired  = tokenInfo && !tokenInfo.valid

  return (
    <div className={`status-bar ${tokenExpired ? 'status-bar-error' : tokenExpiring ? 'status-bar-warn' : ''}`}>
      {/* Token warning */}
      {tokenExpired && (
        <span className="status-token-alert status-token-expired">
          ⚠ Token đã hết hạn — hãy cập nhật trong file .env
        </span>
      )}
      {tokenExpiring && !tokenExpired && (
        <span className="status-token-alert status-token-expiring">
          ⏱ Token còn {tokenInfo!.remaining_minutes} phút
        </span>
      )}

      <div className="status-bar-right">
        {/* Connection dot */}
        <span className={`status-dot ${connected ? 'status-dot-on' : 'status-dot-off'}`} title={connected ? 'Server đang chạy' : 'Mất kết nối server'} />

        {/* Fetch status */}
        {fetchState.is_fetching ? (
          <span className="status-text status-text-running">🔄 Đang cập nhật...</span>
        ) : fetchState.last_status === 'success' ? (
          <span className="status-text">Cập nhật lúc {formatTime(fetchState.last_fetch)}</span>
        ) : fetchState.last_status === 'error' ? (
          <span className="status-text status-text-error">⚠ Lỗi fetch</span>
        ) : null}

        {/* Manual refresh button */}
        <button
          className="status-refresh-btn"
          onClick={triggerRefresh}
          disabled={fetchState.is_fetching || !connected}
          title="Cập nhật dữ liệu ngay"
        >
          {fetchState.is_fetching ? '⏳' : '↻'} Cập nhật
        </button>
      </div>
    </div>
  )
}

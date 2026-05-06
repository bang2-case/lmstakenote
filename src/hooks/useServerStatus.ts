import { useState, useEffect, useRef, useCallback } from 'react'

export interface FetchState {
  is_fetching: boolean
  last_fetch: string | null
  last_status: 'idle' | 'running' | 'success' | 'error'
  last_message: string
  next_fetch: string | null
}

export interface TokenInfo {
  valid: boolean
  expires_at: string | null
  remaining_minutes: number
}

export interface ServerStatus {
  connected: boolean
  fetchState: FetchState
  tokenInfo: TokenInfo | null
  triggerRefresh: () => Promise<void>
  cancelFetch: () => Promise<void>
}

const DEFAULT_FETCH_STATE: FetchState = {
  is_fetching: false,
  last_fetch: null,
  last_status: 'idle',
  last_message: '',
  next_fetch: null,
}

export function useServerStatus(): ServerStatus {
  const [connected, setConnected] = useState(false)
  const [fetchState, setFetchState] = useState<FetchState>(DEFAULT_FETCH_STATE)
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let ws: WebSocket
    let retryTimeout: ReturnType<typeof setTimeout>

    const connect = () => {
      try {
        ws = new WebSocket('ws://localhost:8000/ws')
        wsRef.current = ws

        ws.onopen = () => setConnected(true)

        ws.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'state') {
              setFetchState(msg.fetch_state)
              setTokenInfo(msg.token)
            } else if (msg.type === 'fetch_start') {
              setFetchState((s) => ({ ...s, is_fetching: true, last_status: 'running', last_message: msg.message }))
            } else if (msg.type === 'fetch_done') {
              setFetchState((s) => ({
                ...s,
                is_fetching: false,
                last_status: msg.status === 'canceled' ? 'idle' : msg.status,
                last_message: msg.message,
                last_fetch: msg.status === 'success' ? msg.timestamp : s.last_fetch,
              }))
              // Reload data after successful fetch
              if (msg.status === 'success') {
                window.dispatchEvent(new CustomEvent('lms-data-updated'))
              }
            }
          } catch { /* ignore */ }
        }

        ws.onclose = () => {
          setConnected(false)
          retryTimeout = setTimeout(connect, 3000)
        }

        ws.onerror = () => {
          ws.close()
        }
      } catch { /* ignore */ }
    }

    connect()
    return () => {
      clearTimeout(retryTimeout)
      ws?.close()
    }
  }, [])

  const triggerRefresh = useCallback(async () => {
    try {
      await fetch('/api/refresh', { method: 'POST' })
    } catch { /* ignore */ }
  }, [])

  const cancelFetch = useCallback(async () => {
    try {
      await fetch('/api/cancel', { method: 'POST' })
    } catch { /* ignore */ }
  }, [])

  return { connected, fetchState, tokenInfo, triggerRefresh, cancelFetch }
}

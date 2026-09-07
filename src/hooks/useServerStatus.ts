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
  message?: string
  mode?: 'local' | 'supabase_cache'
}

export interface ModuleFetchState {
  is_fetching: boolean
  last_status: 'idle' | 'running' | 'success' | 'error'
  last_message: string
}

export interface ServerStatus {
  connected: boolean
  fetchState: FetchState
  tokenInfo: TokenInfo | null
  moduleFetchState: Record<string, ModuleFetchState>
  triggerRefresh: () => Promise<void>
  cancelFetch: () => Promise<void>
  cancelModuleRefresh: (module: 'classes' | 'teachers' | 'tp' | 'cp' | 'oh' | 'assignments') => Promise<void>
  triggerModuleRefresh: (module: 'classes' | 'teachers' | 'tp' | 'cp' | 'oh' | 'assignments') => Promise<void>
}

const DEFAULT_FETCH_STATE: FetchState = {
  is_fetching: false,
  last_fetch: null,
  last_status: 'idle',
  last_message: '',
  next_fetch: null,
}

const DEFAULT_MODULE_STATE: ModuleFetchState = {
  is_fetching: false,
  last_status: 'idle',
  last_message: '',
}

export function useServerStatus(): ServerStatus {
  const [connected, setConnected] = useState(false)
  const [fetchState, setFetchState] = useState<FetchState>(DEFAULT_FETCH_STATE)
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null)
  const [moduleFetchState, setModuleFetchState] = useState<Record<string, ModuleFetchState>>({
    classes: { ...DEFAULT_MODULE_STATE },
    teachers: { ...DEFAULT_MODULE_STATE },
    tp: { ...DEFAULT_MODULE_STATE },
    cp: { ...DEFAULT_MODULE_STATE },
    oh: { ...DEFAULT_MODULE_STATE },
    assignments: { ...DEFAULT_MODULE_STATE },
  })
  const hasSyncedRef = useRef(false)
  const previousFetchStateRef = useRef<FetchState | null>(null)
  const previousModuleStateRef = useRef<Record<string, ModuleFetchState> | null>(null)

  useEffect(() => {
    let alive = true

    const syncStatus = async () => {
      try {
        const [fetchRes, moduleRes, tokenRes] = await Promise.all([
          fetch('/api/fetch-status'),
          fetch('/api/module-fetch-status'),
          fetch('/api/token-status'),
        ])
        if (!alive) return
        if (fetchRes.ok && moduleRes.ok && tokenRes.ok) {
          setConnected(true)
        } else {
          setConnected(false)
        }
        const nextFetchState: FetchState | null = fetchRes.ok ? await fetchRes.json() : null
        const nextModuleState: Record<string, ModuleFetchState> | null = moduleRes.ok ? await moduleRes.json() : null
        const nextTokenInfo: TokenInfo | null = tokenRes.ok ? await tokenRes.json() : null
        if (nextFetchState) setFetchState(nextFetchState)
        if (nextModuleState) {
          setModuleFetchState(nextModuleState)
        }
        if (nextTokenInfo) setTokenInfo(nextTokenInfo)

        if (hasSyncedRef.current) {
          const previousFetchState = previousFetchStateRef.current
          if (
            previousFetchState?.last_status === 'running' &&
            nextFetchState?.last_status === 'success'
          ) {
            window.dispatchEvent(new CustomEvent('lms-data-updated'))
            window.dispatchEvent(new CustomEvent('lms-assignments-updated'))
          }

          const previousModuleState = previousModuleStateRef.current
          if (previousModuleState && nextModuleState) {
            for (const [module, state] of Object.entries(nextModuleState)) {
              if (previousModuleState[module]?.last_status === 'running' && state.last_status === 'success') {
                const eventName = module === 'assignments' ? 'lms-assignments-updated' : 'lms-data-updated'
                window.dispatchEvent(new CustomEvent(eventName))
              }
            }
          }
        }

        if (nextFetchState) previousFetchStateRef.current = nextFetchState
        if (nextModuleState) previousModuleStateRef.current = nextModuleState
        hasSyncedRef.current = true
      } catch {
        if (alive) setConnected(false)
      }
    }

    syncStatus()
    const interval = setInterval(syncStatus, 3000)
    return () => {
      alive = false
      clearInterval(interval)
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

  const cancelModuleRefresh = useCallback(async (module: 'classes' | 'teachers' | 'tp' | 'cp' | 'oh' | 'assignments') => {
    try {
      await fetch(`/api/cancel/${module}`, { method: 'POST' })
    } catch { /* ignore */ }
  }, [])

  const triggerModuleRefresh = useCallback(async (module: 'classes' | 'teachers' | 'tp' | 'cp' | 'oh' | 'assignments') => {
    try {
      await fetch(`/api/refresh/${module}`, { method: 'POST' })
    } catch { /* ignore */ }
  }, [])

  return { connected, fetchState, tokenInfo, moduleFetchState, triggerRefresh, cancelFetch, cancelModuleRefresh, triggerModuleRefresh }
}

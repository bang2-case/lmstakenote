import { useServerStatus } from '../hooks/useServerStatus'

type Module = 'classes' | 'teachers' | 'tp' | 'cp' | 'oh' | 'assignments'

interface RefreshButtonProps {
  module: Module
}

export default function RefreshButton({ module }: RefreshButtonProps) {
  const { connected, moduleFetchState, triggerModuleRefresh, cancelModuleRefresh } = useServerStatus()
  const state = moduleFetchState[module]
  const isFetching = state?.is_fetching ?? false

  return (
    <div className="page-banner-refresh-group">
      <button
        className="page-banner-refresh-btn"
        onClick={() => triggerModuleRefresh(module)}
        disabled={isFetching || !connected}
        title={connected ? 'Tải dữ liệu trang này' : 'Mất kết nối server'}
      >
        {isFetching ? 'Đang tải...' : 'Tải dữ liệu'}
      </button>
      {isFetching && (
        <button
          className="page-banner-refresh-btn page-banner-cancel-btn"
          onClick={() => cancelModuleRefresh(module)}
          title="Dừng quá trình tải dữ liệu trang này"
        >
          Hủy
        </button>
      )}
    </div>
  )
}

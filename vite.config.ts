import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.WEB_PORT || process.env.VITE_WEB_PORT || 5173),
    strictPort: false,
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${process.env.VITE_API_PORT || '8000'}`,
        changeOrigin: true,
      },
      '/ws': {
        target: `ws://127.0.0.1:${process.env.VITE_API_PORT || '8000'}`,
        ws: true,
      },
    },
  },
})

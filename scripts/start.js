import { spawn, execSync } from 'child_process'

console.log('🗄️  Khởi động API server (FastAPI, port 8000)...')
const apiServer = spawn('python', ['server.py'], {
  stdio: 'inherit',
  detached: false,
})

apiServer.on('error', (err) => {
  console.error('❌ Không khởi động được server.py:', err.message)
})

// Đợi server khởi động
await new Promise((resolve) => setTimeout(resolve, 1500))

console.log('🚀 Khởi động Vite...')
try {
  execSync('npx vite', { stdio: 'inherit' })
} finally {
  apiServer.kill()
}

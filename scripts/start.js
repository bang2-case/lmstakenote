import { execSync, spawn } from 'child_process'

console.log('🐍 Đang chạy main.py để lấy data...')
try {
  execSync('python main.py', { stdio: 'inherit' })
  console.log('✅ Lấy data xong!\n')
} catch {
  console.warn('⚠️  main.py thất bại (token hết hạn?), tiếp tục với data cũ...\n')
}

console.log('🗄️  Khởi động API server (port 8000)...')
const apiServer = spawn('python', ['server.py'], {
  stdio: 'inherit',
  detached: false,
})

apiServer.on('error', (err) => {
  console.error('❌ Không khởi động được server.py:', err.message)
})

// Đợi server khởi động
await new Promise((resolve) => setTimeout(resolve, 800))

console.log('🚀 Khởi động Vite...')
try {
  execSync('npx vite', { stdio: 'inherit' })
} finally {
  apiServer.kill()
}

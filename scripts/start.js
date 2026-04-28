import { execSync } from 'child_process'

console.log('🐍 Đang chạy main.py để lấy data...')

try {
  execSync('python main.py', { stdio: 'inherit' })
  console.log('✅ Lấy data xong!\n')
} catch {
  console.warn('⚠️  main.py thất bại (token hết hạn?), tiếp tục chạy web với data cũ...\n')
}

console.log('🚀 Khởi động Vite...')
execSync('npx vite', { stdio: 'inherit' })

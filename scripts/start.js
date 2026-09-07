import { spawn, execSync } from 'child_process'
import net from 'net'

const DEFAULT_API_PORT = Number(process.env.API_PORT || process.env.VITE_API_PORT || 8000)

function canUsePort(port) {
  return new Promise((resolve) => {
    const server = net.createServer()

    server.once('error', () => resolve(false))
    server.once('listening', () => {
      server.close(() => resolve(true))
    })
    server.listen(port, '127.0.0.1')
  })
}

async function findAvailablePort(startPort) {
  for (let port = startPort; port < startPort + 50; port += 1) {
    if (await canUsePort(port)) {
      return port
    }
  }
  throw new Error(`No available API port found from ${startPort} to ${startPort + 49}`)
}

const apiPort = await findAvailablePort(DEFAULT_API_PORT)
const env = {
  ...process.env,
  API_PORT: String(apiPort),
  VITE_API_PORT: String(apiPort),
  DISABLE_AUTO_FETCH: process.env.DISABLE_AUTO_FETCH ?? '1',
  PYTHONIOENCODING: 'utf-8',
}

if (apiPort !== DEFAULT_API_PORT) {
  console.log(`Port ${DEFAULT_API_PORT} is busy. Using API port ${apiPort} instead.`)
}

console.log(`Starting API server on http://127.0.0.1:${apiPort}...`)
const apiServer = spawn('python', ['server.py'], {
  stdio: 'inherit',
  detached: false,
  env,
})

let apiExited = false
apiServer.on('exit', (code, signal) => {
  apiExited = true
  if (code !== 0 && signal == null) {
    console.error(`API server exited with code ${code}.`)
  }
})

apiServer.on('error', (err) => {
  console.error('Could not start server.py:', err.message)
})

await new Promise((resolve) => setTimeout(resolve, 1500))

if (apiExited) {
  process.exitCode = 1
} else {
  console.log('Starting Vite...')
  try {
    execSync('npx vite', { stdio: 'inherit', env })
  } finally {
    apiServer.kill()
  }
}

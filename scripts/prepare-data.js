import { existsSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const requiredFiles = ['classes.json', 'teachers.json', 'tp.json', 'cp.json', 'oh.json'];

function run(command, args, extraEnv = {}) {
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: 'inherit',
    shell: process.platform === 'win32',
    env: { ...process.env, ...extraEnv, PYTHONIOENCODING: 'utf-8' },
  });
  return result.status === 0;
}

function readEnvFile() {
  const envPath = join(root, '.env');
  const values = {};

  if (!existsSync(envPath)) {
    return values;
  }

  const content = readFileSync(envPath, 'utf8');
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const index = line.indexOf('=');
    if (index === -1) continue;
    values[line.slice(0, index).trim()] = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
  }

  return values;
}

function getIdToken(extraEnv = {}) {
  const result = spawnSync('node', ['get-idtoken.js'], {
    cwd: root,
    encoding: 'utf8',
    shell: process.platform === 'win32',
    env: { ...process.env, ...extraEnv },
  });

  if (result.status !== 0) {
    const message = result.stderr || result.stdout || 'Unable to get LMS id token.';
    throw new Error(
      `${message.trim()}\n[prepare-data] Cannot generate LMS data without a valid login. To unblock deploy, set LMS_TOKEN directly in Vercel Environment Variables.`
    );
  }

  return result.stdout.trim().split(/\r?\n/).at(-1);
}

function loadMainPyEnv() {
  const existing = readEnvFile();
  const values = {
    ...existing,
    FIREBASE_API_KEY: (process.env.FIREBASE_API_KEY || process.env.NEXT_PUBLIC_FIREBASE_API_KEY || existing.FIREBASE_API_KEY || '').trim(),
    LMS_LOGIN_EMAIL: (process.env.LMS_LOGIN_EMAIL || existing.LMS_LOGIN_EMAIL || '').trim(),
    LMS_LOGIN_PASSWORD: (process.env.LMS_LOGIN_PASSWORD || existing.LMS_LOGIN_PASSWORD || '').trim(),
    GOOGLE_SHEET_ID: (process.env.GOOGLE_SHEET_ID || existing.GOOGLE_SHEET_ID || '').trim(),
    LMS_TOKEN: (process.env.LMS_TOKEN || existing.LMS_TOKEN || '').trim(),
  };

  if (!values.LMS_TOKEN && values.FIREBASE_API_KEY && values.LMS_LOGIN_EMAIL && values.LMS_LOGIN_PASSWORD) {
    console.log('[prepare-data] Fetching LMS_TOKEN from login credentials.');
    values.LMS_TOKEN = getIdToken(values);
  }

  return values;
}

function findPython() {
  const candidates = process.platform === 'win32'
    ? [['py', ['-3']], ['python', ['--version']], ['python3', ['--version']]]
    : [['python3', ['--version']], ['python', ['--version']]];

  for (const [command, args] of candidates) {
    const result = spawnSync(command, args, {
      cwd: root,
      stdio: 'ignore',
      shell: process.platform === 'win32',
    });
    if (result.status === 0) return command;
  }

  return null;
}

const missing = requiredFiles.filter((name) => !existsSync(join(root, 'public', name)));
const forceFetch = process.env.FORCE_FETCH_DATA === '1';
const skipPrepareData = process.env.SKIP_PREPARE_DATA === '1';

if (skipPrepareData) {
  console.log('[prepare-data] SKIP_PREPARE_DATA=1. Skipping LMS data generation.');
  process.exit(0);
}

if (missing.length === 0 && !forceFetch) {
  console.log('[prepare-data] Static data files already exist. Skipping LMS fetch.');
  process.exit(0);
}

const python = findPython();
if (!python) {
  console.error('[prepare-data] Python is required to generate public/*.json during deploy.');
  process.exit(1);
}

console.log(`[prepare-data] Generating LMS data. Missing: ${missing.join(', ') || 'none'}`);
const mainPyEnv = loadMainPyEnv();

if (existsSync(join(root, 'requirements.txt'))) {
  const pipCommand = process.platform === 'win32' && python === 'py' ? 'py' : python;
  const pipArgs = process.platform === 'win32' && python === 'py'
    ? ['-3', '-m', 'pip', 'install', '-r', 'requirements.txt']
    : ['-m', 'pip', 'install', '-r', 'requirements.txt'];

  if (!run(pipCommand, pipArgs)) {
    console.error('[prepare-data] Failed to install Python dependencies.');
    process.exit(1);
  }
}

const mainCommand = process.platform === 'win32' && python === 'py' ? 'py' : python;
const mainArgs = process.platform === 'win32' && python === 'py' ? ['-3', 'main.py'] : ['main.py'];

if (!run(mainCommand, mainArgs, mainPyEnv)) {
  console.error('[prepare-data] Failed to generate LMS data.');
  process.exit(1);
}

const stillMissing = requiredFiles.filter((name) => !existsSync(join(root, 'public', name)));
if (stillMissing.length > 0) {
  console.error(`[prepare-data] Data generation finished but files are still missing: ${stillMissing.join(', ')}`);
  process.exit(1);
}

console.log('[prepare-data] Data files are ready.');

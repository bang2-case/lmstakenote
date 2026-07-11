#!/usr/bin/env node

import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

function loadEnv() {
  const envPath = join(dirname(fileURLToPath(import.meta.url)), '.env');
  const env = { ...process.env };

  if (!existsSync(envPath)) {
    return env;
  }

  const content = readFileSync(envPath, 'utf8');

  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const index = line.indexOf('=');
    if (index === -1) continue;
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
    env[key] = value;
  }

  return env;
}

const env = loadEnv();
const clean = (value) => String(value || '').trim();
const API_KEY = clean(env.FIREBASE_API_KEY || env.NEXT_PUBLIC_FIREBASE_API_KEY);
const EMAIL = clean(env.LMS_LOGIN_EMAIL);
const PASSWORD = clean(env.LMS_LOGIN_PASSWORD);

async function main() {
  if (!API_KEY || !EMAIL || !PASSWORD) {
    throw new Error('Missing FIREBASE_API_KEY/NEXT_PUBLIC_FIREBASE_API_KEY, LMS_LOGIN_EMAIL, or LMS_LOGIN_PASSWORD');
  }

  if (typeof fetch !== 'function') {
    throw new Error('Node.js 18+ is required because global fetch is not available.');
  }

  const response = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=${encodeURIComponent(API_KEY)}`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        accept: '*/*',
      },
      body: JSON.stringify({
        returnSecureToken: true,
        email: EMAIL,
        password: PASSWORD,
        clientType: 'CLIENT_TYPE_WEB',
      }),
    }
  );

  const data = await response.json();

  if (!response.ok) {
    const message = data?.error?.message || 'Unable to get idToken';
    if (message === 'INVALID_LOGIN_CREDENTIALS') {
      throw new Error(
        'INVALID_LOGIN_CREDENTIALS: Firebase rejected the LMS login. Check FIREBASE_API_KEY, LMS_LOGIN_EMAIL, and LMS_LOGIN_PASSWORD, or set LMS_TOKEN directly in Vercel.'
      );
    }
    throw new Error(message);
  }

  if (!data.idToken) {
    throw new Error('Response did not include idToken');
  }

  console.log(data.idToken);
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});

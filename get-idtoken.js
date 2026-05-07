#!/usr/bin/env node

const API_KEY = 'AIzaSyAh2Au-mk5ci-hN83RUBqj1fsAmCMdvJx4';
const EMAIL = 'anhpnh@mindx.com.vn';
const PASSWORD = 'Hoanganh@123';

async function main() {
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
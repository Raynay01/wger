import 'server-only';

import type { Tokens } from './session';
import { apiUrl } from './session';

// Login against the allauth headless API of Django ("app" client, JWT tokens)

type AuthResult = { ok: true; tokens: Tokens } | { ok: false; message: string };

const HEADERS = { 'Content-Type': 'application/json', 'Accept-Language': 'pt-BR' };

function tokensFrom(json: any): Tokens | null {
  const meta = json?.meta ?? {};
  if (meta.access_token && meta.refresh_token) {
    return { access: meta.access_token, refresh: meta.refresh_token };
  }
  return null;
}

function firstError(json: any, fallback: string): string {
  return json?.errors?.[0]?.message || fallback;
}

export async function loginWithPassword(username: string, password: string): Promise<AuthResult> {
  const response = await fetch(`${apiUrl()}/allauth/app/v1/auth/login`, {
    method: 'POST',
    headers: HEADERS,
    body: JSON.stringify({ username, password }),
    cache: 'no-store',
  });
  const json = await response.json().catch(() => null);
  const tokens = tokensFrom(json);
  if (response.ok && tokens) {
    return { ok: true, tokens };
  }
  return { ok: false, message: firstError(json, 'Usuário ou senha incorretos.') };
}

function usernameFromEmail(email: string | undefined): string {
  const base = (email?.split('@')[0] || 'usuario').replace(/[^a-zA-Z0-9_.-]/g, '').slice(0, 20);
  return `${base || 'usuario'}${Math.floor(1000 + Math.random() * 9000)}`;
}

/**
 * Logs in (or signs up) with the ID token Google gave the browser. Django
 * verifies the token with Google and answers with our own JWT pair.
 */
export async function loginWithGoogle(idToken: string): Promise<AuthResult> {
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
  if (!clientId) {
    return { ok: false, message: 'O login com Google ainda não foi configurado.' };
  }

  const response = await fetch(`${apiUrl()}/allauth/app/v1/auth/provider/token`, {
    method: 'POST',
    headers: HEADERS,
    body: JSON.stringify({
      provider: 'google',
      process: 'login',
      token: { client_id: clientId, id_token: idToken },
    }),
    cache: 'no-store',
  });
  const json = await response.json().catch(() => null);
  const tokens = tokensFrom(json);
  if (response.ok && tokens) {
    return { ok: true, tokens };
  }

  // New account that still needs a username: allauth keeps the pending signup
  // in the session identified by the session token
  const pending = json?.data?.flows?.find((f: any) => f.id === 'provider_signup' && f.is_pending);
  const sessionToken = json?.meta?.session_token;
  if (response.status === 401 && pending && sessionToken) {
    const email = json?.data?.flows?.find((f: any) => f.id === 'provider_signup')?.provider?.email;
    for (let attempt = 0; attempt < 3; attempt++) {
      const signup = await fetch(`${apiUrl()}/allauth/app/v1/auth/provider/signup`, {
        method: 'POST',
        headers: { ...HEADERS, 'X-Session-Token': sessionToken },
        body: JSON.stringify({ username: usernameFromEmail(email) }),
        cache: 'no-store',
      });
      const signupJson = await signup.json().catch(() => null);
      const signupTokens = tokensFrom(signupJson);
      if (signup.ok && signupTokens) {
        return { ok: true, tokens: signupTokens };
      }
    }
  }

  return { ok: false, message: firstError(json, 'Não foi possível entrar com o Google.') };
}

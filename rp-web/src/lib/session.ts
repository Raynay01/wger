// Cookie names and token helpers shared by the proxy, route handlers and server code.
// Tokens never reach client-side JavaScript: the cookies are httpOnly.

export const ACCESS_COOKIE = 'kn_access';
export const REFRESH_COOKIE = 'kn_refresh';

export const REFRESH_MAX_AGE = 60 * 60 * 24 * 120;

export function apiUrl(): string {
  return (process.env.KINUTRI_API_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
}

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge,
  };
}

/** Seconds until the JWT expires, or -1 if it cannot be read */
export function secondsLeft(token: string | undefined): number {
  if (!token) {
    return -1;
  }
  try {
    const payload = token.split('.')[1];
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return Math.floor(json.exp - Date.now() / 1000);
  } catch {
    return -1;
  }
}

export type Tokens = { access: string; refresh: string };

export async function refreshTokens(refresh: string): Promise<Tokens | null> {
  const response = await fetch(`${apiUrl()}/allauth/app/v1/tokens/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
    cache: 'no-store',
  });
  if (!response.ok) {
    return null;
  }
  const json = await response.json();
  const data = json.data ?? {};
  if (!data.access_token) {
    return null;
  }
  return { access: data.access_token, refresh: data.refresh_token ?? refresh };
}

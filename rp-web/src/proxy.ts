import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
import { contentSecurityPolicy, newNonce } from './lib/csp';
import {
  ACCESS_COOKIE,
  cookieOptions,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
  refreshTokens,
  secondsLeft,
} from './lib/session';

const PROTECTED = ['/app', '/pro', '/inicio'];

/**
 * Passes the request on with a fresh nonce in its Content Security Policy,
 * which Next applies to its scripts and styles, and sends the same policy
 * to the browser
 */
function next(request: NextRequest): NextResponse {
  const policy = contentSecurityPolicy(newNonce(), process.env.NODE_ENV === 'production');
  const headers = new Headers(request.headers);
  headers.set('Content-Security-Policy', policy);
  const response = NextResponse.next({ request: { headers } });
  response.headers.set('Content-Security-Policy', policy);
  return response;
}

/**
 * Keeps the access token fresh: shortly before it expires it is renewed with
 * the refresh token, for the response (browser) and the current request
 * (server components). Protected areas without a session go to the login.
 */
export default async function proxy(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  const isProtected = PROTECTED.some(p => request.nextUrl.pathname === p || request.nextUrl.pathname.startsWith(`${p}/`));

  if (secondsLeft(access) > 30) {
    return next(request);
  }

  if (refresh) {
    const tokens = await refreshTokens(refresh).catch(() => null);
    if (tokens) {
      request.cookies.set(ACCESS_COOKIE, tokens.access);
      request.cookies.set(REFRESH_COOKIE, tokens.refresh);
      const response = next(request);
      response.cookies.set(ACCESS_COOKIE, tokens.access, cookieOptions(60 * 60));
      response.cookies.set(REFRESH_COOKIE, tokens.refresh, cookieOptions(REFRESH_MAX_AGE));
      return response;
    }
  }

  if (isProtected) {
    // Built from the request's own URL, so the host (and with it the cookie jar) stays the same
    const login = request.nextUrl.clone();
    login.pathname = '/entrar';
    login.search = '';
    const response = NextResponse.redirect(login, 307);
    response.cookies.delete(ACCESS_COOKIE);
    response.cookies.delete(REFRESH_COOKIE);
    return response;
  }
  return next(request);
}

export const config = {
  // Uploads stream to the API: the proxy would buffer (and cut) bodies over 10 MB
  matcher: ['/((?!_next/static|_next/image|favicon.ico|api/auth|api/mensagens).*)'],
};

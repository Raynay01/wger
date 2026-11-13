import { NextResponse } from 'next/server';
import { loginWithGoogle } from '@/lib/auth';
import { ACCESS_COOKIE, cookieOptions, REFRESH_COOKIE, REFRESH_MAX_AGE } from '@/lib/session';

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  if (typeof body.credential !== 'string' || !body.credential) {
    return NextResponse.json({ message: 'Credencial do Google ausente.' }, { status: 400 });
  }

  const result = await loginWithGoogle(body.credential);
  if (!result.ok) {
    return NextResponse.json({ message: result.message }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ACCESS_COOKIE, result.tokens.access, cookieOptions(60 * 60));
  response.cookies.set(REFRESH_COOKIE, result.tokens.refresh, cookieOptions(REFRESH_MAX_AGE));
  return response;
}

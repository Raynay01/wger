import { NextResponse } from 'next/server';
import { loginWithPassword } from '@/lib/auth';
import { safeNext, seeOther } from '@/lib/redirect';
import { ACCESS_COOKIE, cookieOptions, MFA_COOKIE, MFA_MAX_AGE, REFRESH_COOKIE, REFRESH_MAX_AGE } from '@/lib/session';

/** Username and password login, only for development and automated tests */
export async function POST(request: Request) {
  if (process.env.KINUTRI_DEV_LOGIN !== '1') {
    return NextResponse.json({ message: 'Não disponível.' }, { status: 404 });
  }

  const form = await request.formData();
  const result = await loginWithPassword(String(form.get('username') ?? ''), String(form.get('password') ?? ''));

  const next = safeNext(form.get('next'));
  if (!result.ok && 'mfaSession' in result) {
    const response = seeOther(`/entrar/codigo?${new URLSearchParams({ next })}`);
    response.cookies.set(MFA_COOKIE, result.mfaSession, cookieOptions(MFA_MAX_AGE));
    return response;
  }
  if (!result.ok) {
    return seeOther(`/entrar?${new URLSearchParams({ erro: result.message, next })}`);
  }

  const response = seeOther(next);
  response.cookies.set(ACCESS_COOKIE, result.tokens.access, cookieOptions(60 * 60));
  response.cookies.set(REFRESH_COOKIE, result.tokens.refresh, cookieOptions(REFRESH_MAX_AGE));
  return response;
}

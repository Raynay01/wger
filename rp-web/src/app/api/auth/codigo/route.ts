import { cookies } from 'next/headers';
import { completeMfa } from '@/lib/auth';
import { safeNext, seeOther } from '@/lib/redirect';
import { ACCESS_COOKIE, cookieOptions, MFA_COOKIE, REFRESH_COOKIE, REFRESH_MAX_AGE } from '@/lib/session';

/** Second step of the login: the code of the authenticator app or a recovery code */
export async function POST(request: Request) {
  const form = await request.formData();
  const next = safeNext(form.get('next'));
  const sessionToken = (await cookies()).get(MFA_COOKIE)?.value;
  if (!sessionToken) {
    return seeOther(`/entrar?${new URLSearchParams({ erro: 'O tempo para digitar o código acabou. Entre de novo.', next })}`);
  }

  const result = await completeMfa(sessionToken, String(form.get('code') ?? ''));
  if (!result.ok) {
    const message = 'message' in result ? result.message : 'Código incorreto.';
    return seeOther(`/entrar/codigo?${new URLSearchParams({ erro: message, next })}`);
  }

  const response = seeOther(next);
  response.cookies.delete(MFA_COOKIE);
  response.cookies.set(ACCESS_COOKIE, result.tokens.access, cookieOptions(60 * 60));
  response.cookies.set(REFRESH_COOKIE, result.tokens.refresh, cookieOptions(REFRESH_MAX_AGE));
  return response;
}

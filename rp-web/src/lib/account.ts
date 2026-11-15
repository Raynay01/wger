import 'server-only';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { ACCESS_COOKIE, apiUrl } from './session';

/** Account endpoints of allauth headless ("app" client) as the logged-in user */
export async function accountApi(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<{ status: number; json: any }> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) {
    redirect('/entrar');
  }
  const response = await fetch(`${apiUrl()}/allauth/app/v1/${path}`, {
    method: options.method ?? 'GET',
    headers: {
      'Authorization': `Bearer ${access}`,
      'Accept-Language': 'pt-BR',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: 'no-store',
  });
  return { status: response.status, json: await response.json().catch(() => null) };
}

export type MfaStatus = { professional: boolean; enabled: boolean; required: boolean };

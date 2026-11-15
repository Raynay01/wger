'use server';

import { redirect } from 'next/navigation';
import { accountApi } from '@/lib/account';

function back(params: Record<string, string>): never {
  redirect(`/conta/seguranca?${new URLSearchParams(params)}`);
}

/** Turns on the authenticator app with the first code it shows */
export async function activateTotp(formData: FormData) {
  const code = String(formData.get('code') ?? '').replace(/\s/g, '');
  const password = String(formData.get('password') ?? '');

  // Accounts with a password confirm it first; Google-only accounts don't need to
  if (password) {
    const reauth = await accountApi('auth/reauthenticate', { method: 'POST', body: { password } });
    if (reauth.status !== 200) {
      back({ erro: reauth.json?.errors?.[0]?.message || 'Senha incorreta.' });
    }
  }
  const result = await accountApi('account/authenticators/totp', { method: 'POST', body: { code } });
  if (result.status === 401 && result.json?.data?.flows?.some((f: any) => f.id === 'reauthenticate')) {
    back({ erro: 'Confirme a sua senha junto com o código.', senha: '1' });
  }
  if (result.status !== 200) {
    back({ erro: result.json?.errors?.[0]?.message || 'Código incorreto. Confira o horário do celular e tente de novo.' });
  }
  back({ ativada: '1' });
}

import type { Metadata } from 'next';
import { Logo, Notice } from '@/components/ui';
import { APP_NAME } from '@/lib/brand';
import { safeNext } from '@/lib/redirect';
import { DevLoginForm } from './DevLoginForm';
import { GoogleButton } from './GoogleButton';

export const metadata: Metadata = { title: 'Entrar' };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ erro?: string; next?: string }> }) {
  const { erro, next: rawNext } = await searchParams;
  const next = safeNext(rawNext);
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '';
  const devLogin = process.env.KINUTRI_DEV_LOGIN === '1';

  return (
    <main className="grid min-h-dvh place-items-center bg-navy-900 px-4">
      <div className="w-full max-w-sm rounded-3xl bg-white p-8 shadow-xl">
        <Logo />
        <h1 className="mt-6 text-2xl font-bold">Entrar no {APP_NAME}</h1>
        <p className="mt-1 text-sm text-gray-600">Use a sua conta Google (Gmail). Se for o primeiro acesso, a conta é criada na hora.</p>

        <div className="mt-6 flex flex-col gap-4">
          {erro && <Notice tone="error">{erro}</Notice>}
          {googleClientId ? (
            <GoogleButton clientId={googleClientId} next={next} />
          ) : (
            <Notice>O login com Google ainda não foi configurado neste servidor.</Notice>
          )}
          {devLogin && (
            <details className="rounded-xl border border-navy-100 p-3 text-sm" open={!googleClientId}>
              <summary className="cursor-pointer font-medium text-navy-700">Acesso de desenvolvimento</summary>
              <DevLoginForm next={next} />
            </details>
          )}
        </div>

        <p className="mt-6 text-xs text-gray-500">
          Ao entrar, você concorda com os termos de uso e a política de privacidade. Dados de saúde só são compartilhados
          com os profissionais que você autorizar.
        </p>
      </div>
    </main>
  );
}

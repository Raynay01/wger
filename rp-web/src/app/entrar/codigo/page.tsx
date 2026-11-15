import type { Metadata } from 'next';
import Link from 'next/link';
import { Button, Logo, Notice, inputClass } from '@/components/ui';
import { safeNext } from '@/lib/redirect';

export const metadata: Metadata = { title: 'Código de verificação' };

export default async function MfaCodePage({ searchParams }: { searchParams: Promise<{ erro?: string; next?: string }> }) {
  const { erro, next: rawNext } = await searchParams;
  const next = safeNext(rawNext);
  return (
    <main className="grid min-h-dvh place-items-center bg-navy-900 px-4">
      <div className="w-full max-w-sm rounded-3xl bg-white p-8 shadow-xl">
        <Logo />
        <h1 className="mt-6 text-2xl font-bold">Verificação em duas etapas</h1>
        <p className="mt-1 text-sm text-gray-600">
          Digite o código de 6 dígitos do seu aplicativo autenticador. Se estiver sem o celular, use um dos códigos de recuperação.
        </p>
        <form action="/api/auth/codigo" method="post" className="mt-6 flex flex-col gap-3">
          {erro && <Notice tone="error">{erro}</Notice>}
          <input type="hidden" name="next" value={next} />
          <label className="flex flex-col gap-1 text-sm font-medium">
            Código
            <input
              name="code"
              required
              autoFocus
              autoComplete="one-time-code"
              inputMode="numeric"
              maxLength={20}
              className={`${inputClass} text-lg tracking-widest`}
            />
          </label>
          <Button type="submit">Confirmar</Button>
        </form>
        <p className="mt-4 text-sm">
          <Link href="/entrar" className="text-navy-700 underline">
            Voltar e entrar de novo
          </Link>
        </p>
      </div>
    </main>
  );
}

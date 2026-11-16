import Link from 'next/link';
import { Logo } from '@/components/ui';

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh">
      <header className="bg-navy-900 text-white shadow">
        <div className="mx-auto flex max-w-3xl items-center gap-6 px-4 py-3">
          <Link href="/inicio" aria-label="Início">
            <Logo dark />
          </Link>
          <Link href="/inicio" className="ml-auto text-sm text-navy-100 hover:text-white">
            Voltar ao app
          </Link>
          <Link href="/sair" className="text-sm text-navy-100 hover:text-white">
            Sair
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-8">
        <nav aria-label="Conta" className="mb-6 flex gap-2 text-sm">
          <Link href="/conta/seguranca" className="rounded-lg border border-navy-100 px-3 py-1.5 font-medium text-navy-700 hover:bg-navy-100">
            Segurança
          </Link>
          <Link href="/conta/avisos" className="rounded-lg border border-navy-100 px-3 py-1.5 font-medium text-navy-700 hover:bg-navy-100">
            Avisos por e-mail
          </Link>
        </nav>
        {children}
      </main>
    </div>
  );
}

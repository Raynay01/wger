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
      <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
    </div>
  );
}

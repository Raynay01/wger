import Link from 'next/link';
import { Logo } from './ui';

type NavItem = { href: string; label: string };

export function AppShell({
  area,
  nav,
  switchTo,
  children,
}: {
  area: string;
  nav: NavItem[];
  switchTo?: { href: string; label: string };
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-10 bg-navy-900 text-white shadow">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link href="/inicio" aria-label="Início">
            <Logo dark />
          </Link>
          <span className="rounded-full bg-navy-700 px-2.5 py-0.5 text-xs font-semibold text-neon-500">{area}</span>
          <nav aria-label="Principal" className="order-last flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto">
            {nav.map(item => (
              <Link key={item.href} href={item.href} className="whitespace-nowrap rounded-lg px-3 py-1.5 text-sm text-navy-100 hover:bg-navy-700 hover:text-white">
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            {switchTo && (
              <Link href={switchTo.href} className="rounded-lg px-3 py-1.5 text-sm text-neon-500 hover:bg-navy-700">
                {switchTo.label}
              </Link>
            )}
            <form action="/sair" method="post">
              <button type="submit" className="rounded-lg px-3 py-1.5 text-sm text-navy-100 hover:bg-navy-700">
                Sair
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}

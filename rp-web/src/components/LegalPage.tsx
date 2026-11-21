import Link from 'next/link';
import { Logo, Notice } from '@/components/ui';
import type { LegalInfo } from '@/lib/legal';

/** Public page with a legal text: privacy policy, terms of use, account deletion */
export function LegalPage({
  title,
  updated,
  info,
  children,
}: {
  title: string;
  updated: string;
  info: LegalInfo;
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-dvh bg-[#f6f8fb]">
      <header className="bg-navy-900 px-6 py-5">
        <div className="mx-auto max-w-3xl">
          <Link href="/" aria-label="Início">
            <Logo dark />
          </Link>
        </div>
      </header>
      <article className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-10 text-[15px] leading-relaxed text-navy-900">
        <h1 className="text-3xl font-bold">{title}</h1>
        <p className="text-sm text-gray-500">Última atualização: {updated}</p>
        {info.draft && (
          <Notice>
            Minuta em revisão jurídica: este texto descreve como o sistema funciona hoje e ainda será revisado por
            advogado antes do uso com pacientes.
          </Notice>
        )}
        {children}
        <nav className="mt-8 flex flex-wrap gap-4 border-t border-navy-100 pt-6 text-sm">
          <Link className="text-navy-700 underline" href="/privacidade">
            Política de privacidade
          </Link>
          <Link className="text-navy-700 underline" href="/termos">
            Termos de uso
          </Link>
          <Link className="text-navy-700 underline" href="/excluir-conta">
            Excluir a conta
          </Link>
        </nav>
      </article>
    </main>
  );
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-4 flex flex-col gap-2">
      <h2 className="text-xl font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export function List({ children }: { children: React.ReactNode }) {
  return <ul className="ml-5 flex list-disc flex-col gap-1">{children}</ul>;
}

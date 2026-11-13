import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { LinkButton, Logo } from '@/components/ui';
import { APP_NAME, APP_TAGLINE } from '@/lib/brand';
import { REFRESH_COOKIE } from '@/lib/session';

const PILLARS = [
  {
    title: 'Treino',
    text: 'Ficha do dia, cargas, RPE e RIR. Seu personal acompanha o que foi feito.',
  },
  {
    title: 'Fisioterapia',
    text: 'Exercícios com vídeo, registro de dor de 0 a 10 e evolução funcional.',
  },
  {
    title: 'Nutrição',
    text: 'Dieta por refeição, diário, calorias, macros, substituições e água.',
  },
];

export default async function Home() {
  if ((await cookies()).get(REFRESH_COOKIE)) {
    redirect('/inicio');
  }

  return (
    <main className="min-h-dvh bg-navy-900 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-16 px-6 py-10">
        <header className="flex items-center justify-between">
          <Logo dark />
          <LinkButton href="/entrar" variant="secondary">
            Entrar
          </LinkButton>
        </header>

        <section className="max-w-2xl">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-neon-500">{APP_TAGLINE}</p>
          <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
            Treino, reabilitação e alimentação em um só lugar.
          </h1>
          <p className="mt-5 text-lg text-navy-100">
            Com o {APP_NAME}, você vê o treino e a alimentação do dia lado a lado, e cada profissional que acompanha
            você cuida da sua parte, com o que você autorizar compartilhar.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <LinkButton href="/entrar" variant="secondary">
              Começar com Google
            </LinkButton>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-3">
          {PILLARS.map(pillar => (
            <div key={pillar.title} className="rounded-2xl border border-navy-700 bg-navy-800 p-5">
              <h2 className="font-semibold text-neon-500">{pillar.title}</h2>
              <p className="mt-2 text-sm text-navy-100">{pillar.text}</p>
            </div>
          ))}
        </section>

        <footer className="text-xs text-navy-100/70">
          Código-fonte disponível sob a licença AGPL-3.0, baseado no projeto wger.
        </footer>
      </div>
    </main>
  );
}

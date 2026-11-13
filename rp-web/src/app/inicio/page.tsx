import { redirect } from 'next/navigation';
import { Logo } from '@/components/ui';
import { api } from '@/lib/api';
import { professionalContext } from '@/lib/roles';
import type { Paginated, Relationship } from '@/lib/types';

export default async function StartPage() {
  const [{ isProfessional }, asPatient] = await Promise.all([
    professionalContext(),
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'patient' } }),
  ]);

  if (!isProfessional) {
    redirect('/app');
  }

  const invitations = asPatient.results.filter(r => r.status === 'invited').length;

  return (
    <main className="grid min-h-dvh place-items-center bg-navy-900 px-4">
      <div className="w-full max-w-lg">
        <Logo dark />
        <h1 className="mt-6 text-2xl font-bold text-white">Como você quer entrar?</h1>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <a href="/pro" className="rounded-2xl bg-white p-5 hover:ring-4 hover:ring-neon-500">
            <p className="text-lg font-semibold">Área profissional</p>
            <p className="mt-1 text-sm text-gray-600">Pacientes, prescrições e acompanhamento.</p>
          </a>
          <a href="/app" className="rounded-2xl bg-white p-5 hover:ring-4 hover:ring-neon-500">
            <p className="text-lg font-semibold">Meu Dia</p>
            <p className="mt-1 text-sm text-gray-600">
              Seu treino e sua alimentação{invitations ? ` · ${invitations} convite(s)` : ''}.
            </p>
          </a>
        </div>
      </div>
    </main>
  );
}

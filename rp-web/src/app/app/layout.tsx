import { AppShell } from '@/components/AppShell';
import { api } from '@/lib/api';
import { professionalContext } from '@/lib/roles';

export default async function PatientLayout({ children }: { children: React.ReactNode }) {
  const [{ isProfessional }, unread] = await Promise.all([
    professionalContext(),
    api<Record<string, number>>('care-message/unread/', { query: { role: 'patient' } }),
  ]);
  return (
    <AppShell
      area="Meu acompanhamento"
      nav={[
        { href: '/app', label: 'Meu Dia' },
        { href: '/app/agenda', label: 'Agenda' },
        { href: '/app/mensagens', label: 'Mensagens', badge: Object.values(unread).reduce((a, b) => a + b, 0) },
        { href: '/app/convites', label: 'Profissionais' },
        { href: '/app/compartilhamento', label: 'Compartilhamento' },
        { href: '/app/evolucao', label: 'Evolução' },
        { href: '/app/constancia', label: 'Constância' },
        { href: '/app/privacidade', label: 'Privacidade' },
        { href: '/conta/seguranca', label: 'Conta' },
      ]}
      switchTo={isProfessional ? { href: '/pro', label: 'Área profissional' } : { href: '/pro/configurar', label: 'Sou profissional' }}
    >
      {children}
    </AppShell>
  );
}

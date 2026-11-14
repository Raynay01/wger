import { AppShell } from '@/components/AppShell';
import { api } from '@/lib/api';

export default async function ProfessionalLayout({ children }: { children: React.ReactNode }) {
  const unread = await api<Record<string, number>>('care-message/unread/', { query: { role: 'professional' } });
  return (
    <AppShell
      area="Área profissional"
      nav={[
        { href: '/pro', label: 'Pacientes' },
        { href: '/pro/agenda', label: 'Agenda' },
        { href: '/pro/mensagens', label: 'Mensagens', badge: Object.values(unread).reduce((a, b) => a + b, 0) },
        { href: '/pro/pacientes/novo', label: 'Convidar' },
        { href: '/pro/alimentos', label: 'Alimentos' },
        { href: '/pro/alertas', label: 'Alertas de dor' },
        { href: '/pro/configurar', label: 'Configurações' },
      ]}
      switchTo={{ href: '/app', label: 'Meu Dia' }}
    >
      {children}
    </AppShell>
  );
}

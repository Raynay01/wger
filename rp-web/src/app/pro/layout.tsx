import { AppShell } from '@/components/AppShell';
import { api } from '@/lib/api';

export default async function ProfessionalLayout({ children }: { children: React.ReactNode }) {
  const [unread, videos] = await Promise.all([
    api<Record<string, number>>('care-message/unread/', { query: { role: 'professional' } }),
    api<{ count: number }>('care-message/videos/', { query: { limit: 1 } }),
  ]);
  return (
    <AppShell
      area="Área profissional"
      nav={[
        { href: '/pro', label: 'Pacientes' },
        { href: '/pro/agenda', label: 'Agenda' },
        { href: '/pro/mensagens', label: 'Mensagens', badge: Object.values(unread).reduce((a, b) => a + b, 0) },
        { href: '/pro/videos', label: 'Vídeos', badge: videos.count, badgeLabel: 'para revisar' },
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

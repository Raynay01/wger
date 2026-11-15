import Link from 'next/link';
import { AppShell } from '@/components/AppShell';
import { Notice } from '@/components/ui';
import type { MfaStatus } from '@/lib/account';
import { api } from '@/lib/api';

export default async function ProfessionalLayout({ children }: { children: React.ReactNode }) {
  // Without two-step verification the API only answers the setup (organization,
  // registration); the other pages send the professional to the security page
  const { required } = await api<MfaStatus>('care/mfa/');
  const [unread, videos] = required
    ? [{} as Record<string, number>, { count: 0 }]
    : await Promise.all([
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
        { href: '/conta/seguranca', label: 'Segurança' },
      ]}
      switchTo={{ href: '/app', label: 'Meu Dia' }}
    >
      {required && (
        <div className="mb-6">
          <Notice tone="error">
            Para acessar os dados dos pacientes, ative a verificação em duas etapas.{' '}
            <Link href="/conta/seguranca" className="font-semibold underline">
              Ativar agora
            </Link>
          </Notice>
        </div>
      )}
      {children}
    </AppShell>
  );
}

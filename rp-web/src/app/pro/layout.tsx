import { AppShell } from '@/components/AppShell';

export default function ProfessionalLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell
      area="Área profissional"
      nav={[
        { href: '/pro', label: 'Pacientes' },
        { href: '/pro/pacientes/novo', label: 'Convidar' },
        { href: '/pro/alertas', label: 'Alertas de dor' },
        { href: '/pro/configurar', label: 'Configurações' },
      ]}
      switchTo={{ href: '/app', label: 'Meu Dia' }}
    >
      {children}
    </AppShell>
  );
}

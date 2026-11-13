import { AppShell } from '@/components/AppShell';
import { professionalContext } from '@/lib/roles';

export default async function PatientLayout({ children }: { children: React.ReactNode }) {
  const { isProfessional } = await professionalContext();
  return (
    <AppShell
      area="Meu acompanhamento"
      nav={[
        { href: '/app', label: 'Meu Dia' },
        { href: '/app/convites', label: 'Profissionais' },
        { href: '/app/compartilhamento', label: 'Compartilhamento' },
        { href: '/app/evolucao', label: 'Evolução' },
      ]}
      switchTo={isProfessional ? { href: '/pro', label: 'Área profissional' } : { href: '/pro/configurar', label: 'Sou profissional' }}
    >
      {children}
    </AppShell>
  );
}

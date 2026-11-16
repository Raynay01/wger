import type { Metadata } from 'next';
import { saveNotices } from '@/app/conta/actions';
import { Button, Card, Notice } from '@/components/ui';
import { api } from '@/lib/api';

export const metadata: Metadata = { title: 'Avisos' };

type Notices = Record<
  'email_messages' | 'email_prescriptions' | 'email_appointments' | 'push_messages' | 'push_prescriptions' | 'push_appointments',
  boolean
>;

const KINDS: { key: 'messages' | 'prescriptions' | 'appointments'; label: string; hint: string }[] = [
  {
    key: 'messages',
    label: 'Mensagens novas',
    hint: 'Quando uma mensagem fica sem ler por alguns minutos. No máximo um aviso por conversa a cada hora.',
  },
  { key: 'prescriptions', label: 'Planos publicados', hint: 'Quando um profissional publica um treino, dieta ou protocolo para você.' },
  { key: 'appointments', label: 'Atendimentos', hint: 'Quando um atendimento é marcado, remarcado ou cancelado.' },
];

export default async function NoticesPage({ searchParams }: { searchParams: Promise<{ salvo?: string }> }) {
  const { salvo } = await searchParams;
  const [notices, devices] = await Promise.all([
    api<Notices>('care/notices/'),
    api<{ devices: number }>('care/push-devices/'),
  ]);
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Avisos</h1>
        <p className="text-sm text-gray-600">
          Os avisos não trazem o conteúdo das mensagens nem dados de saúde: só contam que há algo novo e levam para o app.
        </p>
      </div>
      {salvo && <Notice tone="success">Preferências salvas.</Notice>}
      <Card title="Quero ser avisado quando houver">
        <form action={saveNotices} className="flex flex-col gap-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-600">
                <th className="pb-2 font-medium">Aviso</th>
                <th className="pb-2 text-center font-medium">E-mail</th>
                <th className="pb-2 text-center font-medium">Celular</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-100">
              {KINDS.map(kind => (
                <tr key={kind.key}>
                  <td className="py-3 pr-4">
                    <span className="font-semibold">{kind.label}</span>
                    <span className="block text-gray-600">{kind.hint}</span>
                  </td>
                  {(['email', 'push'] as const).map(channel => {
                    const name = `${channel}_${kind.key}` as keyof Notices;
                    return (
                      <td key={channel} className="py-3 text-center">
                        <input
                          type="checkbox"
                          name={name}
                          defaultChecked={notices[name]}
                          aria-label={`${kind.label} por ${channel === 'email' ? 'e-mail' : 'celular'}`}
                          className="size-4"
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-gray-600">
            {devices.devices === 0
              ? 'Nenhum celular recebe avisos ainda. Os avisos no celular começam quando você entrar pelo app do ALMOVA.'
              : `${devices.devices} ${devices.devices === 1 ? 'celular recebe' : 'celulares recebem'} os avisos.`}
          </p>
          <div>
            <Button type="submit">Salvar</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

import type { Metadata } from 'next';
import { saveNotices } from '@/app/conta/actions';
import { Button, Card, Notice } from '@/components/ui';
import { api } from '@/lib/api';

export const metadata: Metadata = { title: 'Avisos por e-mail' };

type Notices = { email_messages: boolean; email_prescriptions: boolean; email_appointments: boolean };

const OPTIONS: { name: keyof Notices; label: string; hint: string }[] = [
  {
    name: 'email_messages',
    label: 'Mensagens novas',
    hint: 'Quando uma mensagem fica sem ler por alguns minutos. No máximo um e-mail por conversa a cada hora.',
  },
  { name: 'email_prescriptions', label: 'Planos publicados', hint: 'Quando um profissional publica um treino, dieta ou protocolo para você.' },
  { name: 'email_appointments', label: 'Atendimentos', hint: 'Quando um atendimento é marcado, remarcado ou cancelado.' },
];

export default async function NoticesPage({ searchParams }: { searchParams: Promise<{ salvo?: string }> }) {
  const { salvo } = await searchParams;
  const notices = await api<Notices>('care/notices/');
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Avisos por e-mail</h1>
        <p className="text-sm text-gray-600">
          Os e-mails não trazem o conteúdo das mensagens nem dados de saúde: só avisam que há algo novo e levam para o app.
        </p>
      </div>
      {salvo && <Notice tone="success">Preferências salvas.</Notice>}
      <Card title="Quero receber um e-mail quando houver">
        <form action={saveNotices} className="flex flex-col gap-4">
          {OPTIONS.map(option => (
            <label key={option.name} className="flex items-start gap-3 text-sm">
              <input type="checkbox" name={option.name} defaultChecked={notices[option.name]} className="mt-1 size-4" />
              <span>
                <span className="font-semibold">{option.label}</span>
                <span className="block text-gray-600">{option.hint}</span>
              </span>
            </label>
          ))}
          <div>
            <Button type="submit">Salvar</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

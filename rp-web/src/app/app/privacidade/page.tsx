import type { Metadata } from 'next';
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { Badge, Button, Card, Field, inputClass, Notice } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { dateTime } from '@/lib/format';
import type { Paginated } from '@/lib/types';

export const metadata: Metadata = { title: 'Privacidade' };

type DataRequest = {
  id: string;
  kind: 'export' | 'deletion';
  status: 'pending' | 'done' | 'cancelled' | 'rejected';
  created: string;
  completed_at: string | null;
  notes: string;
};

const KIND = { export: 'Exportação dos dados', deletion: 'Exclusão da conta' };
const STATUS = { pending: 'Em análise', done: 'Concluído', cancelled: 'Cancelado', rejected: 'Recusado' };

async function requestDeletion(formData: FormData) {
  'use server';
  if (String(formData.get('confirmation') ?? '').trim().toUpperCase() !== 'EXCLUIR') {
    redirect(`/app/privacidade?erro=${encodeURIComponent('Digite EXCLUIR para confirmar.')}`);
  }
  try {
    await api('data-request/', { method: 'POST', body: { confirm: true } });
  } catch (error) {
    if (error instanceof ApiError) {
      redirect(`/app/privacidade?erro=${encodeURIComponent(error.message)}`);
    }
    throw error;
  }
  revalidatePath('/app', 'layout');
  redirect('/app/privacidade?pedido=1');
}

async function cancelRequest(formData: FormData) {
  'use server';
  await api(`data-request/${formData.get('id')}/cancel/`, { method: 'POST' });
  revalidatePath('/app/privacidade');
}

export default async function PrivacyPage({ searchParams }: { searchParams: Promise<{ erro?: string; pedido?: string }> }) {
  const { erro, pedido } = await searchParams;
  const requests = await api<Paginated<DataRequest>>('data-request/', { query: { limit: 50 } });
  const pendingDeletion = requests.results.find(r => r.kind === 'deletion' && r.status === 'pending');

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Privacidade e seus dados</h1>
        <p className="mt-1 text-sm text-gray-600">
          Pela Lei Geral de Proteção de Dados (LGPD), você pode ver tudo o que guardamos sobre você, levar seus dados para
          outro serviço e pedir a exclusão da sua conta.
        </p>
      </div>
      <ErrorFromQuery erro={erro} />
      {pedido && <Notice tone="success">Pedido de exclusão registrado. Seus acompanhamentos foram encerrados.</Notice>}

      <Card title="Baixar meus dados">
        <p className="text-sm text-gray-700">
          Um arquivo com sua conta, consentimentos, profissionais, o que você compartilhou e quem acessou, planos, diário
          alimentar, água, treinos, medidas, fotos, fisioterapia e avaliações.
        </p>
        <a
          href="/api/meus-dados"
          className="mt-3 inline-flex items-center rounded-xl bg-navy-900 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-700"
        >
          Baixar arquivo (JSON)
        </a>
      </Card>

      <Card title="Excluir minha conta">
        {pendingDeletion ? (
          <div className="flex flex-col gap-3 text-sm">
            <p>
              Seu pedido de exclusão de {dateTime(pendingDeletion.created)} está em análise. Seus profissionais já não
              acompanham você nem veem os seus dados.
            </p>
            <form action={cancelRequest}>
              <input type="hidden" name="id" value={pendingDeletion.id} />
              <Button variant="ghost" className="border border-navy-100">
                Desistir da exclusão
              </Button>
            </form>
          </div>
        ) : (
          <form action={requestDeletion} className="flex flex-col gap-3 text-sm">
            <p className="text-gray-700">O que acontece:</p>
            <ul className="list-disc pl-5 text-gray-700">
              <li>Na hora: todos os acompanhamentos são encerrados e nada mais é compartilhado.</li>
              <li>
                Depois: a equipe do app exclui a sua conta e os seus dados. Se um profissional tiver registros clínicos que a
                lei obriga a guardar (prontuário), avisamos você sobre o que precisa ser mantido.
              </li>
              <li>Se quiser uma cópia, baixe os seus dados antes.</li>
            </ul>
            <Field label="Digite EXCLUIR para confirmar">
              <input name="confirmation" required autoComplete="off" className={inputClass} />
            </Field>
            <div>
              <Button type="submit" variant="danger">
                Pedir a exclusão da conta
              </Button>
            </div>
          </form>
        )}
      </Card>

      {requests.results.length > 0 && (
        <Card title="Seus pedidos">
          <ul className="flex flex-col divide-y divide-navy-100 text-sm">
            {requests.results.map(r => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  {KIND[r.kind]} · {dateTime(r.created)}
                  {r.notes && <span className="block text-xs text-gray-500">{r.notes}</span>}
                </span>
                <Badge tone={r.status === 'done' ? 'neon' : r.status === 'pending' ? 'amber' : 'gray'}>{STATUS[r.status]}</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

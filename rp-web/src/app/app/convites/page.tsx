import type { Metadata } from 'next';
import { Badge, Button, Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { DISCIPLINE_LABELS, PROFESSION_LABELS } from '@/lib/brand';
import { STATUS_LABELS, date } from '@/lib/format';
import type { Paginated, Relationship } from '@/lib/types';
import { acceptInvitation, declineInvitation, endRelationship } from '../actions';

export const metadata: Metadata = { title: 'Meus profissionais' };

export default async function InvitationsPage() {
  const list = await api<Paginated<Relationship>>('care-relationship/', { query: { role: 'patient', limit: 100 } });
  const invitations = list.results.filter(r => r.status === 'invited');
  const current = list.results.filter(r => r.status === 'active' || r.status === 'paused');

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Meus profissionais</h1>

      <Card title="Convites">
        {invitations.length === 0 ? (
          <Empty title="Nenhum convite pendente">Quando um profissional convidar você pelo seu e-mail, o convite aparece aqui.</Empty>
        ) : (
          <ul className="flex flex-col gap-4">
            {invitations.map(invitation => (
              <li key={invitation.id} className="rounded-xl border border-navy-100 p-4">
                <p className="font-semibold">{invitation.professional_name}</p>
                <p className="text-sm text-gray-600">
                  {PROFESSION_LABELS[invitation.discipline]} · {invitation.organization_name}
                </p>
                <p className="mt-3 text-sm text-gray-700">
                  Ao aceitar, você autoriza este profissional a prescrever e acompanhar a sua parte de{' '}
                  <strong>{DISCIPLINE_LABELS[invitation.discipline].toLowerCase()}</strong> e a ver o que você registrar nela. Seus
                  dados dos outros módulos só são compartilhados se você autorizar depois, e você pode encerrar o
                  acompanhamento quando quiser.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <form action={acceptInvitation}>
                    <input type="hidden" name="id" value={invitation.id} />
                    <Button variant="secondary">Aceitar e autorizar</Button>
                  </form>
                  <form action={declineInvitation}>
                    <input type="hidden" name="id" value={invitation.id} />
                    <Button variant="ghost" className="border border-navy-100">
                      Recusar
                    </Button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Quem acompanha você">
        {current.length === 0 ? (
          <Empty title="Nenhum profissional ainda" />
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {current.map(relationship => (
              <li key={relationship.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-semibold">{relationship.professional_name}</p>
                  <p className="text-sm text-gray-600">
                    {PROFESSION_LABELS[relationship.discipline]} · desde {date(relationship.started)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={relationship.status === 'active' ? 'neon' : 'amber'}>{STATUS_LABELS[relationship.status]}</Badge>
                  <form action={endRelationship}>
                    <input type="hidden" name="id" value={relationship.id} />
                    <Button variant="danger">Encerrar</Button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

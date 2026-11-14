import Link from 'next/link';
import { DISCIPLINE_LABELS, PROFESSION_LABELS } from '@/lib/brand';
import type { Relationship } from '@/lib/types';
import { Badge, Empty } from './ui';

/** The follow-ups of the user with their unread messages, unread first */
export function ConversationList({
  relationships,
  unread,
  basePath,
  side,
}: {
  relationships: Relationship[];
  unread: Record<string, number>;
  basePath: string;
  side: 'patient' | 'professional';
}) {
  const shown = relationships
    .filter(r => r.status !== 'invited')
    .sort((a, b) => (unread[b.id] ?? 0) - (unread[a.id] ?? 0) || Number(b.status !== 'ended') - Number(a.status !== 'ended'));
  if (shown.length === 0) {
    return (
      <Empty title="Nenhuma conversa">
        {side === 'patient' ? 'Quando um profissional acompanhar você, a conversa com ele aparece aqui.' : 'Quando um paciente aceitar o seu convite, a conversa aparece aqui.'}
      </Empty>
    );
  }
  return (
    <ul className="flex flex-col divide-y divide-navy-100 rounded-2xl border border-navy-100 bg-white">
      {shown.map(r => {
        const count = unread[r.id] ?? 0;
        const name = side === 'patient' ? r.professional_name : (r.patient_name ?? r.invited_email);
        const detail = side === 'patient' ? PROFESSION_LABELS[r.discipline] : DISCIPLINE_LABELS[r.discipline];
        return (
          <li key={r.id}>
            <Link href={`${basePath}/${r.id}`} className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-navy-100/40">
              <div>
                <p className={count ? 'font-bold' : 'font-medium'}>{name}</p>
                <p className="text-sm text-gray-500">
                  {detail}
                  {r.status === 'ended' && ' · encerrado'}
                </p>
              </div>
              {count > 0 && (
                <Badge tone="neon">
                  {count} {count === 1 ? 'nova' : 'novas'}
                </Badge>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

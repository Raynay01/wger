import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { SendInvitation } from '@/components/SendInvitation';
import { Badge, Card, Empty, LinkButton, Notice } from '@/components/ui';
import { api } from '@/lib/api';
import { DISCIPLINE_LABELS } from '@/lib/brand';
import { STATUS_LABELS, date } from '@/lib/format';
import { professionalContext } from '@/lib/roles';
import type { Paginated, Relationship } from '@/lib/types';

export const metadata: Metadata = { title: 'Pacientes' };

export default async function ProfessionalHome({ searchParams }: { searchParams: Promise<{ erro?: string; enviado?: string }> }) {
  const { erro, enviado } = await searchParams;
  const { organizations, registrations } = await professionalContext();
  const ready = organizations.length > 0 && registrations.length > 0;
  const [relationships, alerts] = await Promise.all([
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'professional', limit: 200 } }),
    registrations.some(r => r.discipline === 'physio') ? api<unknown[]>('pain-record/alerts/') : Promise.resolve([]),
  ]);
  const open = relationships.results.filter(r => r.status === 'active' || r.status === 'paused');
  const invited = relationships.results.filter(r => r.status === 'invited');

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Pacientes</h1>
        {ready && <LinkButton href="/pro/pacientes/novo" variant="secondary">Convidar paciente</LinkButton>}
      </div>

      <ErrorFromQuery erro={erro} />
      {enviado && <Notice tone="success">Convite enviado por e-mail.</Notice>}

      {!ready && (
        <Notice>
          Para acompanhar pacientes, crie a sua organização e informe o seu registro no conselho.{' '}
          <Link href="/pro/configurar" className="font-semibold underline">
            Configurar agora
          </Link>
        </Notice>
      )}

      {alerts.length > 0 && (
        <Notice tone="error">
          {alerts.length} registro(s) de dor acima do limite nos últimos 14 dias.{' '}
          <Link href="/pro/alertas" className="font-semibold underline">
            Ver alertas
          </Link>
        </Notice>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Pacientes ativos" value={open.length} />
        <Stat label="Convites pendentes" value={invited.length} />
        <Stat label="Alertas de dor" value={alerts.length} />
      </div>

      <Card title="Acompanhamentos">
        {open.length === 0 ? (
          <Empty title="Nenhum paciente ainda">Convide um paciente pelo e-mail dele. Ele aceita no app e aparece aqui.</Empty>
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {open.map(r => (
              <li key={r.id}>
                <Link href={`/pro/pacientes/${r.id}`} className="flex flex-wrap items-center justify-between gap-3 py-3 hover:bg-navy-100/40">
                  <div>
                    <p className="font-semibold">{r.patient_name}</p>
                    <p className="text-sm text-gray-600">
                      {DISCIPLINE_LABELS[r.discipline]} · desde {date(r.started)} · {r.organization_name}
                    </p>
                  </div>
                  <Badge tone={r.status === 'active' ? 'neon' : 'amber'}>{STATUS_LABELS[r.status]}</Badge>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {invited.length > 0 && (
        <Card title="Convites pendentes">
          <ul className="flex flex-col divide-y divide-navy-100 text-sm">
            {invited.map(r => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  {r.invited_email} · {DISCIPLINE_LABELS[r.discipline]}
                </span>
                <span className="flex flex-wrap items-center gap-3">
                  <SendInvitation relationship={r} back="/pro" />
                  <Link href={`/pro/pacientes/novo?convite=${r.id}`} className="font-semibold text-navy-700 underline">
                    Link do convite
                  </Link>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl bg-navy-900 p-5 text-white">
      <p className="text-sm text-navy-100">{label}</p>
      <p className="mt-1 text-3xl font-bold tabular-nums text-neon-500">{value}</p>
    </div>
  );
}

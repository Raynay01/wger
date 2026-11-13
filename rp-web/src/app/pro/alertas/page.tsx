import type { Metadata } from 'next';
import Link from 'next/link';
import { Badge, Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { dateTime } from '@/lib/format';
import type { Paginated, Relationship } from '@/lib/types';

export const metadata: Metadata = { title: 'Alertas de dor' };

type Alert = { patient: number; record: string; datetime: string; value: number; reason: 'threshold' | 'increase' };

export default async function AlertsPage() {
  const [alerts, relationships] = await Promise.all([
    api<Alert[]>('pain-record/alerts/'),
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'professional', discipline: 'physio', limit: 200 } }),
  ]);
  const byPatient = new Map(relationships.results.filter(r => r.patient).map(r => [r.patient!, r]));

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Alertas de dor</h1>
      <Card title="Últimos 14 dias">
        {alerts.length === 0 ? (
          <Empty title="Nenhum alerta">Os alertas usam o limite e o aumento de dor definidos em cada protocolo.</Empty>
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {alerts.map(alert => {
              const relationship = byPatient.get(alert.patient);
              return (
                <li key={alert.record} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div>
                    {relationship ? (
                      <Link href={`/pro/pacientes/${relationship.id}`} className="font-semibold underline">
                        {relationship.patient_name}
                      </Link>
                    ) : (
                      <span className="font-semibold">Paciente</span>
                    )}
                    <p className="text-sm text-gray-600">{dateTime(alert.datetime)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone="red">{alert.value}/10</Badge>
                    <span className="text-sm text-gray-600">{alert.reason === 'threshold' ? 'Acima do limite' : 'Aumentou após os exercícios'}</span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}

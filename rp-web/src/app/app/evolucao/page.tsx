import type { Metadata } from 'next';
import { Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { MOMENT_LABELS, date, dateTime, number } from '@/lib/format';
import type { Paginated } from '@/lib/types';

export const metadata: Metadata = { title: 'Evolução' };

type Assessment = { id: string; name: string; side: string; value: string | null; unit: string; date: string; kind: string };
type Pain = { id: string; datetime: string; moment: string; value: number; body_region: string };
type Water = { id: string; datetime: string; amount_ml: number };

export default async function ProgressPage() {
  const [assessments, pain, water] = await Promise.all([
    api<Paginated<Assessment>>('functional-assessment/', { query: { limit: 100, ordering: 'date' } }),
    api<Paginated<Pain>>('pain-record/', { query: { limit: 30 } }),
    api<Paginated<Water>>('water-log/', { query: { limit: 200 } }),
  ]);

  const byName = new Map<string, Assessment[]>();
  for (const a of assessments.results) {
    const key = `${a.name}${a.side ? ` (${a.side === 'left' ? 'esquerdo' : 'direito'})` : ''}`;
    byName.set(key, [...(byName.get(key) ?? []), a]);
  }

  const waterByDay = new Map<string, number>();
  for (const w of water.results) {
    const day = new Date(w.datetime).toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
    waterByDay.set(day, (waterByDay.get(day) ?? 0) + w.amount_ml);
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Evolução</h1>

      <Card title="Avaliações funcionais">
        {byName.size === 0 ? (
          <Empty title="Nenhuma avaliação registrada">Seu fisioterapeuta registra aqui amplitude, força e testes.</Empty>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {[...byName.entries()].map(([name, entries]) => {
              const sorted = [...entries].sort((a, b) => a.date.localeCompare(b.date));
              const max = Math.max(...sorted.map(e => Number(e.value ?? 0)), 1);
              return (
                <div key={name} className="rounded-xl border border-navy-100 p-4">
                  <p className="font-semibold">{name}</p>
                  <ul className="mt-3 flex flex-col gap-2">
                    {sorted.map(entry => (
                      <li key={entry.id} className="grid grid-cols-[5.5rem_1fr_4.5rem] items-center gap-2 text-sm">
                        <span className="tabular-nums text-gray-600">{date(entry.date)}</span>
                        <span className="h-2 rounded-full bg-navy-100">
                          <span className="block h-2 rounded-full bg-neon-600" style={{ width: `${(Number(entry.value ?? 0) / max) * 100}%` }} />
                        </span>
                        <span className="text-right font-semibold tabular-nums">
                          {number(entry.value, 1)} {entry.unit}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Registros de dor">
          {pain.results.length === 0 ? (
            <Empty title="Nenhum registro de dor" />
          ) : (
            <ul className="flex flex-col divide-y divide-navy-100 text-sm">
              {pain.results.map(record => (
                <li key={record.id} className="flex justify-between gap-2 py-2">
                  <span>
                    <span className="tabular-nums text-gray-600">{dateTime(record.datetime)}</span> · {MOMENT_LABELS[record.moment]}
                    {record.body_region && <span className="text-gray-500"> · {record.body_region}</span>}
                  </span>
                  <span className="font-semibold tabular-nums">{record.value}/10</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Água por dia">
          {waterByDay.size === 0 ? (
            <Empty title="Nenhum registro de água" />
          ) : (
            <ul className="flex flex-col divide-y divide-navy-100 text-sm">
              {[...waterByDay.entries()].map(([day, total]) => (
                <li key={day} className="flex justify-between py-2">
                  <span className="tabular-nums text-gray-600">{day}</span>
                  <span className="font-semibold tabular-nums">{number(total)} ml</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

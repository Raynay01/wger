import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { Badge, Button, Card, Empty, Field, inputClass, Notice } from '@/components/ui';
import { appointmentAction, scheduleAppointment } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { DISCIPLINE_LABELS } from '@/lib/brand';
import { KIND_LABELS, shiftDate } from '@/lib/format';
import { userZone } from '@/lib/userZone';
import { formatTime, todayIn, zonedToUtcIso } from '@/lib/zone';
import type { Paginated, Relationship } from '@/lib/types';

export const metadata: Metadata = { title: 'Agenda' };

type Appointment = {
  id: string;
  relationship: string;
  kind: string;
  status: 'scheduled' | 'done' | 'cancelled';
  start: string;
  duration_minutes: number;
  location: string;
  notes: string;
  discipline: string;
  professional: string;
  patient: string | null;
};

const STATUS = { scheduled: 'Marcada', done: 'Realizada', cancelled: 'Cancelada' };

function monday(date: string): string {
  const weekday = (new Date(`${date}T12:00:00Z`).getUTCDay() + 6) % 7;
  return shiftDate(date, -weekday);
}

export default async function ProfessionalAgendaPage({
  searchParams,
}: {
  searchParams: Promise<{ semana?: string; erro?: string; salvo?: string }>;
}) {
  const params = await searchParams;
  const zone = await userZone();
  const today = todayIn(zone);
  const week = monday(/^\d{4}-\d{2}-\d{2}$/.test(params.semana ?? '') ? params.semana! : today);
  const here = `/pro/agenda?semana=${week}`;

  const [appointments, relationships] = await Promise.all([
    api<Paginated<Appointment>>('appointment/', {
      query: {
        start__gte: zonedToUtcIso(`${week}T00:00`, zone),
        start__lt: zonedToUtcIso(`${shiftDate(week, 7)}T00:00`, zone),
        limit: 200,
      },
    }),
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'professional', limit: 200 } }),
  ]);
  const active = relationships.results.filter(r => r.status === 'active');
  const mine = appointments.results.filter(a => relationships.results.some(r => r.id === a.relationship));
  const byDay = new Map<string, Appointment[]>();
  for (const a of mine) {
    const day = new Intl.DateTimeFormat('en-CA', { timeZone: zone }).format(new Date(a.start));
    byDay.set(day, [...(byDay.get(day) ?? []), a]);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Agenda</h1>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <Link href={`/pro/agenda?semana=${shiftDate(week, -7)}`} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Semana anterior">
              ←
            </Link>
            <span className="tabular-nums text-gray-600">
              {week.split('-').reverse().join('/')} a {shiftDate(week, 6).split('-').reverse().join('/')}
            </span>
            <Link href={`/pro/agenda?semana=${shiftDate(week, 7)}`} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Próxima semana">
              →
            </Link>
          </div>
        </div>
      </div>
      <ErrorFromQuery erro={params.erro} />
      {params.salvo && <Notice tone="success">Consulta marcada. O paciente já vê na agenda dele.</Notice>}

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_22rem]">
        <Card title="Semana">
          <ol className="flex flex-col gap-4">
            {Array.from({ length: 7 }, (_, i) => shiftDate(week, i)).map(day => {
              const items = byDay.get(day) ?? [];
              const label = new Date(`${day}T12:00:00Z`).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: '2-digit', timeZone: 'UTC' });
              return (
                <li key={day}>
                  <p className={`text-sm font-semibold capitalize ${day === today ? 'text-neon-700' : 'text-navy-800'}`}>{label}</p>
                  {items.length === 0 ? (
                    <p className="text-sm text-gray-400">Livre</p>
                  ) : (
                    <ul className="mt-1 flex flex-col gap-2">
                      {items.map(a => (
                        <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-navy-100 p-3">
                          <div>
                            <p className="font-medium">
                              {formatTime(a.start, zone)} · {KIND_LABELS[a.kind]} · {a.patient}
                            </p>
                            <p className="text-xs text-gray-500">
                              {DISCIPLINE_LABELS[a.discipline]} · {a.duration_minutes} min{a.location && ` · ${a.location}`}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge tone={a.status === 'scheduled' ? 'neon' : a.status === 'done' ? 'navy' : 'gray'}>{STATUS[a.status]}</Badge>
                            {a.status === 'scheduled' &&
                              (
                                [
                                  ['done', 'Realizada'],
                                  ['cancel', 'Cancelar'],
                                ] as const
                              ).map(([action, text]) => (
                                <form key={action} action={appointmentAction}>
                                  <input type="hidden" name="back" value={here} />
                                  <input type="hidden" name="id" value={a.id} />
                                  <Button name="action" value={action} variant={action === 'cancel' ? 'danger' : 'ghost'} className="border border-navy-100">
                                    {text}
                                  </Button>
                                </form>
                              ))}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ol>
        </Card>

        <Card title="Marcar consulta">
          {active.length === 0 ? (
            <Empty title="Nenhum paciente ativo" />
          ) : (
            <form action={scheduleAppointment} className="flex flex-col gap-3">
              <input type="hidden" name="back" value={here} />
              <Field label="Paciente">
                <select name="relationship" className={inputClass}>
                  {active.map(r => (
                    <option key={r.id} value={r.id}>
                      {r.patient_name} · {DISCIPLINE_LABELS[r.discipline]}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Tipo">
                <select name="kind" className={inputClass}>
                  {Object.entries(KIND_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Data">
                  <input type="date" name="date" required defaultValue={today} className={inputClass} />
                </Field>
                <Field label="Horário">
                  <input type="time" name="time" required defaultValue="09:00" className={inputClass} />
                </Field>
              </div>
              <Field label="Duração (min)">
                <input name="duration_minutes" inputMode="numeric" defaultValue="60" className={inputClass} />
              </Field>
              <Field label="Local ou link (opcional)">
                <input name="location" maxLength={200} className={inputClass} />
              </Field>
              <Field label="Observações para o paciente (opcional)">
                <textarea name="notes" rows={2} className={inputClass} />
              </Field>
              <p className="text-xs text-gray-500">Horário no seu fuso: {zone}.</p>
              <Button type="submit" variant="secondary">
                Marcar
              </Button>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}

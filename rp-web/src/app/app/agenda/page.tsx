import type { Metadata } from 'next';
import Link from 'next/link';
import { revalidatePath } from 'next/cache';
import { Badge, Button, Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { PROFESSION_LABELS } from '@/lib/brand';
import { FOCUS_COLORS, FOCUS_LABELS, GOAL_LABELS, KIND_LABELS, shiftDate } from '@/lib/format';
import { PeriodizationTimeline } from '@/components/PeriodizationTimeline';
import { userZone } from '@/lib/userZone';
import { formatDateTime, formatTime, todayIn } from '@/lib/zone';
import type { Paginated, TrainingPlan } from '@/lib/types';

export const metadata: Metadata = { title: 'Agenda' };

type Appointment = {
  id: string;
  kind: string;
  status: string;
  start: string;
  duration_minutes: number;
  location: string;
  notes: string;
  discipline: string;
  professional: string;
};

type Day = {
  date: string;
  training: null | { routine: string; day: string; is_rest: boolean };
  phase: null | { plan: string; block: string; focus: string; week: number; weeks: number };
  nutrition: null | { plan: string; meals: number };
  physio: string[];
  appointments: Appointment[];
};

const FILTERS = [
  ['treino', 'Treino'],
  ['alimentacao', 'Alimentação'],
  ['fisio', 'Fisioterapia'],
  ['consultas', 'Consultas'],
] as const;

const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];

async function cancelAppointment(formData: FormData) {
  'use server';
  await api(`appointment/${formData.get('id')}/cancel/`, { method: 'POST' });
  revalidatePath('/app/agenda');
}

function monthStart(month: string): string {
  return `${month}-01`;
}

function addMonths(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1 + delta, 1));
  return date.toISOString().slice(0, 7);
}

export default async function AgendaPage({ searchParams }: { searchParams: Promise<{ mes?: string; ver?: string }> }) {
  const params = await searchParams;
  const zone = await userZone();
  const today = todayIn(zone);
  const month = /^\d{4}-\d{2}$/.test(params.mes ?? '') ? params.mes! : today.slice(0, 7);
  const shown = new Set((params.ver ?? 'treino,alimentacao,fisio,consultas').split(','));

  // Monday of the week of the 1st, six weeks
  const first = monthStart(month);
  const weekday = (new Date(`${first}T12:00:00Z`).getUTCDay() + 6) % 7;
  const start = shiftDate(first, -weekday);
  const end = shiftDate(start, 41);

  const [calendar, upcoming, periodizations] = await Promise.all([
    api<{ modules: string[]; days: Day[] }>('care/calendar/', { query: { start, end } }),
    api<Paginated<Appointment>>('appointment/', {
      query: { start__gte: new Date().toISOString(), status: 'scheduled', limit: 10 },
    }),
    api<Paginated<TrainingPlan>>('training-plan/', { query: { status: 'published', limit: 20 } }),
  ]);
  // The periodization running today, else the next one
  const periodization =
    periodizations.results.find(p => p.blocks.length && p.start <= today && (p.end ?? '') >= today) ??
    periodizations.results.filter(p => p.blocks.length && p.start > today).sort((a, b) => a.start.localeCompare(b.start))[0];

  const toggle = (key: string) => {
    const next = new Set(shown);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    return `/app/agenda?${new URLSearchParams({ mes: month, ver: [...next].join(',') || 'nenhum' })}`;
  };
  const rawLabel = new Date(`${first}T12:00:00Z`).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' });
  const monthLabel = rawLabel.charAt(0).toUpperCase() + rawLabel.slice(1);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-neon-700">Agenda</p>
          <h1 className="text-2xl font-bold">{monthLabel}</h1>
          <div className="mt-1 flex gap-2 text-sm">
            <Link href={`/app/agenda?mes=${addMonths(month, -1)}&ver=${params.ver ?? ''}`} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Mês anterior">
              ←
            </Link>
            <Link href={`/app/agenda?ver=${params.ver ?? ''}`} className="rounded-lg px-2 py-1 hover:bg-navy-100">
              Hoje
            </Link>
            <Link href={`/app/agenda?mes=${addMonths(month, 1)}&ver=${params.ver ?? ''}`} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Próximo mês">
              →
            </Link>
          </div>
        </div>
        <div className="flex flex-wrap gap-2" aria-label="Filtros">
          {FILTERS.map(([key, label]) => (
            <Link
              key={key}
              href={toggle(key)}
              aria-pressed={shown.has(key)}
              className={`rounded-full border px-3 py-1 text-sm ${shown.has(key) ? 'border-navy-900 bg-navy-900 text-white' : 'border-navy-100 bg-white text-navy-700'}`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      {periodization && shown.has('treino') && (
        <Card title={`Periodização: ${periodization.name} · ${GOAL_LABELS[periodization.goal]}`}>
          <PeriodizationTimeline blocks={periodization.blocks} today={today} />
        </Card>
      )}

      <div className="overflow-x-auto">
        <div className="grid min-w-[44rem] grid-cols-7 gap-px overflow-hidden rounded-2xl border border-navy-100 bg-navy-100">
          {WEEKDAYS.map(d => (
            <div key={d} className="bg-navy-900 px-2 py-1 text-center text-xs font-semibold uppercase text-navy-100">
              {d}
            </div>
          ))}
          {calendar.days.map((day, index) => {
            const previous = calendar.days[index - 1]?.phase;
            const phaseStarts = day.phase && (index % 7 === 0 || !previous || previous.week !== day.phase.week || previous.block !== day.phase.block);
            const inMonth = day.date.startsWith(month);
            const isToday = day.date === today;
            return (
              <div key={day.date} className={`min-h-28 p-2 text-xs ${inMonth ? 'bg-white' : 'bg-gray-50 text-gray-400'}`}>
                <p className={`mb-1 text-sm font-semibold ${isToday ? 'inline-grid size-6 place-items-center rounded-full bg-neon-500 text-navy-900' : ''}`}>
                  {Number(day.date.slice(8))}
                </p>
                <div className="flex flex-col gap-1">
                  {shown.has('treino') && day.phase && phaseStarts && (
                    <span className={`rounded px-1.5 py-0.5 font-medium ${FOCUS_COLORS[day.phase.focus] ?? ''}`} title={day.phase.plan}>
                      {day.phase.block || FOCUS_LABELS[day.phase.focus]} · sem. {day.phase.week}/{day.phase.weeks}
                    </span>
                  )}
                  {shown.has('consultas') &&
                    day.appointments.map(a => (
                      <span key={a.id} className="rounded bg-navy-900 px-1.5 py-0.5 text-white">
                        {formatTime(a.start, zone)} {KIND_LABELS[a.kind]}
                      </span>
                    ))}
                  {shown.has('treino') && day.training && (
                    <span className={`rounded px-1.5 py-0.5 ${day.training.is_rest ? 'bg-gray-100 text-gray-600' : 'bg-neon-100 text-neon-700'}`}>
                      {day.training.is_rest ? 'Descanso' : `Treino: ${day.training.day}`}
                    </span>
                  )}
                  {shown.has('alimentacao') && day.nutrition && (
                    <span className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-800">
                      {day.nutrition.meals} {day.nutrition.meals === 1 ? 'refeição' : 'refeições'}
                    </span>
                  )}
                  {shown.has('fisio') &&
                    day.physio.map(name => (
                      <span key={name} className="rounded bg-sky-50 px-1.5 py-0.5 text-sky-800">
                        Fisio: {name}
                      </span>
                    ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <Card title="Próximas consultas">
        {upcoming.results.length === 0 ? (
          <Empty title="Nenhuma consulta marcada" />
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {upcoming.results.map(a => (
              <li key={a.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-semibold capitalize">
                    {formatDateTime(a.start, zone)} · {KIND_LABELS[a.kind]}
                  </p>
                  <p className="text-sm text-gray-600">
                    {a.professional} · {PROFESSION_LABELS[a.discipline]} · {a.duration_minutes} min
                    {a.location && ` · ${a.location}`}
                  </p>
                  {a.notes && <p className="text-sm text-gray-700">{a.notes}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="neon">Marcada</Badge>
                  <form action={cancelAppointment}>
                    <input type="hidden" name="id" value={a.id} />
                    <Button variant="danger">Cancelar</Button>
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

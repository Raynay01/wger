import type { Metadata } from 'next';
import { Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { date, number } from '@/lib/format';
import type { Consistency, ConsistencyDay } from '@/lib/types';

export const metadata: Metadata = { title: 'Constância' };

// Same green as "Realizado" in the training charts
const DONE = '#008300';
const WEEKDAYS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom'];

type Mark = 'done' | 'open' | 'rest' | 'none' | 'future';

type Area = {
  key: string;
  label: string;
  module: string;
  mark: (day: ConsistencyDay) => Mark;
  describe: (day: ConsistencyDay) => string;
};

const AREAS: Area[] = [
  {
    key: 'training',
    label: 'Treino',
    module: 'training',
    mark: d => (d.training === 'done' ? 'done' : d.training === 'missed' ? 'open' : d.training === 'rest' ? 'rest' : d.training === 'planned' ? 'future' : 'none'),
    describe: d =>
      ({ done: 'treino feito', missed: 'treino previsto, sem registro', planned: 'treino previsto', rest: 'descanso', none: 'sem treino previsto' })[
        d.training ?? 'none'
      ],
  },
  {
    key: 'meals',
    label: 'Refeições registradas',
    module: 'nutrition',
    mark: d => (d.meals === null ? 'none' : d.meals ? 'done' : 'open'),
    describe: d => (d.meals === null ? 'sem plano alimentar' : d.meals ? 'refeições registradas' : 'nenhuma refeição registrada'),
  },
  {
    key: 'water',
    label: 'Meta de água',
    module: 'nutrition',
    mark: d => (d.water_goal === null ? 'none' : d.water_goal ? 'done' : 'open'),
    describe: d => (d.water_goal === null ? 'sem meta de água' : `${number(d.water_ml)} ml${d.water_goal ? ', meta atingida' : ''}`),
  },
  {
    key: 'physio',
    label: 'Fisioterapia',
    module: 'physio',
    mark: d => (d.physio === null ? 'none' : d.physio ? 'done' : 'open'),
    describe: d => (d.physio === null ? 'sem protocolo' : d.physio ? 'exercícios feitos' : 'nenhum exercício registrado'),
  },
];

function Cell({ mark, label }: { mark: Mark; label: string }) {
  const base = 'flex h-5 w-5 items-center justify-center rounded text-[10px] leading-none';
  const styles: Record<Mark, string> = {
    done: base,
    open: `${base} border border-gray-400 bg-white`,
    rest: `${base} bg-gray-200 text-gray-500`,
    none: `${base} border border-dashed border-gray-200`,
    future: `${base} border border-gray-200 bg-white`,
  };
  return (
    <span {...(label ? { role: 'img', 'aria-label': label, title: label } : { 'aria-hidden': true })} className={styles[mark]} style={mark === 'done' ? { background: DONE } : undefined}>
      {mark === 'rest' ? '–' : ''}
    </span>
  );
}

function AreaGrid({ area, consistency }: { area: Area; consistency: Consistency }) {
  const weeks = consistency.weeks.map((_, index) => consistency.days.slice(index * 7, index * 7 + 7));
  return (
    <div>
      <p className="mb-2 text-sm font-semibold text-navy-900">{area.label}</p>
      <div className="flex gap-1">
        <div className="flex flex-col gap-1 pr-1 text-[10px] leading-5 text-gray-500">
          {WEEKDAYS.map(day => (
            <span key={day}>{day}</span>
          ))}
        </div>
        {weeks.map(week => (
          <div key={week[0].date} className="flex flex-col gap-1">
            {week.map(day => {
              const future = day.date > consistency.today;
              const mark = future ? (area.mark(day) === 'none' ? 'none' : 'future') : area.mark(day);
              return <Cell key={day.date} mark={mark} label={`${area.label}, ${date(day.date)}: ${area.describe(day)}`} />;
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default async function ConsistencyPage() {
  const consistency = await api<Consistency>('care/consistency/', { query: { weeks: 8 } });
  const areas = AREAS.filter(area => consistency.modules.includes(area.module));
  const current = consistency.weeks[consistency.weeks.length - 1];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Constância</h1>
        <p className="text-sm text-gray-600">O que você registrou nas últimas 8 semanas. Conta o registro, não a quantidade.</p>
      </div>

      {areas.length === 0 ? (
        <Empty title="Nada para acompanhar ainda">Quando um profissional publicar seu treino, plano alimentar ou protocolo, a constância aparece aqui.</Empty>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-[14rem_1fr]">
            <div className="rounded-2xl bg-navy-900 p-4 text-white">
              <p className="text-sm text-navy-100">Sequência</p>
              <p className="mt-1 text-4xl font-bold tabular-nums text-neon-500">
                {consistency.streak} {consistency.streak === 1 ? 'dia' : 'dias'}
              </p>
              <p className="mt-1 text-xs text-navy-100">seguidos com algum registro. Dias de descanso do treino não quebram a sequência.</p>
            </div>
            <Card title={`Esta semana (${date(current.start)} a ${date(current.end)})`}>
              <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                {consistency.modules.includes('training') && (
                  <div>
                    <dt className="text-gray-600">Treinos</dt>
                    <dd className="text-xl font-bold tabular-nums">
                      {current.training_done} de {current.training_planned}
                    </dd>
                  </div>
                )}
                {consistency.modules.includes('nutrition') && (
                  <>
                    <div>
                      <dt className="text-gray-600">Dias com refeições registradas</dt>
                      <dd className="text-xl font-bold tabular-nums">{current.meals_days}</dd>
                    </div>
                    <div>
                      <dt className="text-gray-600">Dias com a meta de água</dt>
                      <dd className="text-xl font-bold tabular-nums">{current.water_goal_days}</dd>
                    </div>
                  </>
                )}
                {consistency.modules.includes('physio') && (
                  <div>
                    <dt className="text-gray-600">Dias com fisioterapia</dt>
                    <dd className="text-xl font-bold tabular-nums">{current.physio_days}</dd>
                  </div>
                )}
              </dl>
            </Card>
          </div>

          <Card title="Dia a dia">
            <div className="flex flex-wrap gap-x-10 gap-y-6">
              {areas.map(area => (
                <AreaGrid key={area.key} area={area} consistency={consistency} />
              ))}
            </div>
            <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-xs text-gray-600" aria-label="Legenda">
              <li className="flex items-center gap-1.5">
                <Cell mark="done" label="" /> Feito
              </li>
              <li className="flex items-center gap-1.5">
                <Cell mark="open" label="" /> Sem registro
              </li>
              <li className="flex items-center gap-1.5">
                <Cell mark="rest" label="" /> Descanso do treino
              </li>
              <li className="flex items-center gap-1.5">
                <Cell mark="none" label="" /> Nada previsto
              </li>
            </ul>
            <p className="mt-2 text-xs text-gray-500">Cada coluna é uma semana, de segunda a domingo. Passe o mouse em um dia para ver o detalhe.</p>

            <details className="mt-4 text-sm">
              <summary className="cursor-pointer font-semibold text-navy-700">Ver como tabela</summary>
              <div className="mt-2 overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="text-xs uppercase text-gray-500">
                    <tr>
                      <th className="py-2">Semana</th>
                      {consistency.modules.includes('training') && <th className="text-right">Treinos</th>}
                      {consistency.modules.includes('nutrition') && (
                        <>
                          <th className="text-right">Refeições</th>
                          <th className="text-right">Meta de água</th>
                        </>
                      )}
                      {consistency.modules.includes('physio') && <th className="text-right">Fisioterapia</th>}
                      <th className="text-right">Dias com registro</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-100">
                    {consistency.weeks.map(week => (
                      <tr key={week.start}>
                        <td className="py-1.5 tabular-nums">
                          {date(week.start)} a {date(week.end)}
                        </td>
                        {consistency.modules.includes('training') && (
                          <td className="text-right tabular-nums">
                            {week.training_done} de {week.training_planned}
                          </td>
                        )}
                        {consistency.modules.includes('nutrition') && (
                          <>
                            <td className="text-right tabular-nums">{week.meals_days} dias</td>
                            <td className="text-right tabular-nums">{week.water_goal_days} dias</td>
                          </>
                        )}
                        {consistency.modules.includes('physio') && <td className="text-right tabular-nums">{week.physio_days} dias</td>}
                        <td className="text-right tabular-nums">{week.recorded_days}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </Card>
        </>
      )}
    </div>
  );
}

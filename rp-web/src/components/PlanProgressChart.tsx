'use client';

import { useState } from 'react';
import { FOCUS_LABELS, date, muscleLabel, number } from '@/lib/format';
import type { PlanProgress, ProgressBlock, ProgressSummary } from '@/lib/types';

// Validated pair (light surface): blue for planned, green for done
const PLANNED = '#2a78d6';
const DONE = '#008300';

const MEASURES = {
  sets: { label: 'Séries', unit: 'séries', planned: 'planned_sets', done: 'done_sets' },
  sessions: { label: 'Sessões', unit: 'sessões', planned: 'planned_sessions', done: 'done_sessions' },
  load: { label: 'Tonelagem', unit: 'kg', planned: 'planned_load', done: 'done_load' },
} as const;

type Measure = keyof typeof MEASURES;

function values(summary: ProgressSummary, measure: Measure): [number, number] {
  const m = MEASURES[measure];
  return [summary[m.planned], summary[m.done]];
}

function percent(planned: number, done: number): string {
  return planned > 0 ? `${Math.round((done / planned) * 100)}%` : '–';
}

/** Weekly sets per muscle of a block: target, the routine's weekly average and what was done each week */
function MuscleSets({ block, today }: { block: ProgressBlock; today: string }) {
  return (
    <div className="overflow-x-auto">
      <p className="mb-1 text-sm font-semibold text-navy-900">{block.name || FOCUS_LABELS[block.focus]}: séries por semana</p>
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-gray-500">
          <tr>
            <th className="py-1.5">Músculo</th>
            <th className="text-right">Meta</th>
            <th className="text-right">No treino</th>
            {block.weeks.map(week => (
              <th key={week.week} className="text-right" title={`${date(week.start)} a ${date(week.end)}`}>
                S{week.week}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-100">
          {block.muscles.map((muscle, index) => {
            const planned = muscle.planned_sets / block.weeks.length;
            return (
              <tr key={muscle.muscle}>
                <td className="py-1.5">{muscleLabel(muscle.name)}</td>
                <td className="text-right tabular-nums">{muscle.weekly_sets}</td>
                <td className="text-right tabular-nums">
                  {number(planned, 1)}
                  {planned < muscle.weekly_sets && <span className="block text-xs text-gray-500">abaixo da meta</span>}
                </td>
                {block.weeks.map(week => {
                  const done = week.muscles[index].done_sets;
                  const reached = done >= muscle.weekly_sets;
                  return (
                    <td key={week.week} className="text-right tabular-nums">
                      {week.start > today ? (
                        <span className="text-gray-400">–</span>
                      ) : (
                        <>
                          {number(done)}
                          {reached && (
                            <span className="ml-0.5 font-semibold text-navy-900" title="Meta atingida">
                              ✓<span className="sr-only"> meta atingida</span>
                            </span>
                          )}
                        </>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Planned versus done per week of a periodization, one measure at a time */
export function PlanProgressChart({ progress, today }: { progress: PlanProgress; today: string }) {
  const [measure, setMeasure] = useState<Measure>('sets');
  const [hover, setHover] = useState<string | null>(null);
  const m = MEASURES[measure];
  const weeks = progress.blocks.flatMap(block => block.weeks.map(week => ({ block, week })));
  if (weeks.length === 0) {
    return null;
  }
  const max = Math.max(1, ...weeks.flatMap(({ week }) => values(week, measure)));
  const elapsed = progress.blocks.filter(block => block.start <= today);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="radiogroup" aria-label="Medida" className="flex rounded-xl border border-navy-100 p-0.5 text-sm">
          {(Object.keys(MEASURES) as Measure[]).map(key => (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={measure === key}
              onClick={() => setMeasure(key)}
              className={`rounded-lg px-3 py-1 ${measure === key ? 'bg-navy-900 font-semibold text-white' : 'text-navy-700 hover:bg-navy-100'}`}
            >
              {MEASURES[key].label}
            </button>
          ))}
        </div>
        <ul className="flex gap-4 text-sm text-navy-900" aria-label="Legenda">
          <li className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: PLANNED }} /> Planejado
          </li>
          <li className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-sm" style={{ background: DONE }} /> Realizado
          </li>
        </ul>
      </div>

      <div className="overflow-x-auto">
        <div className="flex min-w-max items-end gap-4">
          {progress.blocks.map(block => (
            <div key={block.id} className="flex flex-col gap-1">
              <div className="relative flex h-40 items-end gap-2 border-b border-gray-300">
                {block.planned_sessions === 0 && block.done_sessions === 0 && (
                  <span className="absolute inset-x-0 bottom-2 text-center text-xs text-gray-500">Sem treino ligado</span>
                )}
                {block.weeks.map(week => {
                  const [planned, done] = values(week, measure);
                  const future = week.start > today;
                  const key = `${block.id}-${week.week}`;
                  const label = `${block.name || FOCUS_LABELS[block.focus]} · semana ${week.week} (${date(week.start)} a ${date(week.end)}): planejado ${number(planned)} ${m.unit}, realizado ${future ? '–' : `${number(done)} ${m.unit}`}`;
                  return (
                    <div
                      key={key}
                      className="relative flex h-full w-9 cursor-default items-end justify-center gap-0.5"
                      aria-label={label}
                      role="img"
                      tabIndex={0}
                      onMouseEnter={() => setHover(key)}
                      onMouseLeave={() => setHover(null)}
                      onFocus={() => setHover(key)}
                      onBlur={() => setHover(null)}
                    >
                      <span className="block w-3 rounded-t" style={{ height: `${(planned / max) * 100}%`, background: PLANNED, opacity: future ? 0.35 : 1 }} />
                      <span
                        className="block w-3 rounded-t"
                        style={{ height: future ? 0 : `${(done / max) * 100}%`, background: DONE }}
                      />
                      {hover === key && (
                        <span className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 w-56 -translate-x-1/2 rounded-lg bg-navy-900 px-3 py-2 text-xs text-white shadow-lg">
                          <span className="block font-semibold">
                            Semana {week.week} · {date(week.start)} a {date(week.end)}
                          </span>
                          <span className="block">
                            Planejado: {number(planned)} {m.unit}
                          </span>
                          <span className="block">
                            Realizado: {future ? 'semana futura' : `${number(done)} ${m.unit} (${percent(planned, done)})`}
                          </span>
                          {!future && week.average_rir && <span className="block">RIR médio {number(week.average_rir, 1)}</span>}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-2 text-center text-xs text-gray-500">
                {block.weeks.map(week => (
                  <span key={week.week} className={`w-9 ${week.start > today ? 'text-gray-400' : ''}`}>
                    S{week.week}
                  </span>
                ))}
              </div>
              <p className="max-w-[12rem] truncate text-xs font-semibold text-navy-900">{block.name || FOCUS_LABELS[block.focus]}</p>
            </div>
          ))}
        </div>
      </div>

      {weeks.some(({ week }) => week.start > today) && (
        <p className="-mt-2 text-xs text-gray-500">Semanas que ainda não começaram aparecem em tom claro, só com o planejado.</p>
      )}

      {elapsed.length > 0 && (
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {elapsed.map(block => {
            const [planned, done] = values(block, measure);
            return (
              <li key={block.id} className="rounded-xl bg-navy-100/50 p-3">
                <p className="font-semibold">{block.name || FOCUS_LABELS[block.focus]}</p>
                <p className="text-gray-700">
                  {number(done)} de {number(planned)} {m.unit} ({percent(planned, done)})
                  {block.average_rir && ` · RIR médio ${number(block.average_rir, 1)}`}
                  {block.average_rpe && ` · RPE médio ${number(block.average_rpe, 1)}`}
                </p>
                {(block.intensity || block.volume) && (
                  <p className="text-xs text-gray-500">Meta: {[block.intensity, block.volume].filter(Boolean).join(' · ')}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {progress.blocks.some(block => block.muscles.length > 0) && (
        <div className="flex flex-col gap-4 border-t border-navy-100 pt-4">
          {progress.blocks
            .filter(block => block.muscles.length > 0)
            .map(block => (
              <MuscleSets key={block.id} block={block} today={today} />
            ))}
          <p className="-mt-2 text-xs text-gray-500">
            Séries realizadas por semana. Cada série conta para os músculos principais do exercício; ✓ quando a semana atingiu a meta. &quot;No treino&quot; é a média semanal do
            treino ligado à fase.
          </p>
        </div>
      )}

      <details className="text-sm">
        <summary className="cursor-pointer font-semibold text-navy-700">Ver como tabela</summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2">Fase</th>
                <th>Semana</th>
                <th className="text-right">Sessões</th>
                <th className="text-right">Séries</th>
                <th className="text-right">Tonelagem (kg)</th>
                <th className="text-right">RIR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-100">
              {weeks.map(({ block, week }) => (
                <tr key={`${block.id}-${week.week}`}>
                  <td className="py-1.5">{block.name || FOCUS_LABELS[block.focus]}</td>
                  <td className="tabular-nums">
                    {week.week} · {date(week.start)}
                  </td>
                  <td className="text-right tabular-nums">
                    {number(week.done_sessions)} / {number(week.planned_sessions)}
                  </td>
                  <td className="text-right tabular-nums">
                    {number(week.done_sets)} / {number(week.planned_sets)}
                  </td>
                  <td className="text-right tabular-nums">
                    {number(week.done_load)} / {number(week.planned_load)}
                  </td>
                  <td className="text-right tabular-nums">{number(week.average_rir, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-xs text-gray-500">Realizado / planejado.</p>
        </div>
      </details>
    </div>
  );
}

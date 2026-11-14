import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { PeriodizationTimeline } from '@/components/PeriodizationTimeline';
import { PlanProgressChart } from '@/components/PlanProgressChart';
import { PrescriptionHeader } from '@/components/PrescriptionHeader';
import { Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { addTrainingBlock, deleteTrainingBlock, updateTrainingPlan } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { FOCUS_COLORS, FOCUS_LABELS, GOAL_LABELS, STATUS_LABELS, date, muscleLabel } from '@/lib/format';
import type { Muscle, Paginated, PlanProgress, TrainingPlan } from '@/lib/types';
import { userZone } from '@/lib/userZone';
import { todayIn } from '@/lib/zone';

export const metadata: Metadata = { title: 'Periodização' };

type RoutineOption = { id: number; name: string; version: number; status: string; start: string; end: string };

export default async function PeriodizationBuilderPage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string; id: string }>;
  searchParams: Promise<{ erro?: string }>;
}) {
  const { rel, id } = await params;
  const { erro } = await searchParams;
  const [plan, routines, muscleList] = await Promise.all([
    api<TrainingPlan>(`training-plan/${id}/`),
    api<Paginated<RoutineOption>>('routine/', { query: { care_relationship: rel, limit: 100 } }),
    api<Paginated<Muscle>>('muscle/', { query: { limit: 100 } }),
  ]);
  const muscles = muscleList.results
    .map(m => ({ id: m.id, label: muscleLabel(m.name) }))
    .sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'));
  const muscleName = new Map(muscles.map(m => [m.id, m.label]));
  const versions = plan.lineage_id
    ? (await api<Paginated<TrainingPlan>>('training-plan/', { query: { lineage_id: plan.lineage_id, limit: 100 } })).results
    : [plan];
  const editable = plan.status === 'draft';
  const progress = !editable && plan.blocks.length > 0 ? await api<PlanProgress>(`training-plan/${id}/progress/`) : null;
  const here = `/pro/pacientes/${rel}/periodizacao/${id}`;
  const today = todayIn(await userZone());
  const routineChoices = routines.results.filter(r => r.status === 'published' || r.status === 'draft');

  return (
    <div className="flex flex-col gap-6">
      <PrescriptionHeader kind="periodization" relationship={rel} prescription={plan} title={plan.name} versions={versions} path="periodizacao" back={here} />
      <ErrorFromQuery erro={erro} />

      <Card title={`Linha do tempo · ${GOAL_LABELS[plan.goal]}`}>
        {plan.blocks.length === 0 ? (
          <Empty title="Nenhuma fase ainda">Adicione os mesociclos na ordem em que acontecem.</Empty>
        ) : (
          <PeriodizationTimeline blocks={plan.blocks} today={today} />
        )}
      </Card>

      {progress && (
        <Card title="Planejado x realizado">
          <PlanProgressChart progress={progress} today={today} />
        </Card>
      )}

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_22rem]">
        <Card title="Fases (mesociclos)">
          {plan.blocks.length === 0 ? (
            <Empty title="Nenhuma fase ainda" />
          ) : (
            <ol className="flex flex-col gap-3">
              {plan.blocks.map((block, index) => (
                <li key={block.id} className="rounded-xl border border-navy-100 p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <p className="font-semibold">
                      {index + 1}. {block.name || FOCUS_LABELS[block.focus]}{' '}
                      <span className={`ml-1 rounded px-1.5 py-0.5 text-xs font-medium ${FOCUS_COLORS[block.focus]}`}>{FOCUS_LABELS[block.focus]}</span>
                    </p>
                    <span className="text-sm text-gray-600">
                      {date(block.start)} a {date(block.end)} · {block.weeks} {block.weeks === 1 ? 'semana' : 'semanas'}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-700">
                    {[block.current_routine_name && `Treino: ${block.current_routine_name}`, block.intensity && `Intensidade: ${block.intensity}`, block.volume && `Volume: ${block.volume}`]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  {block.weekly_sets.length > 0 && (
                    <p className="mt-1 text-sm text-gray-700">
                      Séries por semana: {block.weekly_sets.map(t => `${muscleName.get(t.muscle) ?? t.muscle} ${t.sets}`).join(' · ')}
                    </p>
                  )}
                  {block.notes && <p className="mt-1 text-sm text-gray-600">{block.notes}</p>}
                  {editable && (
                    <form action={deleteTrainingBlock} className="mt-1 text-right">
                      <input type="hidden" name="back" value={here} />
                      <input type="hidden" name="id" value={block.id} />
                      <Button variant="ghost">Remover</Button>
                    </form>
                  )}
                </li>
              ))}
            </ol>
          )}
        </Card>

        {editable ? (
          <div className="flex flex-col gap-6">
            <Card title="Adicionar fase">
              <form action={addTrainingBlock} className="flex flex-col gap-3">
                <input type="hidden" name="back" value={here} />
                <input type="hidden" name="plan" value={plan.id} />
                <input type="hidden" name="order" value={plan.blocks.length + 1} />
                <Field label="Foco">
                  <select name="focus" className={inputClass}>
                    {Object.entries(FOCUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Semanas">
                    <input name="weeks" inputMode="numeric" required defaultValue="4" className={inputClass} />
                  </Field>
                  <Field label="Nome (opcional)">
                    <input name="name" maxLength={100} placeholder="Ex.: Base" className={inputClass} />
                  </Field>
                </div>
                <Field label="Treino desta fase (opcional)">
                  <select name="routine" className={inputClass} defaultValue="">
                    <option value="">Nenhum</option>
                    {routineChoices.map(r => (
                      <option key={r.id} value={r.id}>
                        {r.name} · v{r.version} ({STATUS_LABELS[r.status]})
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Intensidade (opcional)">
                  <input name="intensity" maxLength={100} placeholder="Ex.: 70-80% 1RM, RIR 2-3" className={inputClass} />
                </Field>
                <Field label="Volume (opcional)">
                  <input name="volume" maxLength={100} placeholder="Ex.: 12-16 séries por grupo/semana" className={inputClass} />
                </Field>
                <details className="rounded-xl border border-navy-100 p-3">
                  <summary className="cursor-pointer text-sm font-semibold text-navy-700">Séries por semana por músculo (opcional)</summary>
                  <p className="mt-2 text-xs text-gray-500">
                    Meta para comparar com o treino e com o que o aluno registrar. Conta as séries dos exercícios em que o músculo é o principal.
                  </p>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {muscles.map(m => (
                      <Field key={m.id} label={m.label}>
                        <input name={`sets_${m.id}`} type="number" min={1} max={60} className={inputClass} />
                      </Field>
                    ))}
                  </div>
                </details>
                <Field label="Observações (opcional)">
                  <textarea name="notes" rows={2} className={inputClass} />
                </Field>
                <Button type="submit" variant="secondary">
                  Adicionar fase
                </Button>
              </form>
            </Card>

            <Card title="Dados da periodização">
              <form action={updateTrainingPlan} className="flex flex-col gap-3">
                <input type="hidden" name="back" value={here} />
                <input type="hidden" name="id" value={plan.id} />
                <Field label="Nome">
                  <input name="name" required maxLength={100} defaultValue={plan.name} className={inputClass} />
                </Field>
                <Field label="Objetivo">
                  <select name="goal" defaultValue={plan.goal} className={inputClass}>
                    {Object.entries(GOAL_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Início da primeira fase">
                  <input type="date" name="start" required defaultValue={plan.start} className={inputClass} />
                </Field>
                <Field label="Descrição (opcional)">
                  <textarea name="description" rows={2} defaultValue={plan.description} className={inputClass} />
                </Field>
                <Button type="submit" variant="ghost" className="border border-navy-100">
                  Salvar
                </Button>
              </form>
            </Card>
          </div>
        ) : (
          plan.description && (
            <Card title="Descrição">
              <p className="text-sm text-gray-700">{plan.description}</p>
            </Card>
          )
        )}
      </div>
    </div>
  );
}

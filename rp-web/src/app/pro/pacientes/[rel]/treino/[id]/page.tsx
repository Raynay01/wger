import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { PrescriptionHeader } from '@/components/PrescriptionHeader';
import { SearchPicker } from '@/components/SearchPicker';
import { Badge, Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { addDay, addExerciseToDay, deleteDay, deleteSlot } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { exerciseNames } from '@/lib/catalog';
import { date, number } from '@/lib/format';
import type { Paginated, Routine } from '@/lib/types';

export const metadata: Metadata = { title: 'Treino' };

type Config = { iteration: number; value: string };
type Entry = {
  id: number;
  exercise: number;
  comment: string;
  tempo: string;
  rpe: string | null;
  range_of_motion: string;
  set_nr_configs: Config[];
  repetitions_configs: Config[];
  weight_configs: Config[];
  rir_configs: Config[];
  rest_configs: Config[];
};
type Structure = Routine & {
  days: { id: number; order: number; name: string; is_rest: boolean; slots: { id: number; order: number; entries: Entry[] }[] }[];
};

function first(configs: Config[]): string | null {
  const config = [...configs].sort((a, b) => a.iteration - b.iteration)[0];
  return config ? config.value : null;
}

function describe(entry: Entry): string {
  const sets = first(entry.set_nr_configs);
  const reps = first(entry.repetitions_configs);
  const weight = first(entry.weight_configs);
  const rir = first(entry.rir_configs);
  const rest = first(entry.rest_configs);
  return [
    sets && reps ? `${number(sets)} × ${number(reps)}` : sets ? `${number(sets)} séries` : reps ? `${number(reps)} reps` : null,
    weight && `${number(weight, 1)} kg`,
    rir && `RIR ${number(rir, 1)}`,
    entry.rpe && `RPE ${number(entry.rpe, 1)}`,
    entry.tempo && `cadência ${entry.tempo}`,
    entry.range_of_motion && `amplitude ${entry.range_of_motion}`,
    rest && `descanso ${number(rest)} s`,
  ]
    .filter(Boolean)
    .join(' · ');
}

export default async function RoutineBuilderPage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string; id: string }>;
  searchParams: Promise<{ erro?: string }>;
}) {
  const { rel, id } = await params;
  const { erro } = await searchParams;
  const [routine, structure, names] = await Promise.all([
    api<Routine>(`routine/${id}/`),
    api<Structure>(`routine/${id}/structure/`),
    exerciseNames(),
  ]);
  const versions = routine.lineage_id
    ? (await api<Paginated<Routine>>('routine/', { query: { lineage_id: routine.lineage_id, limit: 100 } })).results
    : [routine];
  const editable = routine.status === 'draft';
  const here = `/pro/pacientes/${rel}/treino/${id}`;
  const days = [...structure.days].sort((a, b) => a.order - b.order);

  return (
    <div className="flex flex-col gap-6">
      <PrescriptionHeader kind="training" relationship={rel} prescription={routine} title={routine.name} versions={versions} path="treino" back={here} />
      <ErrorFromQuery erro={erro} />
      <p className="text-sm text-gray-600">
        Período: {date(routine.start)} a {date(routine.end)}. Os dias se repetem em ciclo, na ordem abaixo.
      </p>

      {days.length === 0 && <Empty title="Nenhum dia no ciclo ainda" />}

      <div className="grid items-start gap-4 lg:grid-cols-2">
        {days.map((day, index) => (
          <Card
            key={day.id}
            title={
              <span>
                Dia {index + 1} · {day.is_rest ? 'Descanso' : day.name}
              </span>
            }
            action={
              editable ? (
                <form action={deleteDay}>
                  <input type="hidden" name="back" value={here} />
                  <input type="hidden" name="id" value={day.id} />
                  <Button variant="ghost">Remover</Button>
                </form>
              ) : day.is_rest ? (
                <Badge tone="gray">Descanso</Badge>
              ) : null
            }
          >
            {!day.is_rest && (
              <>
                <ol className="flex flex-col divide-y divide-navy-100">
                  {day.slots
                    .sort((a, b) => a.order - b.order)
                    .map(slot =>
                      slot.entries.map(entry => (
                        <li key={entry.id} className="flex items-start justify-between gap-2 py-2">
                          <div>
                            <p className="font-medium">{names.get(entry.exercise) ?? `Exercício ${entry.exercise}`}</p>
                            <p className="text-sm text-gray-600">{describe(entry) || 'Sem dosagem definida'}</p>
                            {entry.comment && <p className="text-xs text-gray-500">{entry.comment}</p>}
                          </div>
                          {editable && (
                            <form action={deleteSlot}>
                              <input type="hidden" name="back" value={here} />
                              <input type="hidden" name="id" value={slot.id} />
                              <button className="text-gray-400 hover:text-red-700" aria-label="Remover exercício">
                                ×
                              </button>
                            </form>
                          )}
                        </li>
                      )),
                    )}
                </ol>
                {editable && (
                  <details className="mt-3 border-t border-navy-100 pt-3">
                    <summary className="cursor-pointer text-sm font-semibold text-navy-700">+ Adicionar exercício</summary>
                    <form action={addExerciseToDay} className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <input type="hidden" name="back" value={here} />
                      <input type="hidden" name="day" value={day.id} />
                      <input type="hidden" name="order" value={day.slots.length + 1} />
                      <div className="col-span-2 sm:col-span-4">
                        <SearchPicker kind="exercise" name="exercise" label="Exercício" placeholder="Ex.: agachamento, squat" />
                      </div>
                      <Field label="Séries">
                        <input name="sets" inputMode="numeric" defaultValue="3" className={inputClass} />
                      </Field>
                      <Field label="Repetições">
                        <input name="repetitions" inputMode="numeric" defaultValue="10" className={inputClass} />
                      </Field>
                      <Field label="Carga (kg)">
                        <input name="weight" inputMode="decimal" className={inputClass} />
                      </Field>
                      <Field label="Descanso (s)">
                        <input name="rest" inputMode="numeric" defaultValue="90" className={inputClass} />
                      </Field>
                      <Field label="RIR">
                        <input name="rir" inputMode="decimal" className={inputClass} />
                      </Field>
                      <Field label="RPE">
                        <input name="rpe" inputMode="decimal" className={inputClass} />
                      </Field>
                      <Field label="Cadência">
                        <input name="tempo" maxLength={15} placeholder="3-1-1-0" className={inputClass} />
                      </Field>
                      <Field label="Amplitude">
                        <input name="range_of_motion" maxLength={50} placeholder="completa" className={inputClass} />
                      </Field>
                      <div className="col-span-2 sm:col-span-4">
                        <Field label="Orientação">
                          <input name="comment" maxLength={100} className={inputClass} />
                        </Field>
                      </div>
                      <div className="col-span-2 sm:col-span-4">
                        <Button type="submit" variant="secondary">
                          Adicionar
                        </Button>
                      </div>
                    </form>
                  </details>
                )}
              </>
            )}
          </Card>
        ))}
      </div>

      {editable && (
        <Card title="Adicionar dia ao ciclo">
          <form action={addDay} className="flex flex-wrap items-end gap-3">
            <input type="hidden" name="back" value={here} />
            <input type="hidden" name="routine" value={id} />
            <input type="hidden" name="order" value={days.length + 1} />
            <Field label="Nome do dia">
              <input name="name" maxLength={20} placeholder="Ex.: Pernas" className={inputClass} />
            </Field>
            <label className="flex items-center gap-2 pb-2 text-sm">
              <input type="checkbox" name="is_rest" /> Dia de descanso
            </label>
            <Button type="submit" variant="secondary">
              Adicionar dia
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { Badge, Button, Card, Empty, Meter } from '@/components/ui';
import { api } from '@/lib/api';
import { exerciseNames } from '@/lib/catalog';
import { ADHERENCE_LABELS, LOCATION_LABELS, MOMENT_LABELS, number, shiftDate, time, weekday } from '@/lib/format';
import type { MyDay } from '@/lib/types';
import { addWater, logPrescribedMeal, recordExercise, setAdherence } from './actions';
import { PainForm } from './PainForm';

export const metadata: Metadata = { title: 'Meu Dia' };

type View = 'ambos' | 'treino' | 'alimentacao';

export default async function MyDayPage({ searchParams }: { searchParams: Promise<{ data?: string; ver?: View }> }) {
  const params = await searchParams;
  const day = await api<MyDay>('care/my-day/', { query: { date: params.data } });
  const view: View = day.combined_view ? (params.ver ?? 'ambos') : 'ambos';
  const showTraining = day.training && view !== 'alimentacao';
  const showNutrition = day.nutrition && view !== 'treino';
  const twoColumns = showTraining && showNutrition;

  const link = (changes: Record<string, string>) => {
    const query = new URLSearchParams({ data: day.date, ...(params.ver ? { ver: params.ver } : {}), ...changes });
    return `/app?${query}`;
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-neon-700">Meu Dia</p>
          <h1 className="text-2xl font-bold capitalize">{weekday(day.date)}</h1>
          <div className="mt-1 flex items-center gap-2 text-sm">
            <Link href={link({ data: shiftDate(day.date, -1) })} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Dia anterior">
              ←
            </Link>
            <span className="tabular-nums text-gray-600">{day.date.split('-').reverse().join('/')}</span>
            <Link href={link({ data: shiftDate(day.date, 1) })} className="rounded-lg px-2 py-1 hover:bg-navy-100" aria-label="Próximo dia">
              →
            </Link>
          </div>
        </div>

        {day.combined_view && (
          <div role="tablist" aria-label="Visualização" className="flex rounded-xl bg-navy-100 p-1 text-sm">
            {(
              [
                ['ambos', 'Treino + alimentação'],
                ['treino', 'Só treino'],
                ['alimentacao', 'Só alimentação'],
              ] as const
            ).map(([value, label]) => (
              <Link
                key={value}
                role="tab"
                aria-selected={view === value}
                href={link({ ver: value })}
                className={`rounded-lg px-3 py-1.5 font-medium ${view === value ? 'bg-white shadow-sm' : 'text-navy-700'}`}
              >
                {label}
              </Link>
            ))}
          </div>
        )}
      </div>

      {day.mode === 'self' && (
        <p className="text-sm text-gray-600">
          Você ainda não é acompanhado por um profissional. Quando aceitar um convite, o Meu Dia mostra o que ele prescreveu.{' '}
          <Link href="/app/convites" className="font-semibold text-navy-700 underline">
            Ver convites
          </Link>
        </p>
      )}

      <div className={`grid items-start gap-6 ${twoColumns ? "lg:grid-cols-2" : ""}`}>
        {showTraining && <TrainingSection day={day} />}
        {showNutrition && <NutritionSection day={day} />}
      </div>

      {day.physio && view === 'ambos' && <PhysioSection day={day} />}
    </div>
  );
}

async function TrainingSection({ day }: { day: MyDay }) {
  const training = day.training!;
  if (!training.routine) {
    return (
      <Card title="Treino do dia">
        <Empty title="Nenhum treino ativo">
          {day.mode === 'guided' ? 'Seu profissional ainda está preparando o seu treino.' : 'Monte um treino no app ou aguarde um profissional.'}
        </Empty>
      </Card>
    );
  }
  const names = await exerciseNames();
  const workout = training.day?.day;

  return (
    <Card
      title={`Treino · ${training.routine.name}`}
      action={training.session_done ? <Badge tone="neon">Treino feito</Badge> : workout && !workout.is_rest ? <Badge>Para hoje</Badge> : null}
    >
      {!workout ? (
        <Empty title="Sem treino programado para este dia" />
      ) : workout.is_rest ? (
        <Empty title="Dia de descanso">Recuperação também faz parte do treino.</Empty>
      ) : (
        <div>
          <p className="mb-3 font-semibold text-navy-800">
            {workout.name}
            {training.day?.label ? <span className="ml-2 text-sm font-normal text-gray-500">{training.day.label}</span> : null}
          </p>
          <ol className="flex flex-col divide-y divide-navy-100">
            {training.day!.slots.map((slot, index) => (
              <li key={index} className="py-3">
                {slot.sets.map((set, i) => (
                  <div key={i} className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium">{names.get(set.exercise) ?? `Exercício ${set.exercise}`}</span>
                    <span className="text-sm tabular-nums text-gray-600">{set.text_repr}</span>
                  </div>
                ))}
                {slot.comment && <p className="mt-1 text-xs text-gray-500">{slot.comment}</p>}
              </li>
            ))}
          </ol>
        </div>
      )}
    </Card>
  );
}

function NutritionSection({ day }: { day: MyDay }) {
  const nutrition = day.nutrition!;
  const logged = nutrition.logged ?? { energy: 0, protein: 0, carbohydrates: 0, fat: 0, fiber: 0 };
  const goals = nutrition.goals;
  const water = nutrition.water;

  return (
    <div className="flex flex-col gap-6">
      <Card title="Alimentação do dia" action={nutrition.plan ? <span className="text-sm text-gray-500">{nutrition.plan.description}</span> : null}>
        <div className="flex flex-col gap-3">
          <Meter label="Calorias" value={Number(logged.energy)} goal={goals?.energy} unit="kcal" color="bg-navy-700" />
          <Meter label="Proteínas" value={Number(logged.protein)} goal={goals?.protein} unit="g" color="bg-protein" />
          <Meter label="Carboidratos" value={Number(logged.carbohydrates)} goal={goals?.carbohydrates} unit="g" color="bg-carbs" />
          <Meter label="Gorduras" value={Number(logged.fat)} goal={goals?.fat} unit="g" color="bg-fat" />
        </div>
        {nutrition.remaining?.energy !== undefined && (
          <p className="mt-3 text-sm text-gray-600">
            Restam <strong className="text-navy-900">{number(Math.max(0, nutrition.remaining.energy))} kcal</strong> para a meta do dia.
          </p>
        )}
      </Card>

      <Card title="Água">
        <Meter label="Hoje" value={water.total_ml} goal={water.goal_ml} unit="ml" color="bg-sky-500" />
        {!water.goal_ml && <p className="mt-2 text-xs text-gray-500">Sem meta definida. Seu nutricionista pode definir uma meta individual.</p>}
        <form action={addWater} className="mt-3 flex flex-wrap gap-2">
          {[200, 300, 500].map(amount => (
            <Button key={amount} name="amount_ml" value={amount} variant="ghost" className="border border-navy-100">
              + {amount} ml
            </Button>
          ))}
        </form>
      </Card>

      {!nutrition.plan ? (
        <Card title="Refeições">
          <Empty title="Nenhum plano alimentar ativo">
            {day.mode === 'guided' ? 'Seu nutricionista ainda está preparando o seu plano.' : 'Sem plano, você ainda pode registrar água.'}
          </Empty>
        </Card>
      ) : (
        <Card title="Refeições">
          <ol className="flex flex-col gap-4">
            {nutrition.meals.map(meal => (
              <li key={meal.id} className="rounded-xl border border-navy-100 p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-semibold">
                    {time(meal.time) && <span className="mr-2 tabular-nums text-neon-700">{time(meal.time)}</span>}
                    {meal.name || 'Refeição'}
                  </p>
                  <span className="text-sm tabular-nums text-gray-500">{number(meal.planned.energy)} kcal</span>
                </div>
                <ul className="mt-2 text-sm text-gray-700">
                  {meal.items.map((item, i) => (
                    <li key={i}>
                      {number(item.amount)} g · {item.name}
                      {item.substitutions > 0 && <span className="ml-1 text-xs text-neon-700">({item.substitutions} substituição(ões))</span>}
                      {item.instructions && <span className="block text-xs text-gray-500">{item.instructions}</span>}
                    </li>
                  ))}
                </ul>
                {meal.instructions && <p className="mt-2 text-xs text-gray-500">{meal.instructions}</p>}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {meal.adherence ? (
                    <Badge tone={meal.adherence === 'full' ? 'neon' : meal.adherence === 'partial' ? 'amber' : 'gray'}>
                      {ADHERENCE_LABELS[meal.adherence]}
                    </Badge>
                  ) : (
                    <>
                      <form action={logPrescribedMeal}>
                        <input type="hidden" name="plan" value={nutrition.plan!.id} />
                        <input type="hidden" name="meal" value={meal.id} />
                        <input type="hidden" name="date" value={day.date} />
                        <input type="hidden" name="items" value={JSON.stringify(meal.items.map(i => ({ ingredient: i.ingredient, amount: i.amount, weight_unit: i.weight_unit })))} />
                        <Button variant="secondary">Segui</Button>
                      </form>
                      {(['partial', 'skipped'] as const).map(status => (
                        <form key={status} action={setAdherence}>
                          <input type="hidden" name="meal" value={meal.id} />
                          <input type="hidden" name="date" value={day.date} />
                          <Button name="status" value={status} variant="ghost" className="border border-navy-100">
                            {ADHERENCE_LABELS[status]}
                          </Button>
                        </form>
                      ))}
                    </>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

function PhysioSection({ day }: { day: MyDay }) {
  const physio = day.physio!;
  if (physio.protocols.length === 0) {
    return (
      <Card title="Fisioterapia">
        <Empty title="Nenhum protocolo ativo">Seu fisioterapeuta ainda está preparando os seus exercícios.</Empty>
      </Card>
    );
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
      <Card title="Fisioterapia">
        {physio.protocols.map(protocol => (
          <div key={protocol.id} className="mb-4 last:mb-0">
            <p className="mb-2 font-semibold">{protocol.name}</p>
            <ul className="flex flex-col gap-3">
              {protocol.exercises.map(exercise => (
                <li key={exercise.id} className="rounded-xl border border-navy-100 p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium">{exercise.name}</span>
                    <span className="text-sm text-gray-600">
                      {[
                        exercise.sets && `${exercise.sets} séries`,
                        exercise.repetitions && `${exercise.repetitions} repetições`,
                        exercise.duration_seconds && `${exercise.duration_seconds} s`,
                        exercise.load,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">{LOCATION_LABELS[exercise.location]}</p>
                  {exercise.instructions && <p className="mt-1 text-sm text-gray-700">{exercise.instructions}</p>}
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    {exercise.video_url && (
                      <a href={exercise.video_url} target="_blank" rel="noreferrer" className="text-sm font-semibold text-navy-700 underline">
                        Ver vídeo
                      </a>
                    )}
                    {exercise.done ? (
                      <Badge tone="neon">Feito hoje</Badge>
                    ) : (
                      <form action={recordExercise}>
                        <input type="hidden" name="protocol_exercise" value={exercise.id} />
                        <Button variant="ghost" className="border border-navy-100">
                          Marcar como feito
                        </Button>
                      </form>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Card>
      <Card title="Como está a dor?">
        <PainForm protocols={physio.protocols.map(p => ({ id: p.id, name: p.name, moments: p.pain_moments }))} />
        {physio.pain.length > 0 && (
          <ul className="mt-4 flex flex-col gap-1 text-sm">
            {physio.pain.map((record, i) => (
              <li key={i} className="flex justify-between">
                <span className="text-gray-600">{MOMENT_LABELS[record.moment]}</span>
                <span className="font-semibold tabular-nums">{record.value}/10</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

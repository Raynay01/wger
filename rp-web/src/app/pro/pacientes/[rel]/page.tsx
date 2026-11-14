import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { Badge, Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { api } from '@/lib/api';
import { exerciseNames } from '@/lib/catalog';
import { DISCIPLINE_LABELS } from '@/lib/brand';
import { GOAL_LABELS, MOMENT_LABELS, SCOPE_LABELS, STATUS_LABELS, date, dateTime, number, shiftDate } from '@/lib/format';
import type { Note, Paginated, Prescription, Relationship, TrainingPlan } from '@/lib/types';
import { userZone } from '@/lib/userZone';
import { todayIn } from '@/lib/zone';
import { addAssessment, addNote, createPlan, createProtocol, createRoutine, createTrainingPlan, relationshipAction } from '../../actions';
import { PeriodizationTimeline } from '@/components/PeriodizationTimeline';

export const metadata: Metadata = { title: 'Paciente' };

const PRESCRIPTION = {
  nutrition: { endpoint: 'nutritionplan', path: 'dieta', label: 'Planos alimentares', title: (p: any) => p.description || 'Plano alimentar' },
  training: { endpoint: 'routine', path: 'treino', label: 'Treinos', title: (p: any) => p.name },
  physio: { endpoint: 'physio-protocol', path: 'protocolo', label: 'Protocolos', title: (p: any) => p.name },
} as const;

export default async function PatientFilePage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string }>;
  searchParams: Promise<{ erro?: string; data?: string }>;
}) {
  const { rel } = await params;
  const { erro, data } = await searchParams;
  const relationship = await api<Relationship>(`care-relationship/${rel}/`);
  const config = PRESCRIPTION[relationship.discipline];
  const isOpen = relationship.status === 'active' || relationship.status === 'paused';
  const here = `/pro/pacientes/${rel}`;
  const today = todayIn(await userZone());

  const [prescriptions, notes, shared] = await Promise.all([
    api<Paginated<Prescription & Record<string, any>>>(`${config.endpoint}/`, { query: { care_relationship: rel, limit: 100 } }),
    api<Paginated<Note>>('multidisciplinary-note/', { query: { patient: relationship.patient ?? undefined, limit: 50 } }),
    isOpen
      ? api<{ scopes: string[]; data: Record<string, any> }>(`care-relationship/${rel}/shared/`)
      : Promise.resolve({ scopes: [] as string[], data: {} as Record<string, any> }),
  ]);
  const sorted = [...prescriptions.results].sort((a, b) => (b.version ?? 0) - (a.version ?? 0));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/pro" className="text-sm text-navy-700 underline">
            ← Pacientes
          </Link>
          <h1 className="mt-1 text-2xl font-bold">{relationship.patient_name ?? relationship.invited_email}</h1>
          <p className="text-sm text-gray-600">
            {DISCIPLINE_LABELS[relationship.discipline]} · {STATUS_LABELS[relationship.status]} · desde {date(relationship.started)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {relationship.status !== 'invited' && (
            <Link href={`/pro/mensagens/${rel}`} className="rounded-xl bg-neon-500 px-4 py-2 text-sm font-semibold text-navy-900 hover:bg-neon-600">
              Mensagens
            </Link>
          )}
          {isOpen && (
            <>
              {(relationship.status === 'active' ? [['pause', 'Pausar']] : [['resume', 'Retomar']]).map(([action, label]) => (
                <form key={action} action={relationshipAction}>
                  <input type="hidden" name="back" value={here} />
                  <input type="hidden" name="id" value={rel} />
                  <Button name="action" value={action} variant="ghost" className="border border-navy-100">
                    {label}
                  </Button>
                </form>
              ))}
              <form action={relationshipAction}>
                <input type="hidden" name="back" value="/pro" />
                <input type="hidden" name="id" value={rel} />
                <Button name="action" value="end" variant="danger">
                  Encerrar
                </Button>
              </form>
            </>
          )}
        </div>
      </div>
      <ErrorFromQuery erro={erro} />

      <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="flex flex-col gap-6">
          <Card title={config.label}>
            {sorted.length === 0 ? (
              <Empty title="Nada prescrito ainda" />
            ) : (
              <ul className="flex flex-col divide-y divide-navy-100">
                {sorted.map(p => (
                  <li key={p.id}>
                    <Link href={`${here}/${config.path}/${p.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-navy-100/40">
                      <span className="font-medium">
                        {config.title(p)} <span className="text-sm text-gray-500">v{p.version}</span>
                      </span>
                      <Badge tone={p.status === 'published' ? 'neon' : p.status === 'draft' ? 'amber' : 'gray'}>{STATUS_LABELS[p.status]}</Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {isOpen && <NewPrescription relationship={relationship} here={here} today={today} />}
          </Card>

          {relationship.discipline === 'training' && <PeriodizationCard relationship={relationship} isOpen={isOpen} here={here} today={today} />}
          {isOpen && relationship.discipline === 'nutrition' && <DiaryCard rel={rel} day={data} here={here} />}
          {isOpen && relationship.discipline === 'training' && <WorkoutLogsCard rel={rel} />}
          {isOpen && relationship.discipline === 'physio' && <PhysioRecordsCard relationship={relationship} here={here} today={today} />}
        </div>

        <div className="flex flex-col gap-6">
          <Card title="Compartilhado pelo paciente">
            {shared.scopes.length === 0 ? (
              <Empty title="Nada compartilhado">O paciente escolhe no app o que mais você pode ver.</Empty>
            ) : (
              <div className="flex flex-col gap-4">
                {shared.scopes.map(scope => (
                  <div key={scope}>
                    <p className="font-semibold">{SCOPE_LABELS[scope]?.title ?? scope}</p>
                    <SharedData scope={scope} data={shared.data[scope]} />
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Observações multidisciplinares">
            {isOpen && (
              <form action={addNote} className="mb-4 flex flex-col gap-2">
                <input type="hidden" name="back" value={here} />
                <input type="hidden" name="relationship" value={rel} />
                <textarea name="text" required rows={3} className={inputClass} placeholder="Ex.: evitar impacto até a reavaliação" />
                <div className="flex flex-wrap items-center gap-3 text-sm">
                  <select name="category" className={`${inputClass} w-auto`} aria-label="Categoria">
                    <option value="general">Geral</option>
                    <option value="guidance">Orientação</option>
                    <option value="restriction">Restrição</option>
                    <option value="alert">Alerta</option>
                  </select>
                  <label className="flex items-center gap-1">
                    <input type="checkbox" name="visible_to_patient" /> visível ao paciente
                  </label>
                  <Button type="submit">Anotar</Button>
                </div>
              </form>
            )}
            {notes.results.length === 0 ? (
              <p className="text-sm text-gray-500">Nenhuma observação.</p>
            ) : (
              <ul className="flex flex-col gap-3 text-sm">
                {notes.results.map(note => (
                  <li key={note.id} className="rounded-xl bg-navy-100/50 p-3">
                    <p>{note.text}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {note.author} · {DISCIPLINE_LABELS[note.discipline]} · {dateTime(note.created)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function NewPrescription({ relationship, here, today }: { relationship: Relationship; here: string; today: string }) {
  if (relationship.discipline === 'nutrition') {
    return (
      <form action={createPlan} className="mt-4 flex flex-wrap items-end gap-2">
        <input type="hidden" name="back" value={here} />
        <input type="hidden" name="relationship" value={relationship.id} />
        <Field label="Novo plano alimentar">
          <input name="description" placeholder="Ex.: Hipertrofia" maxLength={80} className={inputClass} />
        </Field>
        <Button type="submit" variant="secondary">Criar rascunho</Button>
      </form>
    );
  }
  if (relationship.discipline === 'physio') {
    return (
      <form action={createProtocol} className="mt-4 flex flex-wrap items-end gap-2">
        <input type="hidden" name="back" value={here} />
        <input type="hidden" name="relationship" value={relationship.id} />
        <Field label="Novo protocolo">
          <input name="name" placeholder="Ex.: Reabilitação de joelho" maxLength={100} className={inputClass} />
        </Field>
        <Button type="submit" variant="secondary">Criar rascunho</Button>
      </form>
    );
  }
  return (
    <form action={createRoutine} className="mt-4 grid gap-2 sm:grid-cols-4">
      <input type="hidden" name="back" value={here} />
      <input type="hidden" name="relationship" value={relationship.id} />
      <Field label="Novo treino">
        <input name="name" placeholder="Ex.: Força A/B" maxLength={25} className={inputClass} />
      </Field>
      <Field label="Início">
        <input type="date" name="start" defaultValue={today} required className={inputClass} />
      </Field>
      <Field label="Fim">
        <input type="date" name="end" defaultValue={shiftDate(today, 56)} required className={inputClass} />
      </Field>
      <div className="flex items-end">
        <Button type="submit" variant="secondary">Criar rascunho</Button>
      </div>
    </form>
  );
}

async function PeriodizationCard({ relationship, isOpen, here, today }: { relationship: Relationship; isOpen: boolean; here: string; today: string }) {
  const plans = await api<Paginated<TrainingPlan>>('training-plan/', { query: { care_relationship: relationship.id, limit: 100 } });
  const sorted = [...plans.results].sort((a, b) => b.version - a.version);
  const current = sorted.find(p => p.status === 'published');
  return (
    <Card title="Periodização">
      {current && current.blocks.length > 0 && (
        <div className="mb-4">
          <PeriodizationTimeline blocks={current.blocks} today={today} />
        </div>
      )}
      {sorted.length === 0 ? (
        <Empty title="Nenhuma periodização">Organize o treino em fases (mesociclos) com foco, semanas e o treino de cada uma.</Empty>
      ) : (
        <ul className="flex flex-col divide-y divide-navy-100">
          {sorted.map(p => (
            <li key={p.id}>
              <Link href={`${here}/periodizacao/${p.id}`} className="flex flex-wrap items-center justify-between gap-2 py-3 hover:bg-navy-100/40">
                <span className="font-medium">
                  {p.name} <span className="text-sm text-gray-500">v{p.version} · {GOAL_LABELS[p.goal]}</span>
                </span>
                <Badge tone={p.status === 'published' ? 'neon' : p.status === 'draft' ? 'amber' : 'gray'}>{STATUS_LABELS[p.status]}</Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {isOpen && (
        <form action={createTrainingPlan} className="mt-4 grid gap-2 sm:grid-cols-4">
          <input type="hidden" name="back" value={here} />
          <input type="hidden" name="relationship" value={relationship.id} />
          <Field label="Nova periodização">
            <input name="name" placeholder="Ex.: Temporada 2027" maxLength={100} className={inputClass} />
          </Field>
          <Field label="Objetivo">
            <select name="goal" className={inputClass}>
              {Object.entries(GOAL_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Início">
            <input type="date" name="start" defaultValue={today} required className={inputClass} />
          </Field>
          <div className="flex items-end">
            <Button type="submit" variant="secondary">Criar periodização</Button>
          </div>
        </form>
      )}
    </Card>
  );
}

async function DiaryCard({ rel, day, here }: { rel: string; day?: string; here: string }) {
  const diary = await api<{ date: string; items: any[]; total: any }>(`care-relationship/${rel}/nutrition-diary/`, { query: { date: day } });
  return (
    <Card
      title="Diário alimentar"
      action={
        <div className="flex items-center gap-2 text-sm">
          <Link href={`${here}?data=${shiftDate(diary.date, -1)}`} aria-label="Dia anterior">←</Link>
          <span className="tabular-nums">{date(diary.date)}</span>
          <Link href={`${here}?data=${shiftDate(diary.date, 1)}`} aria-label="Próximo dia">→</Link>
        </div>
      }
    >
      {diary.items.length === 0 ? (
        <Empty title="Nenhum registro neste dia" />
      ) : (
        <>
          <ul className="flex flex-col divide-y divide-navy-100 text-sm">
            {diary.items.map(item => (
              <li key={item.id} className="flex justify-between gap-2 py-2">
                <span>
                  <span className="tabular-nums text-gray-500">{dateTime(item.datetime).split(' ')[1]}</span> · {item.ingredient_name} · {number(item.amount)} g
                  {item.comment && <span className="block text-xs text-gray-500">{item.comment}</span>}
                </span>
                <span className="tabular-nums text-gray-600">{number(item.values?.energy)} kcal</span>
              </li>
            ))}
          </ul>
          {diary.total && (
            <p className="mt-3 text-sm">
              Total: <strong>{number(diary.total.energy)} kcal</strong> · P {number(diary.total.protein)} g · C {number(diary.total.carbohydrates)} g · G {number(diary.total.fat)} g
            </p>
          )}
        </>
      )}
    </Card>
  );
}

async function WorkoutLogsCard({ rel }: { rel: string }) {
  const [logs, names] = await Promise.all([api<{ results: any[] }>(`care-relationship/${rel}/workout-logs/`), exerciseNames()]);
  return (
    <Card title="Registros de treino (planejado x realizado)">
      {logs.results.length === 0 ? (
        <Empty title="Nenhum treino registrado ainda" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-gray-500">
              <tr>
                <th className="py-2">Data</th>
                <th>Exercício</th>
                <th className="text-right">Reps</th>
                <th className="text-right">Carga</th>
                <th className="text-right">RIR</th>
                <th className="text-right">RPE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-100">
              {logs.results.slice(0, 50).map(log => (
                <tr key={log.id}>
                  <td className="py-2 tabular-nums">{dateTime(log.date)}</td>
                  <td>{names.get(log.exercise) ?? log.exercise}</td>
                  <td className="text-right tabular-nums">
                    {number(log.repetitions)}
                    {log.repetitions_target ? <span className="text-gray-400"> / {number(log.repetitions_target)}</span> : null}
                  </td>
                  <td className="text-right tabular-nums">
                    {number(log.weight, 1)}
                    {log.weight_target ? <span className="text-gray-400"> / {number(log.weight_target, 1)}</span> : null}
                  </td>
                  <td className="text-right tabular-nums">{number(log.rir, 1)}</td>
                  <td className="text-right tabular-nums">{number(log.rpe, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

async function PhysioRecordsCard({ relationship, here, today }: { relationship: Relationship; here: string; today: string }) {
  const [pain, assessments] = await Promise.all([
    api<Paginated<any>>('pain-record/', { query: { user: relationship.patient ?? undefined, limit: 30 } }),
    api<Paginated<any>>('functional-assessment/', { query: { relationship: relationship.id, limit: 100 } }),
  ]);
  return (
    <>
      <Card title="Registros de dor">
        {pain.results.length === 0 ? (
          <Empty title="Nenhum registro de dor" />
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100 text-sm">
            {pain.results.map(r => (
              <li key={r.id} className="flex justify-between py-2">
                <span>
                  {dateTime(r.datetime)} · {MOMENT_LABELS[r.moment]} {r.body_region && `· ${r.body_region}`}
                </span>
                <Badge tone={r.value >= 7 ? 'red' : r.value >= 4 ? 'amber' : 'neon'}>{r.value}/10</Badge>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card title="Avaliações funcionais">
        {assessments.results.length > 0 && (
          <ul className="mb-4 flex flex-col divide-y divide-navy-100 text-sm">
            {assessments.results.map(a => (
              <li key={a.id} className="flex justify-between py-2">
                <span>
                  {date(a.date)} · {a.name} {a.side && `(${a.side === 'left' ? 'esq.' : 'dir.'})`}
                </span>
                <strong className="tabular-nums">
                  {number(a.value, 1)} {a.unit}
                </strong>
              </li>
            ))}
          </ul>
        )}
        <form action={addAssessment} className="grid gap-2 sm:grid-cols-3">
          <input type="hidden" name="back" value={here} />
          <input type="hidden" name="relationship" value={relationship.id} />
          <Field label="Tipo">
            <select name="kind" className={inputClass}>
              <option value="rom">Amplitude de movimento</option>
              <option value="strength">Força</option>
              <option value="functional_test">Teste funcional</option>
              <option value="questionnaire">Questionário</option>
              <option value="balance">Equilíbrio</option>
              <option value="other">Outro</option>
            </select>
          </Field>
          <Field label="Nome">
            <input name="name" required placeholder="Ex.: Flexão de joelho, TUG" className={inputClass} />
          </Field>
          <Field label="Lado">
            <select name="side" className={inputClass}>
              <option value="">Não se aplica</option>
              <option value="left">Esquerdo</option>
              <option value="right">Direito</option>
            </select>
          </Field>
          <Field label="Valor">
            <input name="value" inputMode="decimal" className={inputClass} />
          </Field>
          <Field label="Unidade">
            <input name="unit" placeholder="°, s, pontos, kg" className={inputClass} />
          </Field>
          <Field label="Data">
            <input type="date" name="date" defaultValue={today} className={inputClass} />
          </Field>
          <div className="sm:col-span-3">
            <Button type="submit">Registrar avaliação</Button>
          </div>
        </form>
      </Card>
    </>
  );
}

function SharedData({ scope, data }: { scope: string; data: any }) {
  if (!data) {
    return null;
  }
  if (scope === 'training.schedule') {
    return (
      <ul className="text-sm text-gray-700">
        {data.routines.map((r: any) => (
          <li key={r.name}>
            {r.name}: {r.training_days_per_cycle} dia(s) de treino por ciclo de {r.cycle_length}
          </li>
        ))}
        {data.usual_start_hours.length > 0 && <li>Horários habituais: {data.usual_start_hours.map((h: number) => `${h}h`).join(', ')}</li>}
        {data.expected_duration_minutes && <li>Duração prevista: {data.expected_duration_minutes} min</li>}
      </ul>
    );
  }
  if (scope === 'training.adherence') {
    return <p className="text-sm text-gray-700">{data.sessions} treino(s) e {data.sets_logged} série(s) nos últimos {data.period_days} dias.</p>;
  }
  if (scope === 'nutrition.goals') {
    return data.plan ? (
      <p className="text-sm text-gray-700">
        {data.plan}: {number(data.goal_energy)} kcal · P {number(data.goal_protein)} g · C {number(data.goal_carbohydrates)} g · G {number(data.goal_fat)} g
        {data.meals.length > 0 && <> · Refeições: {data.meals.map((m: any) => `${m.name}${m.time ? ` (${m.time.slice(0, 5)})` : ''}`).join(', ')}</>}
      </p>
    ) : (
      <p className="text-sm text-gray-500">Sem plano alimentar publicado.</p>
    );
  }
  if (scope === 'nutrition.adherence') {
    return <p className="text-sm text-gray-700">Registrou o diário em {data.days_with_records} de {data.period_days} dias.</p>;
  }
  if (scope === 'physio.pain') {
    return (
      <p className="text-sm text-gray-700">
        {data.records} registro(s) nos últimos {data.period_days} dias{data.average !== null ? `, média ${number(data.average, 1)}/10` : ''}.
      </p>
    );
  }
  if (scope === 'body.measurements') {
    return data.body_weight.length ? (
      <p className="text-sm text-gray-700">
        Último peso: {number(data.body_weight[0].value, 1)} kg em {date(data.body_weight[0].date)}
      </p>
    ) : (
      <p className="text-sm text-gray-500">Sem registros de peso.</p>
    );
  }
  if (scope === 'notes.multidisciplinary') {
    return <p className="text-sm text-gray-700">{data.length} observação(ões) de outros profissionais (veja ao lado).</p>;
  }
  return null;
}

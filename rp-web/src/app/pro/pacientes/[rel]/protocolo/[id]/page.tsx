import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { PrescriptionHeader } from '@/components/PrescriptionHeader';
import { SearchPicker } from '@/components/SearchPicker';
import { Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { addProtocolExercise, deleteProtocolExercise, updateProtocol } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { LOCATION_LABELS, MOMENT_LABELS, date } from '@/lib/format';
import type { Paginated, Protocol, ProtocolExercise } from '@/lib/types';

export const metadata: Metadata = { title: 'Protocolo de fisioterapia' };

export default async function ProtocolBuilderPage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string; id: string }>;
  searchParams: Promise<{ erro?: string }>;
}) {
  const { rel, id } = await params;
  const { erro } = await searchParams;
  const [protocol, exercises] = await Promise.all([
    api<Protocol>(`physio-protocol/${id}/`),
    api<Paginated<ProtocolExercise>>('protocol-exercise/', { query: { protocol: id, limit: 100 } }),
  ]);
  const versions = protocol.lineage_id
    ? (await api<Paginated<Protocol>>('physio-protocol/', { query: { lineage_id: protocol.lineage_id, limit: 100 } })).results
    : [protocol];
  const editable = protocol.status === 'draft';
  const here = `/pro/pacientes/${rel}/protocolo/${id}`;

  return (
    <div className="flex flex-col gap-6">
      <PrescriptionHeader kind="physio" relationship={rel} prescription={protocol} title={protocol.name} versions={versions} path="protocolo" back={here} />
      <ErrorFromQuery erro={erro} />

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_22rem]">
        <Card title="Exercícios">
          {exercises.results.length === 0 ? (
            <Empty title="Nenhum exercício ainda" />
          ) : (
            <ol className="flex flex-col gap-3">
              {exercises.results.map(e => (
                <li key={e.id} className="rounded-xl border border-navy-100 p-3">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-semibold">{e.name}</span>
                    <span className="text-sm text-gray-600">
                      {[
                        e.sets && `${e.sets} séries`,
                        e.repetitions && `${e.repetitions} repetições`,
                        e.duration_seconds && `${e.duration_seconds} s`,
                        e.load,
                        e.frequency_per_week && `${e.frequency_per_week}x/semana`,
                        LOCATION_LABELS[e.location],
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </div>
                  {e.instructions && <p className="mt-1 text-sm text-gray-700">{e.instructions}</p>}
                  <div className="mt-1 flex items-center justify-between gap-2">
                    {e.video_url ? (
                      <a href={e.video_url} target="_blank" rel="noreferrer" className="text-sm text-navy-700 underline">
                        Vídeo
                      </a>
                    ) : (
                      <span />
                    )}
                    {editable && (
                      <form action={deleteProtocolExercise}>
                        <input type="hidden" name="back" value={here} />
                        <input type="hidden" name="id" value={e.id} />
                        <Button variant="ghost">Remover</Button>
                      </form>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}

          {editable && (
            <form action={addProtocolExercise} className="mt-4 grid gap-3 border-t border-navy-100 pt-4 sm:grid-cols-3">
              <input type="hidden" name="back" value={here} />
              <input type="hidden" name="protocol" value={id} />
              <div className="sm:col-span-2">
                <SearchPicker kind="exercise" name="exercise" nameField="exercise_name" label="Exercício da biblioteca (opcional)" required={false} />
              </div>
              <Field label="Ou nome livre">
                <input name="name" maxLength={100} placeholder="Ex.: Isometria de quadríceps" className={inputClass} />
              </Field>
              <Field label="Séries">
                <input name="sets" inputMode="numeric" className={inputClass} />
              </Field>
              <Field label="Repetições">
                <input name="repetitions" inputMode="numeric" className={inputClass} />
              </Field>
              <Field label="Tempo (segundos)">
                <input name="duration_seconds" inputMode="numeric" className={inputClass} />
              </Field>
              <Field label="Carga">
                <input name="load" maxLength={50} placeholder="Ex.: faixa elástica vermelha" className={inputClass} />
              </Field>
              <Field label="Vezes por semana">
                <input name="frequency_per_week" inputMode="numeric" className={inputClass} />
              </Field>
              <Field label="Local">
                <select name="location" className={inputClass}>
                  {Object.entries(LOCATION_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="sm:col-span-2">
                <Field label="Orientações">
                  <textarea name="instructions" rows={2} className={inputClass} />
                </Field>
              </div>
              <Field label="Link do vídeo">
                <input name="video_url" type="url" placeholder="https://" className={inputClass} />
              </Field>
              <div className="sm:col-span-3">
                <Button type="submit" variant="secondary">
                  Adicionar exercício
                </Button>
              </div>
            </form>
          )}
        </Card>

        <Card title="Configuração">
          {editable ? (
            <form action={updateProtocol} className="flex flex-col gap-3">
              <input type="hidden" name="back" value={here} />
              <input type="hidden" name="id" value={id} />
              <Field label="Nome">
                <input name="name" defaultValue={protocol.name} required maxLength={100} className={inputClass} />
              </Field>
              <Field label="Descrição">
                <textarea name="description" defaultValue={protocol.description} rows={3} className={inputClass} />
              </Field>
              <Field label="Término (opcional)">
                <input type="date" name="end" defaultValue={protocol.end ?? ''} className={inputClass} />
              </Field>
              <fieldset className="text-sm">
                <legend className="mb-1 font-medium text-navy-800">Quando pedir o registro de dor (0 a 10)</legend>
                {(['before', 'during', 'after', 'next_day'] as const).map(moment => (
                  <label key={moment} className="flex items-center gap-2">
                    <input type="checkbox" name={`pain_${moment}`} defaultChecked={protocol.pain_moments.includes(moment)} />
                    {MOMENT_LABELS[moment]}
                  </label>
                ))}
              </fieldset>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Alertar a partir de" hint="valor de dor">
                  <input name="pain_alert_threshold" inputMode="numeric" defaultValue={protocol.pain_alert_threshold} className={inputClass} />
                </Field>
                <Field label="Ou aumento de" hint="pontos antes → depois">
                  <input name="pain_alert_increase" inputMode="numeric" defaultValue={protocol.pain_alert_increase} className={inputClass} />
                </Field>
              </div>
              <Button type="submit">Salvar</Button>
            </form>
          ) : (
            <dl className="flex flex-col gap-2 text-sm">
              <dt className="font-medium">Período</dt>
              <dd>
                {date(protocol.start)} até {protocol.end ? date(protocol.end) : 'sem data'}
              </dd>
              <dt className="font-medium">Registro de dor</dt>
              <dd>{protocol.pain_moments.map(m => MOMENT_LABELS[m]).join(', ') || 'Não solicitado'}</dd>
              <dt className="font-medium">Alertas</dt>
              <dd>
                Dor a partir de {protocol.pain_alert_threshold} ou aumento de {protocol.pain_alert_increase} pontos
              </dd>
            </dl>
          )}
        </Card>
      </div>
    </div>
  );
}

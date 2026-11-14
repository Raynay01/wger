import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { NutritionalAssessmentSummary } from '@/components/NutritionalAssessmentSummary';
import { Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { api } from '@/lib/api';
import { ACTIVITY_LABELS, EQUATION_LABELS, SKINFOLD_PROTOCOLS, SKINFOLD_SITES, date, number } from '@/lib/format';
import { ANAMNESIS_FIELDS } from '@/lib/types';
import type { NutritionalAnamnesis, NutritionalAssessment, Paginated, Relationship } from '@/lib/types';
import { userZone } from '@/lib/userZone';
import { todayIn } from '@/lib/zone';
import { addAnamnesis, addNutritionalAssessment, createPlan, deleteNutritionalAssessment } from '../../../actions';

export const metadata: Metadata = { title: 'Avaliação nutricional' };

export default async function NutritionalAssessmentPage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string }>;
  searchParams: Promise<{ erro?: string }>;
}) {
  const { rel } = await params;
  const { erro } = await searchParams;
  const here = `/pro/pacientes/${rel}/avaliacao`;
  const [relationship, assessments, anamneses, today] = await Promise.all([
    api<Relationship>(`care-relationship/${rel}/`),
    api<Paginated<NutritionalAssessment>>('nutritional-assessment/', { query: { relationship: rel, limit: 100 } }),
    api<Paginated<NutritionalAnamnesis>>('nutritional-anamnesis/', { query: { relationship: rel, limit: 20 } }),
    userZone().then(todayIn),
  ]);
  const latest = assessments.results[0];
  const anamnesis = anamneses.results[0];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link href={`/pro/pacientes/${rel}`} className="text-sm text-navy-700 underline">
          ← {relationship.patient_name ?? 'Paciente'}
        </Link>
        <h1 className="mt-1 text-2xl font-bold">Avaliação nutricional</h1>
      </div>
      <ErrorFromQuery erro={erro} />

      <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
        <div className="flex flex-col gap-6">
          <Card title="Antropometria e gasto energético">
            {latest ? (
              <>
                <NutritionalAssessmentSummary assessment={latest} />
                <form action={createPlan} className="mt-4 flex flex-wrap items-end gap-2">
                  <input type="hidden" name="back" value={here} />
                  <input type="hidden" name="relationship" value={rel} />
                  <input type="hidden" name="goal_energy" value={latest.target_energy} />
                  {latest.macros && (
                    <>
                      <input type="hidden" name="goal_protein" value={latest.macros.protein} />
                      <input type="hidden" name="goal_carbohydrates" value={latest.macros.carbohydrates} />
                      <input type="hidden" name="goal_fat" value={latest.macros.fat} />
                    </>
                  )}
                  <Field label="Plano alimentar com esta meta">
                    <input name="description" placeholder="Ex.: Emagrecimento" maxLength={80} className={inputClass} />
                  </Field>
                  <Button type="submit" variant="secondary">
                    Criar plano com {number(latest.target_energy)} kcal
                  </Button>
                </form>
              </>
            ) : (
              <Empty title="Nenhuma avaliação ainda">Registre peso, altura e o nível de atividade para calcular a meta de calorias.</Empty>
            )}
          </Card>

          {assessments.results.length > 1 && (
            <Card title="Evolução">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-gray-500">
                    <tr>
                      <th className="py-2">Data</th>
                      <th className="text-right">Peso</th>
                      <th className="text-right">IMC</th>
                      <th className="text-right">Cintura</th>
                      <th className="text-right">% gordura</th>
                      <th className="text-right">Meta</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-100">
                    {assessments.results.map(a => (
                      <tr key={a.id}>
                        <td className="py-2 tabular-nums">{date(a.date)}</td>
                        <td className="text-right tabular-nums">{number(a.weight, 1)} kg</td>
                        <td className="text-right tabular-nums">{number(a.bmi, 1)}</td>
                        <td className="text-right tabular-nums">{a.waist ? `${number(a.waist, 1)} cm` : '–'}</td>
                        <td className="text-right tabular-nums">{a.body_fat ? `${number(a.body_fat, 1)}%` : '–'}</td>
                        <td className="text-right tabular-nums">{number(a.target_energy)} kcal</td>
                        <td className="text-right">
                          <form action={deleteNutritionalAssessment}>
                            <input type="hidden" name="back" value={here} />
                            <input type="hidden" name="id" value={a.id} />
                            <button type="submit" className="text-xs text-red-700 underline" aria-label={`Apagar avaliação de ${date(a.date)}`}>
                              apagar
                            </button>
                          </form>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          <Card title="Nova avaliação">
            <form action={addNutritionalAssessment} className="grid gap-3 sm:grid-cols-4">
              <input type="hidden" name="back" value={here} />
              <input type="hidden" name="relationship" value={rel} />
              <Field label="Data">
                <input type="date" name="date" defaultValue={today} required className={inputClass} />
              </Field>
              <Field label="Sexo">
                <select name="sex" defaultValue={latest?.sex ?? 'female'} className={inputClass}>
                  <option value="female">Feminino</option>
                  <option value="male">Masculino</option>
                </select>
              </Field>
              <Field label="Idade (anos)">
                <input name="age" type="number" min={10} max={120} required defaultValue={latest?.age} className={inputClass} />
              </Field>
              <Field label="Altura (cm)">
                <input name="height" inputMode="decimal" required defaultValue={latest?.height} className={inputClass} />
              </Field>
              <Field label="Peso (kg)">
                <input name="weight" inputMode="decimal" required className={inputClass} />
              </Field>
              <Field label="Cintura (cm)">
                <input name="waist" inputMode="decimal" className={inputClass} />
              </Field>
              <Field label="Quadril (cm)">
                <input name="hip" inputMode="decimal" className={inputClass} />
              </Field>
              <Field label="Gordura corporal (%)" hint="Bioimpedância, ou deixe para as dobras">
                <input name="body_fat" inputMode="decimal" className={inputClass} />
              </Field>
              <details className="sm:col-span-4 rounded-xl border border-navy-100 p-3" open={Boolean(latest?.skinfold_protocol)}>
                <summary className="cursor-pointer text-sm font-semibold text-navy-700">Dobras cutâneas (mm)</summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-4">
                  <div className="sm:col-span-4">
                    <Field label="Protocolo" hint="Com protocolo, o % de gordura é calculado pelas dobras (equação de Siri).">
                      <select name="skinfold_protocol" defaultValue={latest?.skinfold_protocol ?? ''} className={inputClass}>
                        <option value="">Não usar dobras</option>
                        {Object.entries(SKINFOLD_PROTOCOLS).map(([value, { label }]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <ul className="mt-2 text-xs text-gray-500">
                      {Object.values(SKINFOLD_PROTOCOLS).map(({ label, sites }) => (
                        <li key={label}>
                          <strong className="font-semibold">{label}:</strong> {sites}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {SKINFOLD_SITES.map(([site, label]) => (
                    <Field key={site} label={label}>
                      <input name={`skinfold_${site}`} inputMode="decimal" className={inputClass} />
                    </Field>
                  ))}
                </div>
              </details>
              <div className="sm:col-span-2">
                <Field label="Nível de atividade">
                  <select name="activity_level" defaultValue={latest?.activity_level ?? 'light'} className={inputClass}>
                    {Object.entries(ACTIVITY_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label="Equação">
                <select name="equation" defaultValue={latest?.equation ?? 'mifflin'} className={inputClass}>
                  {Object.entries(EQUATION_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Ajuste (kcal)" hint="Ex.: −500 para perder peso">
                <input name="energy_adjustment" type="number" min={-1500} max={1500} step={50} defaultValue={latest?.energy_adjustment ?? 0} className={inputClass} />
              </Field>
              <Field label="Proteína (g/kg)" hint="Com a gordura, divide a meta em macros">
                <input name="protein_per_kg" inputMode="decimal" defaultValue={latest?.protein_per_kg ?? ''} className={inputClass} />
              </Field>
              <Field label="Gordura (% das kcal)">
                <input name="fat_percent" type="number" min={10} max={70} defaultValue={latest?.fat_percent ?? ''} className={inputClass} />
              </Field>
              <div className="sm:col-span-4">
                <Field label="Observações">
                  <textarea name="notes" rows={2} className={inputClass} />
                </Field>
              </div>
              <div className="sm:col-span-4">
                <Button type="submit">Calcular e registrar</Button>
              </div>
            </form>
          </Card>
        </div>

        <Card title="Anamnese">
          {anamnesis ? (
            <dl className="flex flex-col gap-3 text-sm">
              <div className="text-gray-600">Registrada em {date(anamnesis.date)}</div>
              {ANAMNESIS_FIELDS.filter(([key]) => anamnesis[key]).map(([key, label]) => (
                <div key={key}>
                  <dt className="font-semibold text-navy-900">{label}</dt>
                  <dd className="whitespace-pre-line text-gray-700">{anamnesis[key]}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <Empty title="Nenhuma anamnese">Histórico, alergias, preferências e hábitos do paciente.</Empty>
          )}
          <details className="mt-4" open={!anamnesis}>
            <summary className="cursor-pointer text-sm font-semibold text-navy-700">{anamnesis ? 'Atualizar anamnese' : 'Registrar anamnese'}</summary>
            <form action={addAnamnesis} className="mt-3 flex flex-col gap-3">
              <input type="hidden" name="back" value={here} />
              <input type="hidden" name="relationship" value={rel} />
              <input type="hidden" name="date" value={today} />
              {ANAMNESIS_FIELDS.map(([key, label]) => (
                <Field key={key} label={label}>
                  <textarea name={key} rows={2} defaultValue={anamnesis?.[key] ?? ''} className={inputClass} />
                </Field>
              ))}
              <Button type="submit">Salvar anamnese</Button>
            </form>
          </details>
          {anamneses.results.length > 1 && (
            <p className="mt-3 text-xs text-gray-500">
              Anteriores: {anamneses.results.slice(1).map(a => date(a.date)).join(', ')}
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { PrescriptionHeader } from '@/components/PrescriptionHeader';
import { SearchPicker } from '@/components/SearchPicker';
import { Button, Card, Empty, Field, inputClass } from '@/components/ui';
import { addMeal, addMealItem, addSubstitution, deleteMeal, deleteMealItem, deleteSubstitution, updatePlan } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { CRITERION_LABELS, number, time } from '@/lib/format';
import type { NutritionPlan, Paginated, PlanInfo, Values } from '@/lib/types';

export const metadata: Metadata = { title: 'Plano alimentar' };

const MEAL_NAMES = ['Café da manhã', 'Lanche da manhã', 'Almoço', 'Lanche da tarde', 'Pré-treino', 'Pós-treino', 'Jantar', 'Ceia'];

const KCAL = { protein: 4, carbohydrates: 4, fat: 9 };

function sum(values: Values[]): Values {
  return values.reduce(
    (acc, v) => ({
      energy: acc.energy + Number(v.energy),
      protein: acc.protein + Number(v.protein),
      carbohydrates: acc.carbohydrates + Number(v.carbohydrates),
      fat: acc.fat + Number(v.fat),
      fiber: (acc.fiber ?? 0) + Number(v.fiber ?? 0),
    }),
    { energy: 0, protein: 0, carbohydrates: 0, fat: 0, fiber: 0 },
  );
}

export default async function DietBuilderPage({
  params,
  searchParams,
}: {
  params: Promise<{ rel: string; id: string }>;
  searchParams: Promise<{ erro?: string }>;
}) {
  const { rel, id } = await params;
  const { erro } = await searchParams;
  const plan = await api<PlanInfo>(`nutritionplaninfo/${id}/`);
  const versions = plan.lineage_id
    ? (await api<Paginated<NutritionPlan>>('nutritionplan/', { query: { lineage_id: plan.lineage_id, limit: 100 } })).results
    : [plan];
  const editable = plan.status === 'draft';
  const here = `/pro/pacientes/${rel}/dieta/${id}`;
  const total = sum(plan.meals.map(m => m.nutritional_values));
  const macroKcal = total.protein * KCAL.protein + total.carbohydrates * KCAL.carbohydrates + total.fat * KCAL.fat;
  const share = (grams: number, factor: number) => (macroKcal ? Math.round(((grams * factor) / macroKcal) * 100) : 0);

  return (
    <div className="flex flex-col gap-6">
      <PrescriptionHeader
        kind="nutrition"
        relationship={rel}
        prescription={plan}
        title={plan.description || 'Plano alimentar'}
        versions={versions}
        path="dieta"
        back={here}
      />
      <ErrorFromQuery erro={erro} />

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="flex flex-col gap-4">
          {plan.meals.length === 0 && <Empty title="Nenhuma refeição ainda">Adicione as refeições do dia abaixo.</Empty>}
          {[...plan.meals]
            .sort((a, b) => (a.time ?? '99').localeCompare(b.time ?? '99'))
            .map(meal => (
              <Card
                key={meal.id}
                title={
                  <span>
                    {time(meal.time) && <span className="mr-2 tabular-nums text-neon-700">{time(meal.time)}</span>}
                    {meal.name || 'Refeição'}
                  </span>
                }
                action={
                  <div className="flex items-center gap-3">
                    <span className="text-sm tabular-nums text-gray-600">{number(meal.nutritional_values.energy)} kcal</span>
                    {editable && (
                      <form action={deleteMeal}>
                        <input type="hidden" name="back" value={here} />
                        <input type="hidden" name="id" value={meal.id} />
                        <Button variant="ghost" aria-label={`Remover ${meal.name}`}>
                          Remover
                        </Button>
                      </form>
                    )}
                  </div>
                }
              >
                {meal.instructions && <p className="mb-3 text-sm text-gray-600">{meal.instructions}</p>}
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-gray-500">
                    <tr>
                      <th className="py-1">Alimento</th>
                      <th className="text-right">Qtd.</th>
                      <th className="text-right">kcal</th>
                      <th className="hidden text-right sm:table-cell">P</th>
                      <th className="hidden text-right sm:table-cell">C</th>
                      <th className="hidden text-right sm:table-cell">G</th>
                      {editable && <th />}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-100">
                    {meal.meal_items.map(item => {
                      const ingredient = item.ingredient_obj as any;
                      const factor = Number(item.amount) / 100;
                      return (
                        <tr key={item.id} className="align-top">
                          <td className="py-2">
                            {ingredient.name}
                            {item.instructions && <span className="block text-xs text-gray-500">{item.instructions}</span>}
                            {item.substitutions.length > 0 && (
                              <ul className="mt-1 text-xs text-neon-700">
                                {item.substitutions.map(s => (
                                  <li key={s.id} className="flex items-center gap-2">
                                    ou {number(s.amount)} g de {s.ingredient_name} ({CRITERION_LABELS[s.criterion]})
                                    {editable && (
                                      <form action={deleteSubstitution}>
                                        <input type="hidden" name="back" value={here} />
                                        <input type="hidden" name="id" value={s.id} />
                                        <button className="text-gray-400 hover:text-red-700" aria-label="Remover substituição">
                                          ×
                                        </button>
                                      </form>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            )}
                            {editable && (
                              <details className="mt-1 text-xs">
                                <summary className="cursor-pointer text-navy-700">+ substituição</summary>
                                <form action={addSubstitution} className="mt-2 grid gap-2 sm:grid-cols-[1fr_6rem_10rem_auto]">
                                  <input type="hidden" name="back" value={here} />
                                  <input type="hidden" name="meal_item" value={item.id} />
                                  <SearchPicker kind="food" name="ingredient" label="Alimento" />
                                  <Field label="Gramas">
                                    <input name="amount" required inputMode="decimal" className={inputClass} />
                                  </Field>
                                  <Field label="Critério">
                                    <select name="criterion" className={inputClass}>
                                      {Object.entries(CRITERION_LABELS).map(([value, label]) => (
                                        <option key={value} value={value}>
                                          {label}
                                        </option>
                                      ))}
                                    </select>
                                  </Field>
                                  <div className="flex items-end">
                                    <Button type="submit">Adicionar</Button>
                                  </div>
                                </form>
                              </details>
                            )}
                          </td>
                          <td className="py-2 text-right tabular-nums">{number(item.amount)} g</td>
                          <td className="py-2 text-right tabular-nums">{number(ingredient.energy * factor)}</td>
                          <td className="hidden py-2 text-right tabular-nums sm:table-cell">{number(ingredient.protein * factor, 1)}</td>
                          <td className="hidden py-2 text-right tabular-nums sm:table-cell">{number(ingredient.carbohydrates * factor, 1)}</td>
                          <td className="hidden py-2 text-right tabular-nums sm:table-cell">{number(ingredient.fat * factor, 1)}</td>
                          {editable && (
                            <td className="py-2 text-right">
                              <form action={deleteMealItem}>
                                <input type="hidden" name="back" value={here} />
                                <input type="hidden" name="id" value={item.id} />
                                <button className="text-gray-400 hover:text-red-700" aria-label={`Remover ${ingredient.name}`}>
                                  ×
                                </button>
                              </form>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {editable && (
                  <form action={addMealItem} className="mt-3 grid gap-2 border-t border-navy-100 pt-3 sm:grid-cols-[1fr_6rem_1fr_auto]">
                    <input type="hidden" name="back" value={here} />
                    <input type="hidden" name="meal" value={meal.id} />
                    <SearchPicker kind="food" name="ingredient" label="Adicionar alimento" placeholder="Buscar por nome ou código de barras" />
                    <Field label="Gramas">
                      <input name="amount" required inputMode="decimal" className={inputClass} />
                    </Field>
                    <Field label="Orientação (opcional)">
                      <input name="instructions" maxLength={200} placeholder="Ex.: cozido, sem sal" className={inputClass} />
                    </Field>
                    <div className="flex items-end">
                      <Button type="submit">Adicionar</Button>
                    </div>
                  </form>
                )}
              </Card>
            ))}

          {editable && (
            <Card title="Nova refeição">
              <form action={addMeal} className="grid gap-3 sm:grid-cols-[1fr_8rem]">
                <input type="hidden" name="back" value={here} />
                <input type="hidden" name="plan" value={plan.id} />
                <Field label="Nome">
                  <input name="name" list="meal-names" required maxLength={25} className={inputClass} />
                  <datalist id="meal-names">
                    {MEAL_NAMES.map(name => (
                      <option key={name} value={name} />
                    ))}
                  </datalist>
                </Field>
                <Field label="Horário">
                  <input type="time" name="time" className={inputClass} />
                </Field>
                <div className="sm:col-span-2">
                  <Field label="Orientações (opcional)">
                    <textarea name="instructions" rows={2} className={inputClass} />
                  </Field>
                </div>
                <div>
                  <Button type="submit" variant="secondary">
                    Adicionar refeição
                  </Button>
                </div>
              </form>
            </Card>
          )}
        </div>

        <aside className="flex flex-col gap-4 lg:sticky lg:top-20">
          <Card title="Total do dia">
            <dl className="grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-gray-600">Calorias</dt>
              <dd className="text-right font-semibold tabular-nums">
                {number(total.energy)} {plan.goal_energy ? `/ ${number(plan.goal_energy)}` : ''} kcal
              </dd>
              <dt className="text-gray-600">Proteínas</dt>
              <dd className="text-right tabular-nums">
                {number(total.protein, 1)} {plan.goal_protein ? `/ ${number(plan.goal_protein)}` : ''} g
              </dd>
              <dt className="text-gray-600">Carboidratos</dt>
              <dd className="text-right tabular-nums">
                {number(total.carbohydrates, 1)} {plan.goal_carbohydrates ? `/ ${number(plan.goal_carbohydrates)}` : ''} g
              </dd>
              <dt className="text-gray-600">Gorduras</dt>
              <dd className="text-right tabular-nums">
                {number(total.fat, 1)} {plan.goal_fat ? `/ ${number(plan.goal_fat)}` : ''} g
              </dd>
              <dt className="text-gray-600">Fibras</dt>
              <dd className="text-right tabular-nums">{number(total.fiber, 1)} g</dd>
            </dl>
            <div className="mt-4">
              <p className="mb-1 text-xs font-semibold uppercase text-gray-500">Distribuição das calorias dos macros</p>
              <div className="flex h-3 overflow-hidden rounded-full bg-navy-100" aria-hidden>
                <span className="bg-protein" style={{ width: `${share(total.protein, KCAL.protein)}%` }} />
                <span className="bg-carbs" style={{ width: `${share(total.carbohydrates, KCAL.carbohydrates)}%` }} />
                <span className="bg-fat" style={{ width: `${share(total.fat, KCAL.fat)}%` }} />
              </div>
              <p className="mt-1 text-xs text-gray-600">
                P {share(total.protein, KCAL.protein)}% · C {share(total.carbohydrates, KCAL.carbohydrates)}% · G {share(total.fat, KCAL.fat)}%
                (4/4/9 kcal por grama)
              </p>
            </div>
          </Card>

          <Card title="Metas">
            {editable ? (
              <form action={updatePlan} className="grid grid-cols-2 gap-3">
                <input type="hidden" name="back" value={here} />
                <input type="hidden" name="id" value={plan.id} />
                <div className="col-span-2">
                  <Field label="Descrição">
                    <input name="description" defaultValue={plan.description} maxLength={80} className={inputClass} />
                  </Field>
                </div>
                {(
                  [
                    ['goal_energy', 'Calorias (kcal)'],
                    ['goal_protein', 'Proteínas (g)'],
                    ['goal_carbohydrates', 'Carboidratos (g)'],
                    ['goal_fat', 'Gorduras (g)'],
                    ['goal_fiber', 'Fibras (g)'],
                    ['goal_water_ml', 'Água (ml)'],
                  ] as const
                ).map(([key, label]) => (
                  <Field key={key} label={label}>
                    <input name={key} inputMode="numeric" defaultValue={plan[key] ?? ''} className={inputClass} />
                  </Field>
                ))}
                <div className="col-span-2">
                  <Button type="submit">Salvar metas</Button>
                </div>
              </form>
            ) : (
              <p className="text-sm text-gray-700">
                {number(plan.goal_energy)} kcal · P {number(plan.goal_protein)} g · C {number(plan.goal_carbohydrates)} g · G {number(plan.goal_fat)} g · Fibras{' '}
                {number(plan.goal_fiber)} g · Água {number(plan.goal_water_ml)} ml
              </p>
            )}
            <p className="mt-3 text-xs text-gray-500">As metas são suas: não há distribuição padrão imposta pelo sistema.</p>
          </Card>

          <p className="px-1 text-xs text-gray-500">
            Valores por 100 g. Alimentos marcados como TACO: Tabela Brasileira de Composição de Alimentos, 4ª edição,
            NEPA/UNICAMP, 2011. Nutrientes que a tabela não informa aparecem como não informados.
          </p>
        </aside>
      </div>
    </div>
  );
}

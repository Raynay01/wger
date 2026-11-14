import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { SearchPicker } from '@/components/SearchPicker';
import { Badge, Button, Card, Empty, Field, inputClass, Notice } from '@/components/ui';
import { createFood, deleteFood, updateFood } from '@/app/pro/actions';
import { api } from '@/lib/api';
import { date, number } from '@/lib/format';
import { professionalContext } from '@/lib/roles';
import type { Paginated } from '@/lib/types';

export const metadata: Metadata = { title: 'Alimentos' };

type Food = {
  id: string;
  ingredient: number;
  organization: string;
  based_on: number | null;
  name: string;
  brand: string;
  energy: number;
  protein: string;
  carbohydrates: string;
  fat: string;
  fiber: string | null;
  sodium: string | null;
  in_use: boolean;
  author_name: string | null;
  created: string;
};

const HERE = '/pro/alimentos';

function ValueFields({ food, required }: { food?: Food; required: boolean }) {
  const sodiumMg = food?.sodium ? Math.round(Number(food.sodium) * 1000) : '';
  return (
    <>
      <Field label="Energia (kcal)">
        <input name="energy" inputMode="numeric" required={required} defaultValue={food?.energy ?? ''} className={inputClass} />
      </Field>
      <Field label="Proteínas (g)">
        <input name="protein" inputMode="decimal" required={required} defaultValue={food ? Number(food.protein) : ''} className={inputClass} />
      </Field>
      <Field label="Carboidratos (g)">
        <input name="carbohydrates" inputMode="decimal" required={required} defaultValue={food ? Number(food.carbohydrates) : ''} className={inputClass} />
      </Field>
      <Field label="Gorduras (g)">
        <input name="fat" inputMode="decimal" required={required} defaultValue={food ? Number(food.fat) : ''} className={inputClass} />
      </Field>
      <Field label="Fibras (g)">
        <input name="fiber" inputMode="decimal" defaultValue={food?.fiber ? Number(food.fiber) : ''} className={inputClass} />
      </Field>
      <Field label="Sódio (mg)">
        <input name="sodium_mg" inputMode="numeric" defaultValue={sodiumMg} className={inputClass} />
      </Field>
    </>
  );
}

export default async function FoodsPage({ searchParams }: { searchParams: Promise<{ erro?: string; salvo?: string }> }) {
  const { erro, salvo } = await searchParams;
  const [{ organizations, registrations }, foods] = await Promise.all([
    professionalContext(),
    api<Paginated<Food>>('professional-food/', { query: { limit: 200 } }),
  ]);
  const canAdd = organizations.length > 0 && registrations.some(r => r.discipline === 'nutrition' && r.status !== 'rejected');

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Alimentos cadastrados</h1>
        <p className="mt-1 max-w-3xl text-sm text-gray-600">
          Cadastre produtos e preparações que faltam na base, ou corrija um alimento existente. Os alimentos ficam disponíveis para
          todos, marcados como cadastro profissional da sua organização; o original nunca é alterado. Valores por 100 g.
        </p>
      </div>
      <ErrorFromQuery erro={erro} />
      {salvo && <Notice tone="success">Alimento salvo.</Notice>}

      {canAdd ? (
        <Card title="Novo alimento">
          <form action={createFood} className="grid gap-3 sm:grid-cols-3">
            <input type="hidden" name="back" value={HERE} />
            {organizations.length > 1 ? (
              <Field label="Organização">
                <select name="organization" className={inputClass}>
                  {organizations.map(o => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <input type="hidden" name="organization" value={organizations[0].id} />
            )}
            <div className="sm:col-span-3">
              <SearchPicker kind="food" name="based_on" label="Corrigir um alimento existente (opcional)" required={false} />
              <p className="mt-1 text-xs text-gray-500">Numa correção, os campos deixados em branco ficam com os valores do original.</p>
            </div>
            <Field label="Nome">
              <input name="name" required maxLength={200} placeholder="Ex.: Pão de queijo, padaria X" className={inputClass} />
            </Field>
            <Field label="Marca (opcional)">
              <input name="brand" maxLength={200} className={inputClass} />
            </Field>
            <div className="hidden sm:block" />
            <ValueFields required={false} />
            <div className="sm:col-span-3">
              <Button type="submit" variant="secondary">
                Cadastrar alimento
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <Notice>Somente nutricionistas com CRN informado e uma organização podem cadastrar alimentos (veja Configurações).</Notice>
      )}

      <Card title="Alimentos da sua organização">
        {foods.results.length === 0 ? (
          <Empty title="Nenhum alimento cadastrado ainda" />
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {foods.results.map(food => (
              <li key={food.id} className="py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <span className="font-semibold">
                    {food.name}
                    {food.brand && <span className="ml-1 text-sm font-normal text-gray-500">({food.brand})</span>}
                  </span>
                  <span className="flex items-center gap-2">
                    {food.based_on && <Badge tone="gray">Correção</Badge>}
                    {food.in_use ? <Badge tone="neon">Em uso</Badge> : <Badge tone="amber">Editável</Badge>}
                  </span>
                </div>
                <p className="text-sm tabular-nums text-gray-600">
                  {number(food.energy)} kcal · P {number(food.protein, 1)} g · C {number(food.carbohydrates, 1)} g · G {number(food.fat, 1)} g
                  {food.fiber !== null && ` · fibras ${number(food.fiber, 1)} g`}
                  {food.sodium !== null && ` · sódio ${number(Number(food.sodium) * 1000)} mg`}
                </p>
                <p className="text-xs text-gray-500">
                  {food.author_name ?? 'Profissional'} · {date(food.created)}
                </p>
                {food.in_use ? (
                  <p className="mt-1 text-xs text-gray-500">Usado em dietas publicadas ou diários: para mudar valores, cadastre um novo alimento.</p>
                ) : (
                  <details className="mt-2 text-sm">
                    <summary className="cursor-pointer text-navy-700">Editar ou excluir</summary>
                    <form action={updateFood} className="mt-3 grid gap-3 sm:grid-cols-3">
                      <input type="hidden" name="back" value={HERE} />
                      <input type="hidden" name="id" value={food.id} />
                      <Field label="Nome">
                        <input name="name" required maxLength={200} defaultValue={food.name} className={inputClass} />
                      </Field>
                      <Field label="Marca">
                        <input name="brand" maxLength={200} defaultValue={food.brand} className={inputClass} />
                      </Field>
                      <div className="hidden sm:block" />
                      <ValueFields food={food} required />
                      <div className="flex gap-2 sm:col-span-3">
                        <Button type="submit">Salvar</Button>
                      </div>
                    </form>
                    <form action={deleteFood} className="mt-2">
                      <input type="hidden" name="back" value={HERE} />
                      <input type="hidden" name="id" value={food.id} />
                      <Button variant="danger">Excluir</Button>
                    </form>
                  </details>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

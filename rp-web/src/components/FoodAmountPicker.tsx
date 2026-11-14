'use client';

import { useEffect, useState } from 'react';
import { SearchPicker } from './SearchPicker';
import { Field, inputClass } from './ui';

type Unit = { id: number; name: string; gram: number };

/**
 * Food search plus the amount, in grams or in one of the food's household
 * measures (colher de sopa, concha, ...). Fills ingredient, weight_unit and amount.
 */
export function FoodAmountPicker({ label = 'Adicionar alimento' }: { label?: string }) {
  const [food, setFood] = useState<number | null>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [unit, setUnit] = useState('');

  useEffect(() => {
    setUnit('');
    setUnits([]);
    if (!food) {
      return;
    }
    const controller = new AbortController();
    fetch(`/api/busca/medidas?ingrediente=${food}`, { signal: controller.signal })
      .then(r => (r.ok ? r.json() : []))
      .then(setUnits)
      .catch(() => {});
    return () => controller.abort();
  }, [food]);

  const chosen = units.find(u => String(u.id) === unit);

  return (
    <>
      <SearchPicker kind="food" name="ingredient" label={label} placeholder="Buscar por nome ou código de barras" onChange={setFood} />
      <Field label="Medida">
        <select name="weight_unit" value={unit} onChange={e => setUnit(e.target.value)} className={inputClass} disabled={units.length === 0}>
          <option value="">gramas</option>
          {units.map(u => (
            <option key={u.id} value={u.id}>
              {u.name} ({u.gram} g)
            </option>
          ))}
        </select>
      </Field>
      <Field label={chosen ? 'Quantidade' : 'Gramas'} hint={chosen ? `1 ${chosen.name} = ${chosen.gram} g` : undefined}>
        <input name="amount" required inputMode="decimal" className={inputClass} />
      </Field>
    </>
  );
}

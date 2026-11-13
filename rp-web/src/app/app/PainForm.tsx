'use client';

import { useActionState, useState } from 'react';
import { Button, Field, inputClass, Notice } from '@/components/ui';
import { MOMENT_LABELS } from '@/lib/format';
import { recordPain } from './actions';

/** Numeric rating scale from 0 (no pain) to 10 (worst imaginable) */
export function PainForm({ protocols }: { protocols: { id: string; name: string; moments: string[] }[] }) {
  const [state, action, pending] = useActionState(recordPain, undefined);
  const [protocol, setProtocol] = useState(protocols[0]?.id ?? '');
  const moments = protocols.find(p => p.id === protocol)?.moments ?? ['other'];

  return (
    <form action={action} className="flex flex-col gap-3">
      {protocols.length > 1 && (
        <Field label="Protocolo">
          <select name="protocol" value={protocol} onChange={e => setProtocol(e.target.value)} className={inputClass}>
            {protocols.map(p => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
      )}
      {protocols.length === 1 && <input type="hidden" name="protocol" value={protocol} />}
      <Field label="Momento">
        <select name="moment" className={inputClass}>
          {[...moments, 'other'].filter((m, i, a) => a.indexOf(m) === i).map(m => (
            <option key={m} value={m}>
              {MOMENT_LABELS[m]}
            </option>
          ))}
        </select>
      </Field>
      <fieldset>
        <legend className="mb-1 text-sm font-medium text-navy-800">Intensidade (0 = sem dor, 10 = pior dor imaginável)</legend>
        <div className="grid grid-cols-11 gap-1">
          {Array.from({ length: 11 }, (_, value) => (
            <label key={value} className="relative">
              <input type="radio" name="value" value={value} required className="peer sr-only" />
              <span
                className={`grid h-9 cursor-pointer place-items-center rounded-lg border text-sm font-semibold tabular-nums peer-checked:ring-2 peer-checked:ring-navy-900 peer-focus-visible:ring-2 ${
                  value <= 3 ? 'border-neon-500/50 bg-neon-100' : value <= 6 ? 'border-amber-200 bg-amber-50' : 'border-red-200 bg-red-50'
                }`}
              >
                {value}
              </span>
            </label>
          ))}
        </div>
      </fieldset>
      <Field label="Local da dor (opcional)">
        <input name="body_region" maxLength={50} className={inputClass} placeholder="Ex.: joelho direito" />
      </Field>
      <Button type="submit" disabled={pending}>
        Registrar
      </Button>
      {state?.error && <Notice tone="error">{state.error}</Notice>}
      {state?.ok && <Notice tone="success">{state.ok}</Notice>}
    </form>
  );
}

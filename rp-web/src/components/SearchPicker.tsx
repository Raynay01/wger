'use client';

import { useEffect, useId, useState } from 'react';
import { inputClass } from './ui';

type Option = { id: number; name: string; detail?: string };

function describe(kind: 'food' | 'exercise', item: any): string | undefined {
  if (kind === 'food') {
    const brand = item.brand ? `${item.brand} · ` : '';
    return `${brand}${Math.round(item.energy)} kcal · P ${item.protein} g · C ${item.carbohydrates} g · G ${item.fat} g (100 g)`;
  }
  return undefined;
}

/**
 * Search box that fills a hidden input with the chosen id, for foods or exercises
 */
export function SearchPicker({
  kind,
  name,
  label,
  placeholder,
  required = true,
  nameField,
}: {
  kind: 'food' | 'exercise';
  name: string;
  label: string;
  placeholder?: string;
  required?: boolean;
  nameField?: string;
}) {
  const endpoint = kind === 'food' ? '/api/busca/alimentos' : '/api/busca/exercicios';
  const [term, setTerm] = useState('');
  const [options, setOptions] = useState<Option[]>([]);
  const [chosen, setChosen] = useState<Option | null>(null);
  const listId = useId();

  useEffect(() => {
    if (chosen || term.trim().length < 2) {
      setOptions([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      const response = await fetch(`${endpoint}?q=${encodeURIComponent(term)}`, { signal: controller.signal }).catch(() => null);
      if (response?.ok) {
        const items = await response.json();
        setOptions(items.map((item: any) => ({ id: item.id, name: item.name, detail: describe(kind, item) })));
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [term, chosen, endpoint, kind]);

  return (
    <div className="relative flex flex-col gap-1 text-sm">
      <label htmlFor={listId} className="font-medium text-navy-800">
        {label}
      </label>
      <input type="hidden" name={name} value={chosen?.id ?? ''} />
      {nameField && <input type="hidden" name={nameField} value={chosen?.name ?? ''} />}
      <input
        id={listId}
        value={chosen ? chosen.name : term}
        onChange={e => {
          setChosen(null);
          setTerm(e.target.value);
        }}
        placeholder={placeholder}
        required={required}
        autoComplete="off"
        role="combobox"
        aria-expanded={options.length > 0}
        aria-controls={`${listId}-list`}
        className={inputClass}
      />
      {options.length > 0 && (
        <ul id={`${listId}-list`} role="listbox" className="absolute top-full z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-navy-100 bg-white shadow-lg">
          {options.map(option => (
            <li key={option.id} role="option" aria-selected={false}>
              <button
                type="button"
                onClick={() => {
                  setChosen(option);
                  setOptions([]);
                }}
                className="flex w-full flex-col items-start px-3 py-2 text-left hover:bg-navy-100"
              >
                <span className="font-medium">{option.name}</span>
                {option.detail && <span className="text-xs text-gray-500">{option.detail}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

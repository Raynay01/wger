import 'server-only';

import { api } from './api';
import { exerciseNames } from './catalog';
import type { Paginated, Routine } from './types';

type Structure = { days: { slots: { entries: { exercise: number }[] }[] }[] };

/** The exercises of the published routines of a training follow-up, by name */
export async function routineExercises(relationship: string): Promise<{ id: number; name: string }[]> {
  const routines = await api<Paginated<Routine>>('routine/', {
    query: { care_relationship: relationship, status: 'published', limit: 20 },
  });
  const [structures, names] = await Promise.all([
    Promise.all(routines.results.map(routine => api<Structure>(`routine/${routine.id}/structure/`))),
    exerciseNames(),
  ]);
  const ids = new Set(structures.flatMap(s => s.days.flatMap(d => d.slots.flatMap(slot => slot.entries.map(e => e.exercise)))));
  return [...ids]
    .map(id => ({ id, name: names.get(id) ?? `Exercício ${id}` }))
    .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}

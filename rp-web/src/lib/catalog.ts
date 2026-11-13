import 'server-only';

import { apiUrl } from './session';

const PORTUGUESE = 7;
const ENGLISH = 2;

type Translation = { exercise: number; name: string; language: number };

let cache: { at: number; names: Map<number, string> } | null = null;

async function fetchLanguage(language: number): Promise<Translation[]> {
  const out: Translation[] = [];
  let url: string | null = `${apiUrl()}/api/v2/exercise-translation/?language=${language}&limit=500`;
  while (url) {
    const response: Response = await fetch(url, { next: { revalidate: 86400 } });
    if (!response.ok) {
      break;
    }
    const page = await response.json();
    out.push(...page.results.map((t: any) => ({ exercise: t.exercise, name: t.name, language })));
    url = page.next ? page.next.replace(/^https?:\/\/[^/]+/, apiUrl()) : null;
  }
  return out;
}

/** Exercise names of the public library, Portuguese where available */
export async function exerciseNames(): Promise<Map<number, string>> {
  if (cache && Date.now() - cache.at < 60 * 60 * 1000) {
    return cache.names;
  }
  const [english, portuguese] = await Promise.all([fetchLanguage(ENGLISH), fetchLanguage(PORTUGUESE)]);
  const names = new Map<number, string>();
  for (const t of [...english, ...portuguese]) {
    names.set(t.exercise, t.name);
  }
  cache = { at: Date.now(), names };
  return names;
}

function normalize(value: string): string {
  return value.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

export async function searchExercises(term: string, limit = 20): Promise<{ id: number; name: string }[]> {
  const needle = normalize(term.trim());
  if (needle.length < 2) {
    return [];
  }
  const names = await exerciseNames();
  const out: { id: number; name: string }[] = [];
  for (const [id, name] of names) {
    if (normalize(name).includes(needle)) {
      out.push({ id, name });
    }
  }
  out.sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
  return out.slice(0, limit);
}

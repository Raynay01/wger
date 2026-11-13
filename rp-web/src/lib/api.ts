import 'server-only';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { ACCESS_COOKIE, apiUrl } from './session';

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: unknown,
  ) {
    super(`API error ${status}`);
  }

  /** A readable message from a DRF error response */
  get message(): string {
    return describeErrors(this.data) || 'Algo deu errado. Tente novamente.';
  }
}

function describeErrors(data: unknown): string {
  if (!data) {
    return '';
  }
  if (typeof data === 'string') {
    return data;
  }
  if (Array.isArray(data)) {
    return data.map(describeErrors).filter(Boolean).join(' ');
  }
  if (typeof data === 'object') {
    const record = data as Record<string, unknown>;
    if (typeof record.detail === 'string') {
      return record.detail;
    }
    return Object.values(record).map(describeErrors).filter(Boolean).join(' ');
  }
  return String(data);
}

type Options = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
};

/** Calls the API as the logged-in user. Without a session, sends the user to the login. */
export async function api<T = any>(path: string, options: Options = {}): Promise<T> {
  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  if (!access) {
    redirect('/entrar');
  }

  const url = new URL(`${apiUrl()}/api/v2/${path.replace(/^\//, '')}`);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url, {
    method: options.method ?? 'GET',
    headers: {
      'Authorization': `Bearer ${access}`,
      'Accept': 'application/json',
      'Accept-Language': 'pt-BR',
      ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: 'no-store',
  });

  if (response.status === 401) {
    redirect('/entrar');
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data as T;
}

/** Fetches every page of a list endpoint */
export async function apiList<T = any>(path: string, query: Options['query'] = {}): Promise<T[]> {
  const out: T[] = [];
  let offset = 0;
  for (;;) {
    const page = await api<{ results: T[]; next: string | null }>(path, {
      query: { ...query, limit: 100, offset },
    });
    out.push(...page.results);
    if (!page.next || page.results.length === 0) {
      return out;
    }
    offset += page.results.length;
  }
}

/** The error message of a failed call, for forms */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  throw error;
}

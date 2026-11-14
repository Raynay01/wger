import { NextResponse } from 'next/server';
import { api } from '@/lib/api';

type WeightUnit = { id: number; name: string; amount: number; gram: number };

/** Household measures (colher de sopa, concha, ...) of a food */
export async function GET(request: Request) {
  const ingredient = new URL(request.url).searchParams.get('ingrediente') ?? '';
  if (!/^\d+$/.test(ingredient)) {
    return NextResponse.json([]);
  }
  const page = await api<{ results: WeightUnit[] }>('ingredientweightunit/', { query: { ingredient, limit: 50 } });
  return NextResponse.json(page.results.map(u => ({ id: u.id, name: u.name, gram: u.gram })));
}

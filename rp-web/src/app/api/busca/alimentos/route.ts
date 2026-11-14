import { NextResponse } from 'next/server';
import { api } from '@/lib/api';

type Ingredient = {
  id: number;
  name: string;
  brand: string;
  energy: number;
  protein: string;
  carbohydrates: string;
  fat: string;
  fiber: string | null;
  source_name: string;
  license_author: string;
};

/** Food search for the diet builder, values per 100 g */
export async function GET(request: Request) {
  const term = new URL(request.url).searchParams.get('q')?.trim() ?? '';
  if (term.length < 2) {
    return NextResponse.json([]);
  }
  const page = await api<{ results: Ingredient[] }>('ingredient/', { query: { name__search: term, limit: 20 } });
  return NextResponse.json(
    page.results.map(i => ({
      id: i.id,
      name: i.name,
      brand: i.brand,
      energy: i.energy,
      protein: Number(i.protein),
      carbohydrates: Number(i.carbohydrates),
      fat: Number(i.fat),
      source: i.source_name === 'Cadastro profissional' ? `Cadastro profissional (${i.license_author})` : i.source_name,
    })),
  );
}

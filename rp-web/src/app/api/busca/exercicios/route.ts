import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { searchExercises } from '@/lib/catalog';
import { ACCESS_COOKIE } from '@/lib/session';

export async function GET(request: Request) {
  if (!(await cookies()).get(ACCESS_COOKIE)) {
    return NextResponse.json([], { status: 401 });
  }
  const term = new URL(request.url).searchParams.get('q') ?? '';
  return NextResponse.json(await searchExercises(term));
}

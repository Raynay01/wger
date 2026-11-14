import { NextResponse } from 'next/server';
import { api } from '@/lib/api';
import { ZONE_COOKIE, validZone } from '@/lib/zone';

/**
 * Stores the browser's timezone in the user's profile: the API counts the
 * calendar days of Meu Dia, diaries and agenda in this zone.
 */
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const zone = typeof body.zone === 'string' ? body.zone : '';
  if (!zone || validZone(zone) !== zone) {
    return NextResponse.json({ message: 'Fuso horário inválido.' }, { status: 400 });
  }
  await api('userprofile/', { method: 'PATCH', body: { time_zone: zone } });
  const response = NextResponse.json({ ok: true });
  response.cookies.set(ZONE_COOKIE, zone, { path: '/', sameSite: 'lax', maxAge: 60 * 60 * 24 * 365 });
  return response;
}

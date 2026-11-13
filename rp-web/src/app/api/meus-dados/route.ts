import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { ACCESS_COOKIE, apiUrl } from '@/lib/session';

/** Downloads the user's data export (LGPD) as a JSON file */
export async function GET() {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) {
    return NextResponse.json({ message: 'Entre novamente.' }, { status: 401 });
  }
  const response = await fetch(`${apiUrl()}/api/v2/care/my-data/?format=json`, {
    headers: { Authorization: `Bearer ${access}`, Accept: 'application/json' },
    cache: 'no-store',
  });
  if (!response.ok) {
    return NextResponse.json({ message: 'Não foi possível gerar o arquivo.' }, { status: response.status });
  }
  return new NextResponse(response.body, {
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Content-Disposition': response.headers.get('Content-Disposition') ?? 'attachment; filename="meus-dados.json"',
      'Cache-Control': 'no-store',
    },
  });
}

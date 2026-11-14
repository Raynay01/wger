import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { MAX_UPLOAD_BYTES } from '@/lib/chat';
import { ACCESS_COOKIE, apiUrl, secondsLeft } from '@/lib/session';

/**
 * Sends a chat message. The multipart body (text and an optional photo or
 * video) streams to the API as it is, which validates it.
 */
export async function POST(request: Request) {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (secondsLeft(access) <= 0) {
    return NextResponse.json({ message: 'Sua sessão expirou. Recarregue a página.' }, { status: 401 });
  }
  const length = Number(request.headers.get('content-length') ?? 0);
  if (length > MAX_UPLOAD_BYTES) {
    return NextResponse.json({ message: 'O arquivo passa do limite de 50 MB.' }, { status: 413 });
  }

  const upstream = await fetch(`${apiUrl()}/api/v2/care-message/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${access}`,
      'Accept': 'application/json',
      'Accept-Language': 'pt-BR',
      'Content-Type': request.headers.get('content-type') ?? '',
      ...(length ? { 'Content-Length': String(length) } : {}),
    },
    body: request.body,
    // @ts-expect-error: required by Node's fetch for a streamed body
    duplex: 'half',
  });
  const data = await upstream.json().catch(() => null);
  return NextResponse.json(data, { status: upstream.status });
}

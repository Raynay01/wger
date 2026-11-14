import { cookies } from 'next/headers';
import { ACCESS_COOKIE, apiUrl } from '@/lib/session';

const PASSED_ON = [
  'content-type',
  'content-length',
  'content-range',
  'accept-ranges',
  'content-disposition',
  'cache-control',
  'x-content-type-options',
];

/** The photo or video of a chat message, with range requests for videos */
export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) {
    return new Response(null, { status: 404 });
  }
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!access) {
    return new Response(null, { status: 401 });
  }
  const range = request.headers.get('range');
  const upstream = await fetch(`${apiUrl()}/api/v2/care-message/${id}/attachment/`, {
    headers: { Authorization: `Bearer ${access}`, ...(range ? { Range: range } : {}) },
    cache: 'no-store',
  });
  const headers = new Headers();
  for (const name of PASSED_ON) {
    const value = upstream.headers.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  return new Response(upstream.ok ? upstream.body : null, { status: upstream.status, headers });
}

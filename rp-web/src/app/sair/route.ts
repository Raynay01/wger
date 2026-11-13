import { seeOther } from '@/lib/redirect';
import { ACCESS_COOKIE, REFRESH_COOKIE } from '@/lib/session';

export async function POST() {
  const response = seeOther('/');
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}

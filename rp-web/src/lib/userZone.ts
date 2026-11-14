import 'server-only';

import { cookies } from 'next/headers';
import { validZone, ZONE_COOKIE } from './zone';

/** The timezone the user's browser reported */
export async function userZone(): Promise<string> {
  return validZone((await cookies()).get(ZONE_COOKIE)?.value);
}

// Timezone helpers. The browser reports its zone (cookie kn_tz, also stored in
// the user's profile, which the API uses for calendar days).

export const ZONE_COOKIE = 'kn_tz';
export const DEFAULT_ZONE = 'America/Sao_Paulo';

export function validZone(zone: string | undefined | null): string {
  if (!zone) {
    return DEFAULT_ZONE;
  }
  try {
    new Intl.DateTimeFormat('en-US', { timeZone: zone });
    return zone;
  } catch {
    return DEFAULT_ZONE;
  }
}

/** Offset of the zone at the given instant, in minutes east of UTC */
function offsetMinutes(instant: Date, zone: string): number {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: zone,
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(instant);
  const get = (type: string) => Number(parts.find(p => p.type === type)?.value);
  const asUtc = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'));
  return Math.round((asUtc - instant.getTime()) / 60000);
}

/** "2026-03-10T14:00" in the given zone as an ISO instant */
export function zonedToUtcIso(local: string, zone: string): string {
  const [datePart, timePart = '00:00'] = local.split('T');
  const [y, m, d] = datePart.split('-').map(Number);
  const [hh, mm] = timePart.split(':').map(Number);
  const guess = Date.UTC(y, m - 1, d, hh, mm);
  // Two passes settle the offset also next to a DST switch
  let instant = guess - offsetMinutes(new Date(guess), zone) * 60000;
  instant = guess - offsetMinutes(new Date(instant), zone) * 60000;
  return new Date(instant).toISOString();
}

export function formatTime(iso: string, zone: string): string {
  return new Date(iso).toLocaleTimeString('pt-BR', { timeZone: zone, hour: '2-digit', minute: '2-digit' });
}

export function formatDateTime(iso: string, zone: string): string {
  return new Date(iso).toLocaleString('pt-BR', {
    timeZone: zone,
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Today's date (YYYY-MM-DD) in the zone */
export function todayIn(zone: string): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: zone }).format(new Date());
}

'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

/** Reports the browser's timezone once, and again when it changes (e.g. travel) */
export function TimezoneSync({ current }: { current: string | null }) {
  const router = useRouter();
  useEffect(() => {
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!zone || zone === current) {
      return;
    }
    fetch('/api/perfil/fuso', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zone }),
    })
      .then(response => {
        // The page computed "today" with the old zone
        if (response.ok) {
          router.refresh();
        }
      })
      .catch(() => {});
  }, [current, router]);
  return null;
}

'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

/** Reloads the server data periodically while the tab is visible */
export function AutoRefresh({ seconds }: { seconds: number }) {
  const router = useRouter();
  useEffect(() => {
    const timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        router.refresh();
      }
    }, seconds * 1000);
    return () => clearInterval(timer);
  }, [router, seconds]);
  return null;
}

/** Reloads once, e.g. so the menu badge drops what this page just marked as read */
export function RefreshOnce() {
  const router = useRouter();
  useEffect(() => {
    router.refresh();
  }, [router]);
  return null;
}

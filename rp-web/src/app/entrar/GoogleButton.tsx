'use client';

import { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    google?: any;
  }
}

/**
 * "Sign in with Google" button from Google Identity Services. Google hands the
 * browser an ID token, which our server exchanges for a session with the API.
 */
export function GoogleButton({ clientId }: { clientId: string }) {
  const container = useRef<HTMLDivElement>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onCredential = async (response: { credential: string }) => {
      setBusy(true);
      setError('');
      const result = await fetch('/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential }),
      });
      if (result.ok) {
        window.location.href = '/inicio';
        return;
      }
      const json = await result.json().catch(() => ({}));
      setError(json.message || 'Não foi possível entrar com o Google.');
      setBusy(false);
    };

    const render = () => {
      if (!window.google || !container.current) {
        return;
      }
      window.google.accounts.id.initialize({ client_id: clientId, callback: onCredential, ux_mode: 'popup' });
      window.google.accounts.id.renderButton(container.current, {
        theme: 'filled_black',
        size: 'large',
        shape: 'pill',
        text: 'continue_with',
        locale: 'pt-BR',
        width: 300,
      });
    };

    if (window.google) {
      render();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = render;
    script.onerror = () => setError('Não foi possível carregar o login do Google.');
    document.head.appendChild(script);
  }, [clientId]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div ref={container} aria-busy={busy} />
      {busy && <p className="text-sm text-gray-600">Entrando…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}

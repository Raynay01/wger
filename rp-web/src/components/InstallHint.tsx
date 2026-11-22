'use client';

import { useEffect, useState } from 'react';
import { APP_NAME } from '@/lib/brand';

const DISMISSED = 'almova-install-hint-dismissed';

/** Chrome's install event, not in the DOM types yet */
type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };

/**
 * Offers to install the site as an app on the phone: Android's install
 * dialog, or the steps of the share menu on the iPhone. Hidden when the app
 * is already installed or the person closed the hint.
 */
export function InstallHint() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [iphone, setIphone] = useState(false);
  const [hidden, setHidden] = useState(true);

  useEffect(() => {
    const installed =
      window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;
    if (installed || localStorage.getItem(DISMISSED)) {
      return;
    }
    // Safari on iPhone and iPad has no install event: the hint shows the steps
    const ua = navigator.userAgent;
    const apple = /iPhone|iPad|iPod/.test(ua) || (ua.includes('Macintosh') && navigator.maxTouchPoints > 1);
    if (apple && /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS/.test(ua)) {
      setIphone(true);
      setHidden(false);
    }
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setPrompt(event as InstallPrompt);
      setHidden(false);
    };
    const onInstalled = () => setHidden(true);
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, []);

  if (hidden) {
    return null;
  }

  function dismiss() {
    localStorage.setItem(DISMISSED, '1');
    setHidden(true);
  }

  async function install() {
    if (!prompt) {
      return;
    }
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    setPrompt(null);
    if (outcome === 'accepted') {
      setHidden(true);
    }
  }

  return (
    <aside
      aria-label={`Instalar o ${APP_NAME}`}
      className="mb-5 flex flex-col gap-3 rounded-2xl border border-neon-500/40 bg-neon-100 px-4 py-3 text-sm text-navy-900"
    >
      {/* The buttons get their own line: beside the text they squeeze it on a phone */}
      <div className="flex items-start gap-3">
        <span aria-hidden className="grid size-9 shrink-0 place-items-center rounded-lg bg-neon-500 font-bold">
          A
        </span>
        <p className="min-w-0 flex-1">
          <strong>Use o {APP_NAME} como app.</strong>{' '}
          {iphone ? (
            <>
              No Safari, toque em <strong>Compartilhar</strong> e depois em <strong>Adicionar à Tela de Início</strong>.
            </>
          ) : (
            'Ele fica na tela inicial do celular e abre em tela cheia.'
          )}
        </p>
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" onClick={dismiss} className="rounded-xl px-3 py-2 text-navy-700 hover:bg-white/60">
          Agora não
        </button>
        {prompt && (
          <button
            type="button"
            onClick={install}
            className="rounded-xl bg-navy-900 px-4 py-2 font-semibold text-white hover:bg-navy-700"
          >
            Instalar o app
          </button>
        )}
      </div>
    </aside>
  );
}

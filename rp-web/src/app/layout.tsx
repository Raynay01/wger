import type { Metadata, Viewport } from 'next';
import { connection } from 'next/server';
import { APP_NAME, APP_TAGLINE } from '@/lib/brand';
import './globals.css';

export const metadata: Metadata = {
  title: { default: `${APP_NAME} · ${APP_TAGLINE}`, template: `%s · ${APP_NAME}` },
  description: `${APP_NAME}: treino, fisioterapia e nutrição no mesmo app, com os seus profissionais.`,
};

export const viewport: Viewport = {
  themeColor: '#0b1f3a',
  width: 'device-width',
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Every page renders per request, so its scripts get the nonce of the Content Security Policy
  await connection();
  return (
    <html lang="pt-BR">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}

import type { MetadataRoute } from 'next';
import { APP_NAME } from '@/lib/brand';

/** Makes the site installable on the phone's home screen (PWA) */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: APP_NAME,
    short_name: APP_NAME,
    description: 'Treino, fisioterapia e nutrição com seus profissionais, num só app.',
    lang: 'pt-BR',
    // The start page sends each person to their area, or to the login
    start_url: '/inicio',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#0b1f3a',
    theme_color: '#0b1f3a',
    categories: ['health', 'fitness', 'medical'],
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
}

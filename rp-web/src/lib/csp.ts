/**
 * Content Security Policy of the web app. Scripts and Next's inline styles
 * need the nonce of the request; Google's sign-in button is the only outside
 * source.
 */
export function contentSecurityPolicy(nonce: string, production: boolean): string {
  const google = 'https://accounts.google.com/gsi/';
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic' ${google}client${production ? '' : " 'unsafe-eval'"}`,
    // The dev tools of `next dev` inject styles without a nonce; a nonce would void 'unsafe-inline'
    `style-src 'self' ${production ? `'nonce-${nonce}'` : "'unsafe-inline'"} ${google}style`,
    // style="" attributes (widths of progress bars), which nonces don't cover
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' blob: data:",
    "font-src 'self'",
    `connect-src 'self' ${google}${production ? '' : ' ws: wss:'}`,
    `frame-src ${google}`,
    "media-src 'self' blob:",
    // The service worker of the installable app (public/sw.js); script-src's
    // 'strict-dynamic' would otherwise decide for it
    "worker-src 'self'",
    "manifest-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    ...(production ? ['upgrade-insecure-requests'] : []),
  ].join('; ');
}

export function newNonce(): string {
  return Buffer.from(crypto.randomUUID()).toString('base64');
}

// Icons of the installable web app (PWA) from the provisional ALMOVA mark,
// the "A" of the Android icon. With the official logo, change MARK and run:
//
//   node scripts/gerar-icones.mjs
//
// Needs Playwright (Chromium).

import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require('playwright');
} catch {
  playwright = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'));
}

const publicDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');
const NAVY = '#0b1f3a';
const NEON = '#39ff88';
// The "A" of the Android icon, in its 108 x 108 box
const MARK = 'M36,74L49.4,35H58.6L72,74H64.2L61.6,65.6H46.4L43.8,74ZM48.2,59.6H59.8L54,41.8Z';

/** The A on neon green; rounded corners on a transparent background, or a full square */
function svg(size, rounded) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 108 108" xmlns="http://www.w3.org/2000/svg">
    <rect width="108" height="108" ${rounded ? 'rx="24"' : ''} fill="${NEON}"/>
    <path d="${MARK}" fill="${NAVY}" transform="translate(54 54) scale(1.25) translate(-54 -54.5)"/>
  </svg>`;
}

// "any" icons have their own corners; the maskable one and Apple's are cut by the system
const icons = [
  ['icon-192.png', 192, true],
  ['icon-512.png', 512, true],
  ['icon-maskable-512.png', 512, false],
  ['apple-touch-icon.png', 180, false],
];

const browser = await playwright.chromium.launch();
for (const [name, size, rounded] of icons) {
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  await page.setContent(`<style>html,body{margin:0;background:transparent}</style>${svg(size, rounded)}`);
  await page.screenshot({ path: path.join(publicDir, name), omitBackground: rounded });
  await page.close();
  console.log(name);
}
await browser.close();

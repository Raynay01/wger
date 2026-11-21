// Play Store icon (512 x 512) and feature graphic (1024 x 500) from the
// provisional ALMOVA mark, the "A" of the Android icon. With the official
// logo, change MARK (and the texts) and run again:
//
//   node extras/flutter-almova/play-store/gerar-imagens.mjs
//
// Needs Playwright (Chromium). The Roboto of the Flutter SDK is used when
// FLUTTER_ROOT is set, the browser's sans-serif otherwise.

import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
let playwright;
try {
  playwright = require('playwright');
} catch {
  playwright = require(path.join(execSync('npm root -g').toString().trim(), 'playwright'));
}

const here = path.dirname(fileURLToPath(import.meta.url));
const NAVY = '#0b1f3a';
const NEON = '#39ff88';
// The "A" of android/app/src/main/res/drawable/ic_launcher_foreground.xml (108 x 108)
const MARK = 'M36,74L49.4,35H58.6L72,74H64.2L61.6,65.6H46.4L43.8,74ZM48.2,59.6H59.8L54,41.8Z';

const fonts = process.env.FLUTTER_ROOT
  ? path.join(process.env.FLUTTER_ROOT, 'bin/cache/artifacts/material_fonts')
  : '';
const fontFace = (weight, file) =>
  fonts && existsSync(path.join(fonts, file))
    ? `@font-face { font-family: Brand; font-weight: ${weight}; src: url('${pathToFileURL(path.join(fonts, file))}'); }`
    : '';
const style = `
  ${fontFace(400, 'Roboto-Regular.ttf')}
  ${fontFace(700, 'Roboto-Bold.ttf')}
  html, body { margin: 0; }
  body { font-family: Brand, Roboto, sans-serif; }
`;

const icon = `
  <style>${style}</style>
  <svg width="512" height="512" viewBox="0 0 108 108" xmlns="http://www.w3.org/2000/svg">
    <rect width="108" height="108" fill="${NEON}"/>
    <path d="${MARK}" fill="${NAVY}" transform="translate(54 54) scale(1.25) translate(-54 -54.5)"/>
  </svg>`;

const feature = `
  <style>${style}
    .page { width: 1024px; height: 500px; background: ${NAVY}; color: #fff; display: flex;
            align-items: center; gap: 56px; padding: 0 88px; box-sizing: border-box; }
    .name { font-size: 92px; font-weight: 700; letter-spacing: 2px; line-height: 1; }
    .tagline { margin-top: 22px; font-size: 34px; line-height: 1.3; color: #e6ecf5; }
    .tagline b { color: ${NEON}; font-weight: 700; }
  </style>
  <div class="page">
    <svg width="220" height="220" viewBox="0 0 108 108" xmlns="http://www.w3.org/2000/svg">
      <rect width="108" height="108" rx="24" fill="${NEON}"/>
      <path d="${MARK}" fill="${NAVY}" transform="translate(54 54) scale(1.25) translate(-54 -54.5)"/>
    </svg>
    <div>
      <div class="name">ALMOVA</div>
      <div class="tagline"><b>Treino, fisioterapia e nutrição</b><br>com seus profissionais, num só app.</div>
    </div>
  </div>`;

const browser = await playwright.chromium.launch();
for (const [name, html, width, height] of [
  ['icone-512', icon, 512, 512],
  ['destaque-1024x500', feature, 1024, 500],
]) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(here, `${name}.png`), clip: { x: 0, y: 0, width, height } });
  await page.close();
  console.log(`${name}.png`);
}
await browser.close();

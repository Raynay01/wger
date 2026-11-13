// End-to-end walk through the web app with real Django and Next.js servers.
//
// Needs: Django on KINUTRI_API_URL (local_dev settings, sample fixtures loaded),
// the web app on KINUTRI_WEB_URL with KINUTRI_DEV_LOGIN=1, and Playwright.
// Users are created fresh for every run through manage.py.

import { execFileSync, execSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
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

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '..', '..');
const WEB = process.env.KINUTRI_WEB_URL || 'http://127.0.0.1:3000';
const shots = path.join(here, 'screenshots');
mkdirSync(shots, { recursive: true });

const run = Date.now().toString(36);
const users = {
  bruno: `bruno_${run}`,
  carla: `carla_${run}`,
  ana: `ana_${run}`,
  dani: `dani_${run}`,
};
const PASSWORD = 'senha-forte-123';

execFileSync(
  'uv',
  [
    'run',
    './manage.py',
    'shell',
    '-c',
    `from django.contrib.auth.models import User\nfor u in ${JSON.stringify(Object.values(users))}:\n    User.objects.create_user(u, f'{u}@example.com', '${PASSWORD}', first_name=u.split('_')[0].title())`,
  ],
  { cwd: repo, env: { ...process.env, DJANGO_SETTINGS_MODULE: 'settings.local_dev' }, stdio: 'ignore' },
);

let step = 0;
function log(message) {
  step += 1;
  console.log(`${String(step).padStart(2, '0')}. ${message}`);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Falhou: ${message}`);
  }
}

const browser = await playwright.chromium.launch();
const errors = [];

async function session(name, viewport = { width: 1280, height: 900 }) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2, locale: 'pt-BR' });
  const page = await context.newPage();
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  await page.goto(`${WEB}/entrar`);
  if (!(await page.locator('input[name=username]').isVisible())) {
    await page.getByText('Acesso de desenvolvimento').click();
  }
  await page.fill('input[name=username]', users[name]);
  await page.fill('input[name=password]', PASSWORD);
  await page.click('form[action="/api/auth/password"] button[type=submit]');
  await page.waitForURL(/\/(app|inicio|pro)/);
  return page;
}

async function pick(page, label, term, scope = page) {
  const input = scope.getByLabel(label, { exact: true });
  await input.fill(term);
  const option = scope.getByRole('option').first();
  await option.waitFor({ timeout: 15000 });
  await option.locator('button').click();
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(shots, `${name}.png`), fullPage: true, caret: 'initial' });
}

try {
  // Professionals set up their organization and council registrations
  const bruno = await session('bruno');
  await bruno.goto(`${WEB}/pro/configurar`);
  await bruno.getByLabel('Nome (seu nome profissional ou da clínica)').fill('Bruno Nutrição e Treino');
  await bruno.getByRole('button', { name: 'Criar organização' }).click();
  await bruno.getByText('Bruno Nutrição e Treino').waitFor();
  for (const [discipline, number, shown] of [
    ['nutrition', '12345', 'CRN 12345/SP'],
    ['training', '67890-G', 'CREF 67890-G/SP'],
  ]) {
    await bruno.locator('select[name=discipline]').selectOption(discipline);
    await bruno.getByLabel('Número do registro').fill(number);
    await bruno.getByRole('button', { name: 'Adicionar' }).click();
    await bruno.getByText(shown).waitFor();
  }
  await shot(bruno, '01-configuracoes');
  log('Bruno criou a organização e registrou CRN e CREF');

  const carla = await session('carla');
  await carla.goto(`${WEB}/pro/configurar`);
  await carla.getByLabel('Nome (seu nome profissional ou da clínica)').fill('Clínica Carla Fisio');
  await carla.getByRole('button', { name: 'Criar organização' }).click();
  await carla.getByText('Clínica Carla Fisio').waitFor();
  await carla.locator('select[name=discipline]').selectOption('physio');
  await carla.getByLabel('Número do registro').fill('55555-F');
  await carla.getByRole('button', { name: 'Adicionar' }).click();
  await carla.getByText('CREFITO 55555-F/SP').waitFor();
  log('Carla criou a clínica e registrou o CREFITO');

  // Invitations
  for (const discipline of ['nutrition', 'training']) {
    await bruno.goto(`${WEB}/pro/pacientes/novo`);
    await bruno.getByLabel(/E-mail do paciente/).fill(`${users.ana}@example.com`);
    await bruno.locator('select[name=discipline]').selectOption(discipline);
    await bruno.getByRole('button', { name: 'Enviar convite' }).click();
    await bruno.getByText('Convite criado').waitFor();
  }
  await carla.goto(`${WEB}/pro/pacientes/novo`);
  await carla.getByLabel(/E-mail do paciente/).fill(`${users.ana}@example.com`);
  await carla.getByRole('button', { name: 'Enviar convite' }).click();
  await carla.getByText('Convite criado').waitFor();
  const inviteLink = await carla.getByLabel('Link do convite').inputValue();
  assert(inviteLink.includes('/convite/') && inviteLink.includes('token='), 'link de convite com token');
  log('Convites de nutrição, treino e fisioterapia criados');

  // Nothing is emailed until the professional asks for it
  assert(await carla.getByText('Ainda não enviado').isVisible(), 'convite ainda não enviado');
  await carla.getByRole('button', { name: 'Enviar convite por e-mail' }).click();
  await carla.getByText(/Convite enviado por e-mail para/).waitFor();
  await carla.getByText(/Último envio:/).waitFor();
  await carla.getByRole('button', { name: 'Reenviar por e-mail' }).click();
  await carla.getByText('O convite foi enviado há poucos minutos, aguarde um pouco.').waitFor();
  log('Carla enviou o convite por e-mail quando quis; o reenvio imediato foi bloqueado');

  // Invitation link for someone who logs in with another email address
  await bruno.goto(`${WEB}/pro/pacientes/novo`);
  await bruno.getByLabel(/E-mail do paciente/).fill(`outro.email.${run}@example.com`);
  await bruno.locator('select[name=discipline]').selectOption('nutrition');
  await bruno.getByRole('button', { name: 'Enviar convite' }).click();
  const daniLink = await bruno.getByLabel('Link do convite').inputValue();
  const visitor = await (await browser.newContext({ locale: 'pt-BR' })).newPage();
  await visitor.goto(daniLink.replace(/^https?:\/\/[^/]+/, WEB));
  await visitor.getByRole('link', { name: 'Entrar para aceitar' }).click();
  await visitor.fill('input[name=username]', users.dani);
  await visitor.fill('input[name=password]', PASSWORD);
  await visitor.click('form[action="/api/auth/password"] button[type=submit]');
  await visitor.waitForURL(/\/convite\//);
  await visitor.getByRole('button', { name: 'Aceitar e autorizar' }).click();
  await visitor.waitForURL(/compartilhamento/);
  await visitor.getByText(/Profissional de Educação Física|Nutricionista/).first().waitFor();
  log('Dani entrou pelo link do convite com outro e-mail, voltou ao convite e aceitou');

  // The patient accepts
  const ana = await session('ana');
  await ana.goto(`${WEB}/app/convites`);
  assert((await ana.getByRole('button', { name: 'Aceitar e autorizar' }).count()) === 3, 'três convites');
  await shot(ana, '02-convites');
  for (let i = 0; i < 3; i++) {
    await ana.goto(`${WEB}/app/convites`);
    await ana.getByRole('button', { name: 'Aceitar e autorizar' }).first().click();
    await ana.waitForURL(/compartilhamento/);
  }
  await ana.goto(`${WEB}/app/convites`);
  assert((await ana.getByRole('button', { name: 'Encerrar' }).count()) === 3, 'três profissionais ativos');
  log('Ana aceitou os três convites com consentimento');

  // Diet: draft, meal, foods, substitution, goals, publish
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Nutrição · desde/ }).first().click();
  await bruno.getByPlaceholder('Ex.: Hipertrofia').fill('Hipertrofia');
  await bruno.getByRole('button', { name: 'Criar rascunho' }).click();
  await bruno.waitForURL(/\/dieta\//);
  await bruno.getByLabel('Nome', { exact: true }).fill('Almoço');
  await bruno.locator('input[name=time]').fill('12:00');
  await bruno.getByRole('button', { name: 'Adicionar refeição' }).click();
  await bruno.getByRole('heading', { name: /Almoço/ }).waitFor();
  const lunch = bruno.locator('section', { has: bruno.getByRole('heading', { name: /Almoço/ }) });
  await pick(bruno, 'Adicionar alimento', 'test', lunch);
  await lunch.getByLabel('Gramas').fill('150');
  await lunch.getByRole('button', { name: 'Adicionar' }).click();
  await bruno.waitForLoadState('networkidle');
  const lunch2 = bruno.locator('section', { has: bruno.getByRole('heading', { name: /Almoço/ }) });
  await lunch2.getByText('+ substituição').click();
  await pick(bruno, 'Alimento', 'organic', lunch2);
  await lunch2.locator('details').getByLabel('Gramas').fill('120');
  await lunch2.locator('details').getByRole('button', { name: 'Adicionar' }).click();
  await bruno.getByText(/ou 120 g de/).waitFor();
  await bruno.getByLabel('Calorias (kcal)').fill('2400');
  await bruno.getByLabel('Proteínas (g)').fill('160');
  await bruno.getByLabel('Água (ml)').fill('2500');
  await bruno.getByRole('button', { name: 'Salvar metas' }).click();
  await bruno.waitForLoadState('networkidle');
  await shot(bruno, '03-construtor-dieta');
  await bruno.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await bruno.getByRole('button', { name: 'Criar nova versão para editar' }).waitFor();
  const dietUrl = bruno.url();
  log('Bruno montou e publicou a dieta (refeição, alimento, substituição, metas)');

  // Training: draft, day, exercise, publish
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Treino · desde/ }).first().click();
  await bruno.getByPlaceholder('Ex.: Força A/B').fill('Força');
  await bruno.getByRole('button', { name: 'Criar rascunho' }).click();
  await bruno.waitForURL(/\/treino\//);
  await bruno.getByLabel('Nome do dia').fill('Pernas');
  await bruno.getByRole('button', { name: 'Adicionar dia' }).click();
  await bruno.getByText('Dia 1 · Pernas').waitFor();
  await bruno.getByText('+ Adicionar exercício').click();
  await pick(bruno, 'Exercício', 'squat');
  await bruno.getByLabel('Carga (kg)').fill('60');
  await bruno.getByLabel('RPE').fill('8');
  await bruno.getByLabel('Cadência').fill('3-1-1-0');
  await bruno.getByRole('button', { name: 'Adicionar', exact: true }).click();
  await bruno.getByText(/3 × 10 · 60 kg/).waitFor();
  await shot(bruno, '04-construtor-treino');
  await bruno.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await bruno.getByRole('button', { name: 'Criar nova versão para editar' }).waitFor();
  log('Bruno montou e publicou o treino (dia, exercício com carga, RPE e cadência)');

  // Physio protocol
  await carla.goto(`${WEB}/pro`);
  await carla.getByRole('link', { name: /Ana Fisioterapia · desde/ }).first().click();
  await carla.getByPlaceholder('Ex.: Reabilitação de joelho').fill('Joelho direito');
  await carla.getByRole('button', { name: 'Criar rascunho' }).click();
  await carla.waitForURL(/\/protocolo\//);
  await carla.getByLabel('Ou nome livre').fill('Isometria de quadríceps');
  await carla.getByLabel('Séries').fill('3');
  await carla.getByLabel('Tempo (segundos)').fill('30');
  await carla.getByLabel('Link do vídeo').fill('https://videos.example.com/quadriceps.mp4');
  await carla.getByRole('button', { name: 'Adicionar exercício' }).click();
  await carla.getByText('Isometria de quadríceps').first().waitFor();
  await carla.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await carla.getByRole('button', { name: 'Criar nova versão para editar' }).waitFor();
  await shot(carla, '05-protocolo');
  log('Carla montou e publicou o protocolo com vídeo');

  // Patient day
  await ana.goto(`${WEB}/app`);
  assert(await ana.getByRole('tab', { name: 'Treino + alimentação' }).isVisible(), 'visão combinada');
  assert(await ana.getByText('Treino · Força').isVisible(), 'treino do dia');
  assert(await ana.getByText('Isometria de quadríceps').isVisible(), 'exercício de fisioterapia');
  await ana.getByRole('button', { name: 'Segui', exact: true }).click();
  await ana.getByText('Segui', { exact: true }).waitFor();
  await ana.getByRole('button', { name: '+ 300 ml' }).click();
  await ana.getByText('300 / 2500 ml').waitFor();
  await ana.getByRole('button', { name: 'Marcar como feito' }).click();
  await ana.getByText('Feito hoje').waitFor();
  await ana.locator('select[name=moment]').selectOption('before');
  await ana.locator('label', { hasText: /^2$/ }).click();
  await ana.getByRole('button', { name: 'Registrar' }).click();
  await ana.getByText('Dor registrada.').waitFor();
  await ana.locator('select[name=moment]').selectOption('after');
  await ana.locator('label', { hasText: /^6$/ }).click();
  await ana.getByRole('button', { name: 'Registrar' }).click();
  await ana.getByText('6/10').waitFor();
  await shot(ana, '06-meu-dia');
  log('Ana usou o Meu Dia: seguiu a refeição, bebeu água, fez o exercício e registrou dor');

  const phone = await browser.newContext({ ...playwright.devices['iPhone 13'], locale: 'pt-BR' });
  await phone.addCookies(await ana.context().cookies());
  const mobile = await phone.newPage();
  await mobile.goto(`${WEB}/app`);
  await mobile.screenshot({ path: path.join(shots, '07-meu-dia-celular.png'), fullPage: true, caret: 'initial' });
  await mobile.goto(`${WEB}/app?ver=alimentacao`);
  assert(!(await mobile.getByText('Treino · Força').isVisible()), 'somente alimentação esconde o treino');
  log('Meu Dia no celular e filtro "Só alimentação" conferidos');

  // Sharing
  await ana.goto(`${WEB}/app/compartilhamento`);
  const brunoTraining = ana.locator('section', { hasText: 'Profissional de Educação Física' });
  await brunoTraining.getByRole('button', { name: 'Compartilhar Registros de dor' }).click();
  await ana.getByRole('button', { name: 'Parar de compartilhar Registros de dor' }).waitFor();
  await shot(ana, '08-compartilhamento');
  log('Ana compartilhou os registros de dor com o personal');

  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Treino · desde/ }).first().click();
  await bruno.getByText(/registro\(s\) nos últimos 28 dias/).waitFor();
  log('O personal vê o resumo de dor compartilhado');

  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Nutrição · desde/ }).first().click();
  await bruno.getByText('Nada compartilhado').waitFor();
  assert(await bruno.getByText(/kcal/).first().isVisible(), 'diário com a refeição seguida');
  await shot(bruno, '09-ficha-nutricao');
  log('O nutricionista vê o diário, mas nada que não foi compartilhado com ele');

  // Pain alert
  await carla.goto(`${WEB}/pro/alertas`);
  await carla.getByText('Aumentou após os exercícios').first().waitFor();
  await shot(carla, '10-alertas');
  log('Carla recebeu o alerta de aumento de dor');

  // New version keeps the old one
  await bruno.goto(dietUrl);
  await bruno.getByRole('button', { name: 'Criar nova versão para editar' }).click();
  await bruno.getByText('versão 2').waitFor();
  await bruno.getByLabel('Calorias (kcal)').fill('2200');
  await bruno.getByRole('button', { name: 'Salvar metas' }).click();
  await bruno.waitForLoadState('networkidle');
  await bruno.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await bruno.getByRole('link', { name: 'v1 · Versão anterior' }).waitFor();
  log('Nova versão da dieta publicada; a versão 1 ficou no histórico');

  await ana.goto(`${WEB}/app`);
  await ana.getByText(/\/ 2200 kcal/).waitFor();
  log('Ana passou a ver a meta da nova versão');

  assert(errors.length === 0, `erros no navegador: ${errors.join(' | ')}`);
  console.log('\nTudo certo. Capturas em e2e/screenshots/');
} catch (error) {
  for (const [index, context] of browser.contexts().entries()) {
    for (const [i, page] of context.pages().entries()) {
      await page.screenshot({ path: path.join(shots, `falha-${index}-${i}.png`), fullPage: true, caret: 'initial' }).catch(() => {});
      console.error(`falha-${index}-${i}: ${page.url()}`);
    }
  }
  console.error(error);
  console.error('Erros no navegador:', errors);
  process.exitCode = 1;
} finally {
  await browser.close();
}

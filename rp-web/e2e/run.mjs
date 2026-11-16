// End-to-end walk through the web app with real Django and Next.js servers.
//
// Needs: Django on KINUTRI_API_URL (local_dev settings, sample fixtures loaded),
// the web app on KINUTRI_WEB_URL with KINUTRI_DEV_LOGIN=1, and Playwright.
// Users are created fresh for every run through manage.py.

import { execFileSync, execSync } from 'node:child_process';
import crypto from 'node:crypto';
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

// Django shell code, on the local dev server or, with KINUTRI_MANAGE (e.g.
// "docker compose exec -T web python3 manage.py"), on the staging stack
function manageShell(code) {
  if (process.env.KINUTRI_MANAGE) {
    execFileSync('sh', ['-c', `${process.env.KINUTRI_MANAGE} shell`], { input: code, stdio: ['pipe', 'ignore', 'inherit'] });
    return;
  }
  execFileSync('uv', ['run', './manage.py', 'shell', '-c', code], {
    cwd: repo,
    env: { ...process.env, DJANGO_SETTINGS_MODULE: 'settings.local_dev' },
    stdio: 'ignore',
  });
}

manageShell(
  `from django.contrib.auth.models import User\nfor u in ${JSON.stringify(Object.values(users))}:\n    User.objects.create_user(u, f'{u}@example.com', '${PASSWORD}', first_name=u.split('_')[0].title())`,
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

// Script errors and Content Security Policy violations fail the run
function watch(page, name) {
  page.on('pageerror', e => errors.push(`${name}: ${e.message}`));
  page.on('console', message => {
    if (message.type() === 'error' && /Content Security Policy|Refused to/.test(message.text())) {
      errors.push(`${name}: ${message.text()}`);
    }
  });
}

// Two-step verification (RFC 6238, as the authenticator apps): secret of each professional
const totpSecrets = {};

function totp(secret, at = Date.now()) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const char of secret.replace(/=+$/, '')) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, '0');
  }
  const key = Buffer.from(bits.match(/.{8}/g).map(byte => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(at / 30000)));
  const hmac = crypto.createHmac('sha1', key).update(counter).digest();
  const offset = hmac[hmac.length - 1] & 15;
  return String((hmac.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, '0');
}

// A code is accepted once: wait for the next one when the current was just used
const usedCodes = new Set();
async function freshCode(name) {
  for (;;) {
    const code = totp(totpSecrets[name]);
    if (!usedCodes.has(`${name}:${code}`)) {
      usedCodes.add(`${name}:${code}`);
      return code;
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

async function enableMfa(page, name) {
  await page.goto(`${WEB}/conta/seguranca`);
  totpSecrets[name] = (await page.getByLabel('Chave do autenticador').textContent()).trim();
  await page.getByLabel('Código do aplicativo').fill(await freshCode(name));
  await page.getByLabel(/Senha da conta/).fill(PASSWORD);
  await page.getByRole('button', { name: 'Ativar' }).click();
  await page.getByText('Pronto: a verificação em duas etapas está ativada.').waitFor();
}

async function session(name, viewport = { width: 1280, height: 900 }) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 2, locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
  const page = await context.newPage();
  watch(page, name);
  await page.goto(`${WEB}/entrar`);
  if (!(await page.locator('input[name=username]').isVisible())) {
    await page.getByText('Acesso de desenvolvimento').click();
  }
  await page.fill('input[name=username]', users[name]);
  await page.fill('input[name=password]', PASSWORD);
  await page.click('form[action="/api/auth/password"] button[type=submit]');
  await page.waitForURL(/\/(app|inicio|pro|entrar\/codigo)/);
  if (page.url().includes('/entrar/codigo')) {
    await page.getByLabel('Código').fill(await freshCode(name));
    await page.getByRole('button', { name: 'Confirmar' }).click();
    await page.waitForURL(/\/(app|inicio|pro)/);
  }
  // The app stores the browser's timezone in the profile on the first page
  if (!page.url().includes('/inicio')) {
    for (let i = 0; i < 50 && !(await context.cookies()).some(c => c.name === 'kn_tz'); i++) {
      await page.waitForTimeout(200);
    }
  }
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
  await page.evaluate(() => window.scrollTo(0, 0));
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

  // A professional account sees no patient data before two-step verification
  await bruno.goto(`${WEB}/pro`);
  await bruno.waitForURL(/\/conta\/seguranca/);
  await bruno.getByText('Contas de profissionais precisam da verificação em duas etapas').waitFor();
  await shot(bruno, '01b-seguranca');
  await enableMfa(bruno, 'bruno');
  const recovery = await bruno.getByRole('list', { name: 'Códigos de recuperação' }).locator('li').count();
  assert(recovery >= 10, `códigos de recuperação (${recovery})`);
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('heading', { name: 'Pacientes', exact: true }).waitFor();
  log('Bruno ativou a verificação em duas etapas (QR code e códigos de recuperação) e entrou na área profissional');

  const carla = await session('carla');
  await carla.goto(`${WEB}/pro/configurar`);
  await carla.getByLabel('Nome (seu nome profissional ou da clínica)').fill('Clínica Carla Fisio');
  await carla.getByRole('button', { name: 'Criar organização' }).click();
  await carla.getByText('Clínica Carla Fisio').waitFor();
  await carla.locator('select[name=discipline]').selectOption('physio');
  await carla.getByLabel('Número do registro').fill('55555-F');
  await carla.getByRole('button', { name: 'Adicionar' }).click();
  await carla.getByText('CREFITO 55555-F/SP').waitFor();
  await enableMfa(carla, 'carla');
  log('Carla criou a clínica registrou o CREFITO e ativou a verificação em duas etapas');

  // Foods added by the nutritionist, shared with everyone
  await bruno.goto(`${WEB}/pro/alimentos`);
  await bruno.getByLabel('Nome', { exact: true }).fill(`Pão de queijo da casa ${run}`);
  for (const [label, value] of [['Energia (kcal)', '363'], ['Proteínas (g)', '5,1'], ['Carboidratos (g)', '34,2'], ['Gorduras (g)', '24,6']]) {
    await bruno.getByLabel(label).first().fill(value);
  }
  await bruno.getByRole('button', { name: 'Cadastrar alimento' }).click();
  await bruno.getByText('Alimento salvo.').waitFor();
  await pick(bruno, 'Corrigir um alimento existente (opcional)', 'Arroz, tipo 1, cozido');
  await bruno.getByLabel('Nome', { exact: true }).first().fill(`Arroz tipo 1 cozido, corrigido ${run}`);
  await bruno.getByLabel('Energia (kcal)').first().fill('130');
  await bruno.getByRole('button', { name: 'Cadastrar alimento' }).click();
  await bruno.getByText(`Arroz tipo 1 cozido, corrigido ${run}`).waitFor();
  assert(await bruno.getByText('Correção').first().isVisible(), 'correção marcada');
  await shot(bruno, '02b-alimentos');
  log('Bruno cadastrou um alimento novo e corrigiu o arroz da TACO (o original continua igual)');

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
  const visitor = await (await browser.newContext({ locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' })).newPage();
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
  await pick(bruno, 'Adicionar alimento', 'Arroz, tipo 1, cozido', lunch);
  const measure = lunch.locator('select[name=weight_unit]');
  await measure.locator('option', { hasText: 'colher de arroz (de servir)' }).waitFor({ state: 'attached' });
  await measure.selectOption({ label: 'colher de arroz (de servir) (45 g)' });
  await lunch.getByLabel('Quantidade').fill('3');
  await lunch.getByRole('button', { name: 'Adicionar', exact: true }).click();
  await bruno.getByText('3 × colher de arroz (de servir)').waitFor();
  await bruno.getByText('135 g').first().waitFor();
  const lunch2 = bruno.locator('section', { has: bruno.getByRole('heading', { name: /Almoço/ }) });
  await lunch2.getByText('+ substituição').click();
  await pick(bruno, 'Alimento', 'batata', lunch2);
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
  log('Bruno montou e publicou a dieta (refeição, arroz em colheres de servir, substituição, metas)');

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
  await pick(bruno, 'Exercício', 'agachamento completo');
  await bruno.getByLabel('Carga (kg)').fill('60');
  await bruno.getByLabel('RPE').fill('8');
  await bruno.getByLabel('Cadência').fill('3-1-1-0');
  await bruno.getByRole('button', { name: 'Adicionar', exact: true }).click();
  await bruno.getByText(/3 × 10 · 60 kg/).waitFor();
  await shot(bruno, '04-construtor-treino');
  await bruno.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await bruno.getByRole('button', { name: 'Criar nova versão para editar' }).waitFor();
  log('Bruno montou e publicou o treino (dia, exercício com carga, RPE e cadência)');

  // Periodization: two phases, the first with the routine
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Treino · desde/ }).first().click();
  await bruno.getByPlaceholder('Ex.: Temporada 2027').fill('Temporada de verão');
  await bruno.getByRole('button', { name: 'Criar periodização' }).click();
  await bruno.waitForURL(/\/periodizacao\//);
  await bruno.locator('select[name=focus]').selectOption('hypertrophy');
  await bruno.getByLabel('Semanas').fill('4');
  await bruno.getByLabel('Nome (opcional)').fill('Base');
  await bruno.locator('select[name=routine]').selectOption({ label: 'Força · v1 (Publicado)' });
  await bruno.getByLabel('Intensidade (opcional)').fill('RIR 2-3');
  await bruno.getByText('Séries por semana por músculo (opcional)').click();
  await bruno.getByLabel('Quadríceps', { exact: true }).fill('12');
  await bruno.getByLabel('Peitoral', { exact: true }).fill('10');
  await bruno.getByRole('button', { name: 'Adicionar fase' }).click();
  await bruno.getByText('Treino: Força · Intensidade: RIR 2-3').waitFor();
  await bruno.getByText('Séries por semana: Peitoral 10 · Quadríceps 12').waitFor();
  await bruno.locator('select[name=focus]').selectOption('deload');
  await bruno.getByLabel('Semanas').fill('1');
  await bruno.getByRole('button', { name: 'Adicionar fase' }).click();
  await bruno.getByText('2. Deload (recuperação)').waitFor();
  await shot(bruno, '04b-periodizacao');
  await bruno.getByRole('button', { name: 'Publicar para o paciente' }).click();
  await bruno.getByRole('button', { name: 'Criar nova versão para editar' }).waitFor();
  const periodizationUrl = bruno.url();
  log('Bruno montou e publicou a periodização: 4 semanas de base com o treino Força e 1 de deload');

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
  await ana.getByText('3 × colher de arroz (de servir) (135 g) · Arroz, tipo 1, cozido').waitFor();
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

  const phone = await browser.newContext({ ...playwright.devices['iPhone 13'], locale: 'pt-BR', timezoneId: 'America/Sao_Paulo' });
  await phone.addCookies(await ana.context().cookies());
  const mobile = await phone.newPage();
  await mobile.goto(`${WEB}/app`);
  await mobile.screenshot({ path: path.join(shots, '07-meu-dia-celular.png'), fullPage: true, caret: 'initial' });
  await mobile.goto(`${WEB}/app?ver=alimentacao`);
  assert(!(await mobile.getByText('Treino · Força').isVisible()), 'somente alimentação esconde o treino');
  log('Meu Dia no celular e filtro "Só alimentação" conferidos');

  // Agenda: the physiotherapist schedules, the patient sees and cancels
  const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' });
  await carla.goto(`${WEB}/pro/agenda`);
  await carla.locator('select[name=kind]').selectOption('session');
  await carla.locator('input[name=date]').fill(tomorrow);
  await carla.locator('input[name=time]').fill('14:00');
  await carla.getByLabel('Duração (min)').fill('50');
  await carla.getByRole('button', { name: 'Marcar', exact: true }).click();
  await carla.getByText('Consulta marcada.').waitFor();
  await carla.goto(`${WEB}/pro/agenda?semana=${tomorrow}`);
  await carla.getByText(/14:00 · Sessão · Ana/).waitFor();
  await shot(carla, '10b-agenda-profissional');

  await ana.goto(`${WEB}/app/agenda?mes=${tomorrow.slice(0, 7)}`);
  await ana.getByText('14:00 Sessão').first().waitFor();
  assert(await ana.getByText('Treino: Pernas').first().isVisible(), 'treino no calendário');
  assert(await ana.getByText('Periodização: Temporada de verão · Hipertrofia').isVisible(), 'periodização na agenda');
  assert(await ana.getByText('Base · sem. 1/4').first().isVisible(), 'fase e semana no calendário');
  assert(await ana.getByText('Fisio: Joelho direito').first().isVisible(), 'fisioterapia no calendário');
  await shot(ana, '10c-agenda-paciente');
  await ana.getByRole('button', { name: 'Cancelar' }).first().click();
  await ana.getByText('Nenhuma consulta marcada').waitFor();
  await carla.goto(`${WEB}/pro/agenda?semana=${tomorrow}`);
  await carla.getByText('Cancelada').waitFor();
  log('Carla marcou uma sessão; Ana viu no calendário com treino e fisioterapia, cancelou, e Carla viu cancelada');

  // Chat with a video and a photo of the exercise
  const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAE0lEQVR4nGM8858BK2DCLjxYJQBq5QHbT0Y1YwAAAABJRU5ErkJggg==', 'base64');
  const MP4 = Buffer.concat([Buffer.from([0, 0, 0, 0x18]), Buffer.from('ftypmp42'), Buffer.alloc(2048, 7)]);
  await ana.goto(`${WEB}/app/mensagens`);
  await ana.getByRole('link', { name: /Fisioterapeuta/ }).click();
  await ana.getByText('Nenhuma mensagem ainda. Escreva a primeira.').waitFor();
  await ana.locator('input[type=file]').setInputFiles({ name: 'agachamento.mp4', mimeType: 'video/mp4', buffer: MP4 });
  await ana.getByLabel('Mensagem').fill('Fiz o agachamento, segue o vídeo. Doeu um pouco no fim.');
  await ana.getByRole('button', { name: 'Enviar' }).click();
  await ana.getByText('Fiz o agachamento, segue o vídeo.', { exact: false }).waitFor();
  await ana.getByRole('button', { name: 'Enviando…' }).waitFor({ state: 'detached' });
  await ana.locator('input[type=file]').setInputFiles({ name: 'joelho.png', mimeType: 'image/png', buffer: PNG });
  await ana.getByRole('button', { name: 'Enviar' }).click();
  await ana.locator('ol[aria-label=Mensagens] img').waitFor();
  assert(await ana.locator('ol[aria-label=Mensagens] img').evaluate(img => img.complete && img.naturalWidth === 8), 'a foto enviada carrega');
  assert(await ana.locator('ol[aria-label=Mensagens] video').count() === 1, 'o vídeo aparece na conversa');
  log('Ana mandou um vídeo do exercício com texto e uma foto para a fisioterapeuta');

  await carla.goto(`${WEB}/pro`);
  await carla.getByRole('link', { name: /Mensagens\s*2/ }).waitFor();
  await carla.getByText('Último registro de fisioterapia: hoje').waitFor();
  await carla.goto(`${WEB}/pro/mensagens`);
  await carla.getByText('2 novas').waitFor();
  await carla.getByRole('link', { name: /Ana/ }).click();
  await carla.getByText('Doeu um pouco no fim.', { exact: false }).waitFor();
  const videoSrc = await carla.locator('ol[aria-label=Mensagens] video').getAttribute('src');
  const partial = await carla.evaluate(async src => {
    const response = await fetch(src, { headers: { Range: 'bytes=0-11' } });
    return [response.status, response.headers.get('content-range'), (await response.arrayBuffer()).byteLength];
  }, videoSrc);
  assert(partial[0] === 206 && partial[1] === `bytes 0-11/${MP4.length}` && partial[2] === 12, `vídeo por partes: ${partial}`);
  await carla.getByLabel('Mensagem').fill('Ótimo! Na próxima, desça mais devagar e pare antes da dor.');
  await carla.getByLabel('Mensagem').press('Enter');
  await carla.locator('ol[aria-label=Mensagens]').getByText('Na próxima, desça mais devagar', { exact: false }).waitFor();
  // Opening the conversation marked Ana's messages as read: the menu badge goes away
  await carla.getByRole('link', { name: 'Mensagens', exact: true }).waitFor();
  await carla.getByText('Rendering').waitFor({ state: 'detached' }).catch(() => {});
  await shot(carla, '11b-conversa-profissional');
  const blocked = await bruno.evaluate(async src => (await fetch(src)).status, videoSrc);
  assert(blocked === 404, `outro profissional não abre o anexo (${blocked})`);
  log('Carla viu o aviso de 2 mensagens, assistiu ao vídeo (por partes) e respondeu; Bruno não abre o anexo');

  // The open conversation refreshes by itself
  await ana.locator('ol[aria-label=Mensagens]').getByText('Na próxima, desça mais devagar', { exact: false }).waitFor({ timeout: 25000 });
  await ana.getByRole('link', { name: 'Mensagens', exact: true }).waitFor();
  await ana.getByText('✓✓ lida').first().waitFor();
  await shot(ana, '11-conversa-paciente');
  log('A resposta apareceu sozinha na conversa da Ana, com as mensagens dela marcadas como lidas');

  // Execution video to the trainer, with the exercise of the routine; he reviews it from the queue
  await ana.goto(`${WEB}/app/mensagens`);
  await ana.getByRole('link', { name: /Educação Física/ }).click();
  await ana.locator('input[type=file]').setInputFiles({ name: 'serie.mp4', mimeType: 'video/mp4', buffer: MP4 });
  const exerciseSelect = ana.getByLabel('Exercício do vídeo (opcional)');
  const squatName = (await exerciseSelect.locator('option').nth(1).textContent()).trim();
  assert(squatName === 'Agachamento completo com barra', `nome do exercício em português: ${squatName}`);
  await exerciseSelect.selectOption({ index: 1 });
  await ana.getByRole('button', { name: 'Enviar' }).click();
  await ana.getByText(`Execução: ${squatName}`).waitFor();
  await ana.getByText('aguardando revisão').waitFor();
  await bruno.goto(`${WEB}/pro`);
  const anaTraining = bruno.locator('li', { hasText: 'Ana' }).filter({ hasText: 'Treino ·' });
  await anaTraining.getByText('Nenhum registro ainda').waitFor();
  await anaTraining.getByText('Sem registro recente').waitFor();
  await bruno.getByRole('link', { name: /Vídeos\s*1/ }).click();
  await bruno.getByRole('heading', { name: 'A revisar (1)' }).waitFor();
  await bruno.getByText(`${squatName} · enviado em`, { exact: false }).waitFor();
  await shot(bruno, '11c-videos-para-revisar');
  await bruno.getByLabel('Comentário para o paciente (opcional)').fill('Boa descida. Mantenha os joelhos alinhados com os pés.');
  await bruno.getByRole('button', { name: 'Marcar como revisado' }).click();
  await bruno.getByText('Nenhum vídeo para revisar').waitFor();
  await bruno.getByText('revisado em', { exact: false }).waitFor();
  await ana.reload();
  await ana.getByText('vídeo revisado').waitFor();
  await ana.getByText('Mantenha os joelhos alinhados com os pés.', { exact: false }).waitFor();
  log(`Ana mandou o vídeo do ${squatName} para o personal, que revisou na fila e comentou na conversa`);

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

  // Nutritional assessment: anamnesis, anthropometry and energy needs
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Nutrição · desde/ }).first().click();
  await bruno.getByRole('link', { name: 'Avaliar' }).click();
  await bruno.waitForURL(/\/avaliacao$/);
  await bruno.getByLabel('Queixa principal e objetivo').fill('Perder gordura mantendo a massa muscular');
  await bruno.getByLabel('Alergias e intolerâncias').fill('Intolerância à lactose');
  await bruno.getByRole('button', { name: 'Salvar anamnese' }).click();
  await bruno.getByRole('definition').filter({ hasText: 'Intolerância à lactose' }).waitFor();
  await bruno.getByLabel('Idade (anos)').fill('30');
  await bruno.getByLabel('Altura (cm)').fill('165');
  await bruno.getByLabel('Peso (kg)').fill('65');
  await bruno.getByLabel('Cintura (cm)').fill('70');
  await bruno.getByLabel('Quadril (cm)').fill('98');
  await bruno.getByLabel('Ajuste (kcal)').fill('-400');
  await bruno.getByText('Dobras cutâneas (mm)').click();
  await bruno.getByRole('combobox', { name: /^Protocolo/ }).selectOption('jp3');
  await bruno.getByLabel('Tríceps', { exact: true }).fill('18');
  await bruno.getByLabel('Suprailíaca', { exact: true }).fill('15');
  await bruno.getByLabel('Coxa', { exact: true }).fill('25');
  await bruno.getByLabel('Proteína (g/kg)').fill('1,6');
  await bruno.getByLabel('Gordura (% das kcal)').fill('30');
  await bruno.getByRole('button', { name: 'Calcular e registrar' }).click();
  await bruno.getByRole('button', { name: /Criar plano com 1\.484 kcal/ }).waitFor();
  assert(await bruno.getByText('1.370 kcal').isVisible(), 'taxa metabólica basal (Mifflin)');
  assert(await bruno.getByText('1.884 kcal').isVisible(), 'gasto energético total');
  assert(await bruno.getByText('Eutrofia').isVisible(), 'classificação do IMC');
  assert(await bruno.getByText('23,5%').isVisible(), '% de gordura pelas dobras (Jackson-Pollock 3)');
  assert(await bruno.getByText('104 g').isVisible(), 'proteínas: 1,6 g/kg');
  assert(await bruno.getByText('157 g').isVisible(), 'carboidratos: o restante');
  await shot(bruno, '12-avaliacao-nutricional');
  log('Bruno registrou a anamnese e a avaliação com dobras; meta de 1.484 kcal dividida em macros');

  await ana.goto(`${WEB}/app/evolucao`);
  await ana.getByText('1.484 kcal').waitFor();
  await shot(ana, '12b-evolucao-paciente');
  log('Ana vê a avaliação e a meta na Evolução');

  await ana.goto(`${WEB}/app/compartilhamento`);
  await ana
    .locator('section', { hasText: 'Profissional de Educação Física' })
    .getByRole('button', { name: 'Compartilhar Peso e medidas' })
    .click();
  await ana.getByRole('button', { name: 'Parar de compartilhar Peso e medidas' }).waitFor();
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Treino · desde/ }).first().click();
  await bruno.getByText(/Avaliação nutricional de .*: 65 kg · IMC 23,9 · cintura 70 cm · 23,5% de gordura/).waitFor();
  assert(!(await bruno.getByText('1.484 kcal').isVisible()), 'o personal não vê a meta de calorias');
  log('Ana compartilhou peso e medidas com o personal: ele vê a antropometria, não as metas');

  // Planned versus done: three sets logged today (as the mobile app does)
  manageShell(
    [
        'from django.contrib.auth.models import User',
        'from django.utils import timezone',
        'from wger.manager.models import Routine, SlotEntry, WorkoutLog',
        `user = User.objects.get(username='${users.ana}')`,
        "routine = Routine.objects.get(user=user, status='published')",
        'entry = SlotEntry.objects.filter(slot__day__routine=routine).first()',
        'for _ in range(3):',
        '    WorkoutLog.objects.create(user=user, routine=routine, exercise=entry.exercise, date=timezone.now(), repetitions=10, weight=60, rir=2)',
      ].join('\n'),
  );
  await bruno.goto(periodizationUrl);
  await bruno.getByText('Planejado x realizado').waitFor();
  // One training day repeated daily: 7 sessions of 3 sets a week, 4 weeks
  await bruno.getByText('3 de 84 séries (4%) · RIR médio 2').waitFor();
  await bruno.getByRole('radio', { name: 'Tonelagem' }).click();
  await bruno.getByText('1.800 de 50.400 kg (4%) · RIR médio 2').waitFor();
  await bruno.getByRole('radio', { name: 'Séries' }).click();
  await bruno.getByRole('img', { name: /Base · semana 1/ }).hover();
  await bruno.getByText('Realizado: 3 séries (14%)').waitFor();
  // The squat trains the quadriceps (21 sets a week in the routine); no exercise for the chest
  const quads = bruno.getByRole('row').filter({ hasText: 'Quadríceps' });
  assert((await quads.innerText()).replace(/\s+/g, ' ').startsWith('Quadríceps 12 21 3 –'), `séries de quadríceps: ${await quads.innerText()}`);
  const chest = bruno.getByRole('row').filter({ hasText: 'Peitoral' });
  assert((await chest.innerText()).includes('abaixo da meta'), 'peitoral abaixo da meta no treino');
  await shot(bruno, '13-planejado-realizado');
  log('O personal comparou o planejado com o realizado na fase (séries, tonelagem e séries por músculo)');

  await ana.goto(`${WEB}/app/evolucao`);
  await ana.getByText('Treino planejado x realizado · Temporada de verão').waitFor();
  await ana.getByText('3 de 84 séries (4%) · RIR médio 2').waitFor();
  log('Ana vê o próprio planejado x realizado na Evolução');

  // Consistency: today she trained, ate, drank water and did the physio exercise
  await ana.goto(`${WEB}/app/constancia`);
  const todayBr = new Date().toLocaleDateString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  await ana.getByText('1 dia', { exact: true }).waitFor();
  await ana.getByRole('img', { name: `Treino, ${todayBr}: treino feito` }).waitFor();
  await ana.getByRole('img', { name: `Refeições registradas, ${todayBr}: refeições registradas` }).waitFor();
  await ana.getByRole('img', { name: `Fisioterapia, ${todayBr}: exercícios feitos` }).waitFor();
  await ana.getByRole('heading', { name: 'Conquistas' }).waitFor();
  await ana.getByText('Conclua 10 treinos').waitFor();
  await shot(ana, '14-constancia');
  log('Ana vê a constância e as conquistas em português do Brasil');

  // The trainer turns achievements and the streak off for Ana, then on again
  await bruno.goto(`${WEB}/pro`);
  await bruno.getByRole('link', { name: /Ana Treino · desde/ }).first().click();
  await bruno.getByRole('button', { name: 'Desativar para este paciente' }).click();
  await bruno.getByText('Desativadas por você').waitFor();
  await ana.reload();
  await ana.getByText(/Conquistas e sequência desativadas por .*, que acompanha você/).waitFor();
  assert(!(await ana.getByText('Sequência', { exact: true }).isVisible()), 'sequência escondida');
  await bruno.getByRole('button', { name: 'Ativar de novo' }).click();
  await bruno.getByRole('button', { name: 'Desativar para este paciente' }).waitFor();
  await ana.reload();
  await ana.getByText('Sequência', { exact: true }).waitFor();
  log('O personal desativou as conquistas e a sequência da Ana e ativou de novo');

  // Email notices: on by default, each one can be turned off
  await ana.goto(`${WEB}/conta/avisos`);
  const messagesNotice = ana.getByLabel('Mensagens novas por e-mail');
  assert(await messagesNotice.isChecked(), 'aviso de mensagens ligado por padrão');
  await messagesNotice.uncheck();
  await ana.getByRole('button', { name: 'Salvar' }).click();
  await ana.getByText('Preferências salvas.').waitFor();
  await ana.reload();
  assert(!(await ana.getByLabel('Mensagens novas por e-mail').isChecked()), 'aviso de mensagens desligado');
  assert(await ana.getByLabel('Mensagens novas por celular').isChecked(), 'aviso no celular continua ligado');
  assert(await ana.getByLabel('Atendimentos por e-mail').isChecked(), 'aviso de atendimentos continua ligado');
  await ana.getByText('Nenhum celular recebe avisos ainda.', { exact: false }).waitFor();
  log('Ana desligou o e-mail de mensagens novas e manteve os outros avisos (e-mail e celular)');

  // LGPD: export and deletion request
  await ana.goto(`${WEB}/app/privacidade`);
  const [download] = await Promise.all([ana.waitForEvent('download'), ana.getByRole('link', { name: 'Baixar arquivo (JSON)' }).click()]);
  const exported = JSON.parse(await (await import('node:fs/promises')).readFile(await download.path(), 'utf8'));
  assert(download.suggestedFilename().startsWith(`dados-${users.ana}`), 'nome do arquivo exportado');
  assert(exported.nutrition.NutritionPlan.length === 2, 'as duas versões da dieta na exportação');
  assert(exported.physio.PainRecord.length === 2, 'registros de dor na exportação');
  assert(exported.care.reads_of_your_shared_data.length > 0, 'acessos aos dados compartilhados na exportação');
  assert(exported.care.messages.length === 5, 'as mensagens na exportação');
  assert(exported.care.messages.some(m => m.exercise && m.reviewed_at), 'o vídeo de execução revisado na exportação');
  assert(exported.nutrition.NutritionalAssessment.length === 1, 'a avaliação nutricional na exportação');
  log('Ana baixou os seus dados (dietas, dor, mensagens e quem acessou o que ela compartilhou)');

  await visitor.goto(`${WEB}/app/privacidade`);
  await visitor.getByLabel('Digite EXCLUIR para confirmar').fill('excluir');
  await visitor.getByRole('button', { name: 'Pedir a exclusão da conta' }).click();
  await visitor.getByText('Pedido de exclusão registrado.').waitFor();
  await visitor.getByRole('button', { name: 'Desistir da exclusão' }).waitFor();
  await bruno.goto(`${WEB}/pro`);
  assert(!(await bruno.getByRole('link', { name: /Dani Nutrição · desde/ }).isVisible()), 'Dani saiu da lista do nutricionista');
  log('Dani pediu a exclusão: o acompanhamento terminou na hora e o pedido ficou em análise');

  const anonymous = await (await browser.newContext()).newPage();
  watch(anonymous, 'visitante');
  const protectedPage = await anonymous.goto(`${WEB}/pro`);
  assert(protectedPage.ok(), `área protegida sem login: ${protectedPage.status()}`);
  await anonymous.waitForURL(/\/entrar$/);
  await anonymous.getByText('ALMOVA').first().waitFor();
  // A new login of a professional asks for the code; a wrong one is refused
  const login = await (await browser.newContext()).newPage();
  watch(login, 'bruno (novo login)');
  await login.goto(`${WEB}/entrar`);
  if (!(await login.locator('input[name=username]').isVisible())) {
    await login.getByText('Acesso de desenvolvimento').click();
  }
  await login.fill('input[name=username]', users.bruno);
  await login.fill('input[name=password]', PASSWORD);
  await login.click('form[action="/api/auth/password"] button[type=submit]');
  await login.waitForURL(/\/entrar\/codigo/);
  const wrong = totp(totpSecrets.bruno) === '000000' ? '111111' : '000000';
  await login.getByLabel('Código').fill(wrong);
  await login.getByRole('button', { name: 'Confirmar' }).click();
  await login.waitForURL(/\/entrar\/codigo\?.*erro=/);
  assert(!(await login.context().cookies()).some(c => c.name === 'kn_access'), 'sem sessão com código errado');
  await login.getByLabel('Código').fill(await freshCode('bruno'));
  await login.getByRole('button', { name: 'Confirmar' }).click();
  await login.waitForURL(/\/(inicio|pro|app)/);
  log('Novo login do Bruno pediu o código do autenticador e recusou um código errado');

  log('Sem login, a área profissional leva à tela de entrada do ALMOVA');

  const policy = protectedPage.headers()['content-security-policy'] ?? '';
  assert(/script-src 'self' 'nonce-[^']+' 'strict-dynamic'/.test(policy), `política de segurança (CSP): ${policy}`);
  assert(policy.includes("frame-ancestors 'none'") && policy.includes("object-src 'none'"), 'CSP sem frames nem plugins');
  const nonce = policy.match(/'nonce-([^']+)'/)[1];
  const again = (await anonymous.goto(`${WEB}/entrar`)).headers()['content-security-policy'];
  assert(!again.includes(nonce), 'nonce novo a cada página');
  if (process.env.KINUTRI_EXPECT_PRODUCTION === '1') {
    const hsts = protectedPage.headers()['strict-transport-security'] ?? '';
    assert(hsts.startsWith('max-age=63072000'), `HSTS: ${hsts}`);
    assert(!policy.includes('unsafe-eval'), 'sem unsafe-eval em produção');
    // In development, `next dev` inserts scripts at runtime, which 'strict-dynamic' allows without a nonce
    const scripts = await anonymous.evaluate(() => [...document.scripts].map(script => script.nonce));
    assert(scripts.length > 0 && scripts.every(Boolean), `todos os scripts com o nonce (${scripts.length})`);
  }
  log('Cada página tem a política de segurança (CSP) com nonce próprio, sem violações no navegador');

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

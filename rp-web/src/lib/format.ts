export const STATUS_LABELS: Record<string, string> = {
  invited: 'Convite enviado',
  active: 'Ativo',
  paused: 'Pausado',
  ended: 'Encerrado',
  draft: 'Rascunho',
  published: 'Publicado',
  superseded: 'Versão anterior',
  archived: 'Arquivado',
  pending: 'Em verificação',
  verified: 'Verificado',
  rejected: 'Recusado',
};

export const SCOPE_LABELS: Record<string, { title: string; text: string }> = {
  'training.schedule': { title: 'Rotina de treino', text: 'Dias, horários e frequência dos treinos.' },
  'training.adherence': { title: 'Treinos realizados', text: 'Quantos treinos você fez nas últimas semanas.' },
  'nutrition.goals': { title: 'Metas nutricionais', text: 'Calorias, macros e horários das refeições.' },
  'nutrition.adherence': { title: 'Resumo do diário alimentar', text: 'Dias com registro e refeições seguidas.' },
  'physio.pain': { title: 'Registros de dor', text: 'Média e últimos registros de dor.' },
  'body.measurements': { title: 'Peso e medidas', text: 'Seus últimos registros de peso.' },
  'notes.multidisciplinary': { title: 'Observações dos profissionais', text: 'O que os seus outros profissionais anotaram.' },
};

export const MOMENT_LABELS: Record<string, string> = {
  before: 'Antes dos exercícios',
  during: 'Durante os exercícios',
  after: 'Depois dos exercícios',
  next_day: 'No dia seguinte',
  other: 'Outro momento',
};

export const ADHERENCE_LABELS: Record<string, string> = {
  full: 'Segui',
  partial: 'Segui parcialmente',
  skipped: 'Não segui',
};

export const KIND_LABELS: Record<string, string> = {
  consultation: 'Consulta',
  session: 'Sessão',
  assessment: 'Avaliação',
  follow_up: 'Retorno',
};

export const LOCATION_LABELS: Record<string, string> = {
  home: 'Em casa',
  gym: 'Na academia',
  clinic: 'Na clínica',
};

export const CRITERION_LABELS: Record<string, string> = {
  energy: 'Mesma energia',
  macronutrient: 'Mesmo macronutriente',
  manual: 'Definida pelo nutricionista',
  preference: 'Preferência',
  availability: 'Disponibilidade',
};

export function number(value: number | string | null | undefined, digits = 0): string {
  if (value === null || value === undefined || value === '') {
    return '–';
  }
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: digits });
}

export function date(value: string | null | undefined): string {
  if (!value) {
    return '–';
  }
  const [y, m, d] = value.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

export function dateTime(value: string | null | undefined): string {
  if (!value) {
    return '–';
  }
  return new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short', timeZone: 'America/Sao_Paulo' });
}

export function weekday(isoDate: string): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString('pt-BR', { weekday: 'long', timeZone: 'UTC' });
}

export function shiftDate(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  const value = new Date(Date.UTC(y, m - 1, d + days));
  return value.toISOString().slice(0, 10);
}

export function time(value: string | null | undefined): string {
  return value ? value.slice(0, 5) : '';
}

export const GOAL_LABELS: Record<string, string> = {
  hypertrophy: 'Hipertrofia',
  strength: 'Força',
  fat_loss: 'Emagrecimento',
  endurance: 'Resistência',
  performance: 'Desempenho esportivo',
  health: 'Saúde e condicionamento',
};

export const FOCUS_LABELS: Record<string, string> = {
  adaptation: 'Adaptação',
  hypertrophy: 'Hipertrofia',
  strength: 'Força',
  power: 'Potência',
  endurance: 'Resistência',
  deload: 'Deload (recuperação)',
  peak: 'Pico',
  transition: 'Transição',
};

/** Background and text classes per block focus, for timelines and the calendar */
export const FOCUS_COLORS: Record<string, string> = {
  adaptation: 'bg-sky-100 text-sky-900',
  hypertrophy: 'bg-neon-100 text-navy-900',
  strength: 'bg-navy-800 text-white',
  power: 'bg-amber-200 text-amber-900',
  endurance: 'bg-teal-100 text-teal-900',
  deload: 'bg-gray-200 text-gray-700',
  peak: 'bg-red-100 text-red-800',
  transition: 'bg-violet-100 text-violet-900',
};

export const ACTIVITY_LABELS: Record<string, string> = {
  sedentary: 'Sedentário (1,2)',
  light: 'Levemente ativo (1,375)',
  moderate: 'Moderadamente ativo (1,55)',
  very: 'Muito ativo (1,725)',
  extreme: 'Extremamente ativo (1,9)',
};

export const EQUATION_LABELS: Record<string, string> = {
  mifflin: 'Mifflin-St Jeor',
  harris_benedict: 'Harris-Benedict (revisada)',
  katch_mcardle: 'Katch-McArdle (massa magra)',
};

// WHO adult BMI classes
export function bmiClass(bmi: number): string {
  if (bmi < 18.5) return 'Baixo peso';
  if (bmi < 25) return 'Eutrofia';
  if (bmi < 30) return 'Sobrepeso';
  if (bmi < 35) return 'Obesidade grau I';
  if (bmi < 40) return 'Obesidade grau II';
  return 'Obesidade grau III';
}

export const SKINFOLD_PROTOCOLS: Record<string, { label: string; sites: string }> = {
  jp3: { label: 'Jackson-Pollock 3 dobras', sites: 'Homens: peitoral, abdominal, coxa. Mulheres: tríceps, suprailíaca, coxa.' },
  jp7: { label: 'Jackson-Pollock 7 dobras', sites: 'Peitoral, axilar média, tríceps, subescapular, abdominal, suprailíaca, coxa.' },
  durnin: { label: 'Durnin-Womersley 4 dobras', sites: 'Bíceps, tríceps, subescapular, suprailíaca.' },
};

export const SKINFOLD_SITES: [string, string][] = [
  ['chest', 'Peitoral'],
  ['midaxillary', 'Axilar média'],
  ['triceps', 'Tríceps'],
  ['subscapular', 'Subescapular'],
  ['abdomen', 'Abdominal'],
  ['suprailiac', 'Suprailíaca'],
  ['thigh', 'Coxa'],
  ['biceps', 'Bíceps'],
];

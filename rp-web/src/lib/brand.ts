// The app name lives here only, so a rename is a one-line change (or NEXT_PUBLIC_APP_NAME).
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Kinutri';

export const APP_TAGLINE = 'Treino, reabilitação e nutrição';

export const DISCIPLINE_LABELS: Record<string, string> = {
  training: 'Treino',
  physio: 'Fisioterapia',
  nutrition: 'Nutrição',
};

export const PROFESSION_LABELS: Record<string, string> = {
  training: 'Profissional de Educação Física',
  physio: 'Fisioterapeuta',
  nutrition: 'Nutricionista',
};

export const COUNCIL_LABELS: Record<string, string> = {
  training: 'CREF',
  physio: 'CREFITO',
  nutrition: 'CRN',
};

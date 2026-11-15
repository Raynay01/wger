export type Discipline = 'training' | 'physio' | 'nutrition';

export type Paginated<T> = { count: number; next: string | null; results: T[] };

export type Organization = {
  id: string;
  name: string;
  kind: 'solo' | 'clinic' | 'team';
  document: string;
  is_active: boolean;
  my_role: string | null;
};

export type Registration = {
  id: string;
  discipline: Discipline;
  council: string;
  number: string;
  region: string;
  status: 'pending' | 'verified' | 'rejected';
};

export type Relationship = {
  id: string;
  organization: string;
  organization_name: string;
  professional: number;
  professional_name: string;
  patient: number | null;
  patient_name: string | null;
  discipline: Discipline;
  status: 'invited' | 'active' | 'paused' | 'ended';
  invited_email: string;
  invitation_token: string | null;
  invitation_sent_at: string | null;
  created: string;
  started: string | null;
  gamification_enabled: boolean;
  my_role: 'professional' | 'patient';
};

export type Grant = {
  id: string;
  relationship: string;
  scope: string;
  granted_at: string;
  revoked_at: string | null;
};

export type Note = {
  id: string;
  relationship: string;
  patient: number;
  author: string;
  discipline: Discipline;
  category: string;
  text: string;
  visible_to_patient: boolean;
  created: string;
};

export type Prescription = {
  id: string | number;
  status: 'draft' | 'published' | 'superseded' | 'archived';
  version: number;
  lineage_id: string | null;
  author: number | null;
  care_relationship: string | null;
  published_at: string | null;
  previous_version: string | number | null;
};

export type NutritionPlan = Prescription & {
  id: string;
  description: string;
  start: string;
  end: string | null;
  goal_energy: number | null;
  goal_protein: number | null;
  goal_carbohydrates: number | null;
  goal_fat: number | null;
  goal_fiber: number | null;
  goal_water_ml: number | null;
};

export type Values = {
  energy: number;
  protein: number;
  carbohydrates: number;
  fat: number;
  fiber: number | null;
};

export type MealItemInfo = {
  id: string;
  ingredient: number;
  ingredient_obj: { name: string; energy: number };
  amount: string;
  weight_unit: number | null;
  instructions: string;
  substitutions: { id: string; ingredient: number; ingredient_name: string; amount: string; criterion: string; note: string }[];
};

export type MealInfo = {
  id: string;
  name: string;
  time: string | null;
  order: number;
  instructions: string;
  meal_items: MealItemInfo[];
  nutritional_values: Values;
};

export type PlanInfo = NutritionPlan & { meals: MealInfo[] };

export type Routine = Prescription & {
  id: number;
  name: string;
  description: string;
  start: string;
  end: string;
};

export type Protocol = Prescription & {
  id: string;
  name: string;
  description: string;
  start: string;
  end: string | null;
  pain_moments: string[];
  pain_alert_threshold: number;
  pain_alert_increase: number;
};

export type ProtocolExercise = {
  id: string;
  protocol: string;
  exercise: number | null;
  name: string;
  sets: number | null;
  repetitions: number | null;
  duration_seconds: number | null;
  load: string;
  frequency_per_week: number | null;
  location: 'home' | 'gym' | 'clinic';
  instructions: string;
  video_url: string;
  order: number;
};

export type MyDay = {
  date: string;
  mode: 'guided' | 'self';
  modules: Discipline[];
  combined_view: boolean;
  training: null | {
    routine: null | { id: number; name: string; author: number | null };
    day: null | {
      date: string;
      label: string | null;
      day: null | { id: number; name: string; is_rest: boolean; description: string };
      slots: { comment: string; sets: { exercise: number; text_repr: string; sets: number }[]; exercises: number[] }[];
    };
    session_done: boolean;
  };
  nutrition: null | {
    plan: null | { id: string; description: string; author: number | null };
    goals: null | Record<'energy' | 'protein' | 'carbohydrates' | 'fat' | 'fiber', number | null>;
    meals: {
      id: string;
      name: string;
      time: string | null;
      instructions: string;
      planned: Values;
      items: { ingredient: number; name: string; amount: string; weight_unit: number | null; unit_name: string | null; grams: string; instructions: string; substitutions: number }[];
      adherence: 'full' | 'partial' | 'skipped' | null;
    }[];
    logged: Values | null;
    remaining: Record<string, number> | null;
    water: { total_ml: number; goal_ml: number | null };
  };
  physio: null | {
    protocols: {
      id: string;
      name: string;
      pain_moments: string[];
      exercises: {
        id: string;
        name: string;
        sets: number | null;
        repetitions: number | null;
        duration_seconds: number | null;
        load: string;
        location: string;
        video_url: string;
        instructions: string;
        done: boolean;
      }[];
    }[];
    pain: { moment: string; value: number; datetime: string; protocol: string | null }[];
  };
};

export type Message = {
  id: string;
  relationship: string;
  sender: number | null;
  sender_name: string | null;
  mine: boolean;
  text: string;
  attachment_kind: '' | 'image' | 'video';
  attachment_name: string;
  exercise: number | null;
  exercise_name: string | null;
  created: string;
  read_at: string | null;
  reviewed_at: string | null;
};

export type Video = Message & { patient_name: string };

export type TrainingBlock = {
  id: string;
  order: number;
  name: string;
  focus: string;
  weeks: number;
  routine: number | null;
  current_routine: number | null;
  current_routine_name: string | null;
  intensity: string;
  volume: string;
  weekly_sets: WeeklySets[];
  notes: string;
  start: string;
  end: string;
};

/** Target sets per week of a muscle */
export type WeeklySets = { muscle: number; sets: number };

export type Muscle = { id: number; name: string; name_en: string };

export type TrainingPlan = Prescription & {
  id: string;
  name: string;
  goal: string;
  start: string;
  end: string | null;
  description: string;
  blocks: TrainingBlock[];
};

export type NutritionalAssessment = {
  id: string;
  relationship: string;
  patient: number;
  date: string;
  sex: 'female' | 'male';
  age: number;
  weight: string;
  height: string;
  waist: string | null;
  hip: string | null;
  body_fat: string | null;
  skinfold_protocol: '' | 'jp3' | 'jp7' | 'durnin';
  skinfolds: Record<string, number>;
  skinfold_sum: string | null;
  activity_level: string;
  equation: string;
  energy_adjustment: number;
  protein_per_kg: string | null;
  fat_percent: number | null;
  macros: { protein: number; carbohydrates: number; fat: number } | null;
  notes: string;
  bmi: string;
  waist_hip_ratio: string | null;
  lean_mass: string | null;
  basal_energy: number;
  total_energy: number;
  target_energy: number;
  created: string;
};

export const ANAMNESIS_FIELDS = [
  ['goal', 'Queixa principal e objetivo'],
  ['medical_history', 'Histórico clínico (doenças, cirurgias, exames)'],
  ['medications', 'Medicamentos e suplementos'],
  ['allergies', 'Alergias e intolerâncias'],
  ['preferences', 'Preferências e aversões alimentares'],
  ['eating_habits', 'Hábitos alimentares (horários, onde, com quem)'],
  ['bowel_habits', 'Hábito intestinal'],
  ['sleep', 'Sono'],
  ['water', 'Ingestão de água'],
  ['alcohol_smoking', 'Álcool e tabagismo'],
  ['physical_activity', 'Atividade física'],
  ['notes', 'Observações'],
] as const;

export type AnamnesisField = (typeof ANAMNESIS_FIELDS)[number][0];

export type NutritionalAnamnesis = { id: string; relationship: string; date: string; created: string } & Record<AnamnesisField, string>;

export type ProgressSummary = {
  start: string;
  end: string;
  planned_sessions: number;
  done_sessions: number;
  planned_sets: number;
  done_sets: number;
  planned_load: number;
  done_load: number;
  average_rir: string | null;
  average_rpe: string | null;
};

export type ProgressMuscle = { muscle: number; planned_sets: number; done_sets: number };

export type ProgressBlock = ProgressSummary & {
  id: string;
  name: string;
  focus: string;
  intensity: string;
  volume: string;
  /** Totals over the block of the muscles with a weekly target */
  muscles: (ProgressMuscle & { name: string; weekly_sets: number })[];
  weeks: (ProgressSummary & { week: number; muscles: ProgressMuscle[] })[];
};

export type PlanProgress = {
  start: string;
  end: string | null;
  blocks: ProgressBlock[];
};

export type ConsistencyDay = {
  date: string;
  training: 'done' | 'missed' | 'planned' | 'rest' | null;
  meals: boolean | null;
  water_ml: number | null;
  water_goal: boolean | null;
  physio: boolean | null;
  recorded: boolean;
};

export type ConsistencyWeek = {
  start: string;
  end: string;
  training_done: number;
  training_planned: number;
  meals_days: number;
  water_goal_days: number;
  physio_days: number;
  recorded_days: number;
};

export type Consistency = { modules: string[]; today: string; streak: number; weeks: ConsistencyWeek[]; days: ConsistencyDay[] };

export type Gamification = {
  enabled: boolean;
  reason: 'patient' | 'professional' | 'pain' | null;
  disabled_by: string[];
  pain_until: string | null;
};

export type TrophyProgress = {
  trophy: { id: number; name: string; description: string; image: string | null; is_progressive: boolean };
  is_earned: boolean;
  earned_at: string | null;
  progress: number;
};

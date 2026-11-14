import { ACTIVITY_LABELS, EQUATION_LABELS, bmiClass, date, number } from '@/lib/format';
import type { NutritionalAssessment } from '@/lib/types';

function Tile({ label, value, hint, strong = false }: { label: string; value: string; hint?: string; strong?: boolean }) {
  return (
    <div className={`rounded-xl p-3 ${strong ? 'bg-navy-900 text-white' : 'bg-navy-100/50'}`}>
      <p className={`text-xs ${strong ? 'text-navy-100' : 'text-gray-600'}`}>{label}</p>
      <p className={`mt-0.5 text-xl font-bold tabular-nums ${strong ? 'text-neon-500' : 'text-navy-900'}`}>{value}</p>
      {hint && <p className={`text-xs ${strong ? 'text-navy-100' : 'text-gray-500'}`}>{hint}</p>}
    </div>
  );
}

/** The latest assessment: anthropometry and the energy needs */
export function NutritionalAssessmentSummary({ assessment }: { assessment: NutritionalAssessment }) {
  const adjustment = assessment.energy_adjustment;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-600">
        Avaliação de {date(assessment.date)} · {assessment.sex === 'female' ? 'Feminino' : 'Masculino'}, {assessment.age} anos
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Tile label="Peso" value={`${number(assessment.weight, 1)} kg`} hint={`Altura ${number(assessment.height)} cm`} />
        <Tile label="IMC" value={number(assessment.bmi, 1)} hint={bmiClass(Number(assessment.bmi))} />
        <Tile
          label="Relação cintura-quadril"
          value={assessment.waist_hip_ratio ? number(assessment.waist_hip_ratio, 2) : '–'}
          hint={assessment.waist ? `Cintura ${number(assessment.waist, 1)} cm` : undefined}
        />
        <Tile
          label="Gordura corporal"
          value={assessment.body_fat ? `${number(assessment.body_fat, 1)}%` : '–'}
          hint={assessment.lean_mass ? `Massa magra ${number(assessment.lean_mass, 1)} kg` : undefined}
        />
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Tile label="Taxa metabólica basal" value={`${number(assessment.basal_energy)} kcal`} hint={EQUATION_LABELS[assessment.equation]} />
        <Tile label="Gasto energético total" value={`${number(assessment.total_energy)} kcal`} hint={ACTIVITY_LABELS[assessment.activity_level]} />
        <Tile
          label="Meta diária"
          value={`${number(assessment.target_energy)} kcal`}
          hint={adjustment === 0 ? 'Manutenção' : `${adjustment > 0 ? '+' : '−'}${number(Math.abs(adjustment))} kcal para o objetivo`}
          strong
        />
      </div>
      {assessment.notes && <p className="text-sm text-gray-700">{assessment.notes}</p>}
    </div>
  );
}

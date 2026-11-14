'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { userZone } from '@/lib/userZone';
import { zonedToUtcIso } from '@/lib/zone';

// Every form posts a hidden "back" path; errors are shown there as ?erro=

function back(formData: FormData): string {
  const path = String(formData.get('back') || '/pro');
  return path.startsWith('/pro') ? path : '/pro';
}

function withParam(path: string, key: string, value: string): string {
  const [base, query = ''] = path.split('?');
  const params = new URLSearchParams(query);
  params.delete('erro');
  params.set(key, value);
  return `${base}?${params}`;
}

async function attempt(formData: FormData, call: () => Promise<unknown>): Promise<void> {
  try {
    await call();
  } catch (error) {
    if (error instanceof ApiError) {
      redirect(withParam(back(formData), 'erro', error.message));
    }
    throw error;
  }
  revalidatePath('/pro', 'layout');
}

function text(formData: FormData, key: string): string {
  return String(formData.get(key) ?? '').trim();
}

function optionalNumber(formData: FormData, key: string): number | null {
  const value = text(formData, key).replace(',', '.');
  return value === '' ? null : Number(value);
}

// Organization and registration

export async function createOrganization(formData: FormData) {
  await attempt(formData, () =>
    api('organization/', {
      method: 'POST',
      body: { name: text(formData, 'name'), kind: text(formData, 'kind') || 'solo', document: text(formData, 'document') },
    }),
  );
  redirect(back(formData));
}

export async function addRegistration(formData: FormData) {
  await attempt(formData, () =>
    api('professional-registration/', {
      method: 'POST',
      body: { discipline: text(formData, 'discipline'), number: text(formData, 'number'), region: text(formData, 'region') },
    }),
  );
  redirect(back(formData));
}

// Patients

export async function invitePatient(formData: FormData) {
  let id = '';
  await attempt(formData, async () => {
    const created = await api<{ id: string }>('care-relationship/', {
      method: 'POST',
      body: {
        organization: text(formData, 'organization'),
        discipline: text(formData, 'discipline'),
        invited_email: text(formData, 'invited_email'),
      },
    });
    id = created.id;
  });
  redirect(`/pro/pacientes/novo?convite=${id}`);
}

/** Emails the invitation, only when the professional asks for it */
export async function sendInvitationEmail(formData: FormData) {
  await attempt(formData, () => api(`care-relationship/${text(formData, 'id')}/send-email/`, { method: 'POST' }));
  redirect(withParam(back(formData), 'enviado', '1'));
}

export async function relationshipAction(formData: FormData) {
  const action = text(formData, 'action');
  if (!['pause', 'resume', 'end'].includes(action)) {
    return;
  }
  await attempt(formData, () => api(`care-relationship/${text(formData, 'id')}/${action}/`, { method: 'POST' }));
  redirect(back(formData));
}

export async function addNote(formData: FormData) {
  await attempt(formData, () =>
    api('multidisciplinary-note/', {
      method: 'POST',
      body: {
        relationship: text(formData, 'relationship'),
        text: text(formData, 'text'),
        category: text(formData, 'category') || 'general',
        visible_to_patient: formData.get('visible_to_patient') === 'on',
      },
    }),
  );
  redirect(back(formData));
}

export async function addAssessment(formData: FormData) {
  await attempt(formData, () =>
    api('functional-assessment/', {
      method: 'POST',
      body: {
        relationship: text(formData, 'relationship'),
        kind: text(formData, 'kind'),
        name: text(formData, 'name'),
        side: text(formData, 'side'),
        value: optionalNumber(formData, 'value'),
        unit: text(formData, 'unit'),
        date: text(formData, 'date') || undefined,
        notes: text(formData, 'notes'),
      },
    }),
  );
  redirect(back(formData));
}

export async function addAnamnesis(formData: FormData) {
  const fields = ['goal', 'medical_history', 'medications', 'allergies', 'preferences', 'eating_habits', 'bowel_habits', 'sleep', 'water', 'alcohol_smoking', 'physical_activity', 'notes'];
  await attempt(formData, () =>
    api('nutritional-anamnesis/', {
      method: 'POST',
      body: {
        relationship: text(formData, 'relationship'),
        date: text(formData, 'date') || undefined,
        ...Object.fromEntries(fields.map(key => [key, text(formData, key)])),
      },
    }),
  );
  redirect(back(formData));
}

export async function addNutritionalAssessment(formData: FormData) {
  await attempt(formData, () =>
    api('nutritional-assessment/', {
      method: 'POST',
      body: {
        relationship: text(formData, 'relationship'),
        date: text(formData, 'date') || undefined,
        sex: text(formData, 'sex'),
        age: optionalNumber(formData, 'age'),
        weight: optionalNumber(formData, 'weight'),
        height: optionalNumber(formData, 'height'),
        waist: optionalNumber(formData, 'waist'),
        hip: optionalNumber(formData, 'hip'),
        body_fat: optionalNumber(formData, 'body_fat'),
        skinfold_protocol: text(formData, 'skinfold_protocol'),
        skinfolds: Object.fromEntries(
          ['chest', 'midaxillary', 'triceps', 'subscapular', 'abdomen', 'suprailiac', 'thigh', 'biceps']
            .map(site => [site, optionalNumber(formData, `skinfold_${site}`)])
            .filter(([, mm]) => mm !== null),
        ),
        activity_level: text(formData, 'activity_level'),
        equation: text(formData, 'equation'),
        energy_adjustment: optionalNumber(formData, 'energy_adjustment') ?? 0,
        protein_per_kg: optionalNumber(formData, 'protein_per_kg'),
        fat_percent: optionalNumber(formData, 'fat_percent'),
        notes: text(formData, 'notes'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteNutritionalAssessment(formData: FormData) {
  await attempt(formData, () => api(`nutritional-assessment/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

// Prescriptions in general

const KINDS: Record<string, { endpoint: string; path: string }> = {
  nutrition: { endpoint: 'nutritionplan', path: 'dieta' },
  training: { endpoint: 'routine', path: 'treino' },
  physio: { endpoint: 'physio-protocol', path: 'protocolo' },
  periodization: { endpoint: 'training-plan', path: 'periodizacao' },
};

export async function prescriptionAction(formData: FormData) {
  const kind = KINDS[text(formData, 'kind')];
  const action = text(formData, 'action');
  if (!kind || !['publish', 'new-version', 'archive'].includes(action)) {
    return;
  }
  let target = text(formData, 'id');
  await attempt(formData, async () => {
    const result = await api<{ id: string | number }>(`${kind.endpoint}/${target}/${action}/`, { method: 'POST' });
    target = String(result.id);
  });
  redirect(`/pro/pacientes/${text(formData, 'relationship')}/${kind.path}/${target}`);
}

export async function deletePrescription(formData: FormData) {
  const kind = KINDS[text(formData, 'kind')];
  if (!kind) {
    return;
  }
  await attempt(formData, () => api(`${kind.endpoint}/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(`/pro/pacientes/${text(formData, 'relationship')}`);
}

// Nutrition

export async function createPlan(formData: FormData) {
  const relationship = text(formData, 'relationship');
  let id = '';
  await attempt(formData, async () => {
    const plan = await api<{ id: string }>('nutritionplan/', {
      method: 'POST',
      body: {
        description: text(formData, 'description') || 'Plano alimentar',
        care_relationship: relationship,
        ...(optionalNumber(formData, 'goal_energy') !== null && { goal_energy: optionalNumber(formData, 'goal_energy'), has_goal_calories: true }),
        ...Object.fromEntries(
          ['goal_protein', 'goal_carbohydrates', 'goal_fat']
            .map(key => [key, optionalNumber(formData, key)])
            .filter(([, value]) => value !== null),
        ),
      },
    });
    id = plan.id;
  });
  redirect(`/pro/pacientes/${relationship}/dieta/${id}`);
}

export async function updatePlan(formData: FormData) {
  await attempt(formData, () =>
    api(`nutritionplan/${text(formData, 'id')}/`, {
      method: 'PATCH',
      body: {
        description: text(formData, 'description'),
        goal_energy: optionalNumber(formData, 'goal_energy'),
        goal_protein: optionalNumber(formData, 'goal_protein'),
        goal_carbohydrates: optionalNumber(formData, 'goal_carbohydrates'),
        goal_fat: optionalNumber(formData, 'goal_fat'),
        goal_fiber: optionalNumber(formData, 'goal_fiber'),
        goal_water_ml: optionalNumber(formData, 'goal_water_ml'),
        has_goal_calories: optionalNumber(formData, 'goal_energy') !== null,
      },
    }),
  );
  redirect(back(formData));
}

export async function addMeal(formData: FormData) {
  await attempt(formData, () =>
    api('meal/', {
      method: 'POST',
      body: {
        plan: text(formData, 'plan'),
        name: text(formData, 'name'),
        time: text(formData, 'time') || null,
        instructions: text(formData, 'instructions'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteMeal(formData: FormData) {
  await attempt(formData, () => api(`meal/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

export async function addMealItem(formData: FormData) {
  await attempt(formData, () =>
    api('mealitem/', {
      method: 'POST',
      body: {
        meal: text(formData, 'meal'),
        ingredient: Number(text(formData, 'ingredient')),
        weight_unit: text(formData, 'weight_unit') ? Number(text(formData, 'weight_unit')) : null,
        amount: optionalNumber(formData, 'amount'),
        instructions: text(formData, 'instructions'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteMealItem(formData: FormData) {
  await attempt(formData, () => api(`mealitem/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

export async function addSubstitution(formData: FormData) {
  await attempt(formData, () =>
    api('substitution-option/', {
      method: 'POST',
      body: {
        meal_item: text(formData, 'meal_item'),
        ingredient: Number(text(formData, 'ingredient')),
        amount: optionalNumber(formData, 'amount'),
        criterion: text(formData, 'criterion') || 'manual',
        note: text(formData, 'note'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteSubstitution(formData: FormData) {
  await attempt(formData, () => api(`substitution-option/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

// Physiotherapy

export async function createProtocol(formData: FormData) {
  const relationship = text(formData, 'relationship');
  let id = '';
  await attempt(formData, async () => {
    const protocol = await api<{ id: string }>('physio-protocol/', {
      method: 'POST',
      body: { name: text(formData, 'name') || 'Protocolo', care_relationship: relationship },
    });
    id = protocol.id;
  });
  redirect(`/pro/pacientes/${relationship}/protocolo/${id}`);
}

export async function updateProtocol(formData: FormData) {
  await attempt(formData, () =>
    api(`physio-protocol/${text(formData, 'id')}/`, {
      method: 'PATCH',
      body: {
        name: text(formData, 'name'),
        description: text(formData, 'description'),
        end: text(formData, 'end') || null,
        pain_before: formData.get('pain_before') === 'on',
        pain_during: formData.get('pain_during') === 'on',
        pain_after: formData.get('pain_after') === 'on',
        pain_next_day: formData.get('pain_next_day') === 'on',
        pain_alert_threshold: optionalNumber(formData, 'pain_alert_threshold') ?? 7,
        pain_alert_increase: optionalNumber(formData, 'pain_alert_increase') ?? 3,
      },
    }),
  );
  redirect(back(formData));
}

export async function addProtocolExercise(formData: FormData) {
  const exercise = text(formData, 'exercise');
  await attempt(formData, () =>
    api('protocol-exercise/', {
      method: 'POST',
      body: {
        protocol: text(formData, 'protocol'),
        exercise: exercise ? Number(exercise) : null,
        name: text(formData, 'name') || text(formData, 'exercise_name'),
        sets: optionalNumber(formData, 'sets'),
        repetitions: optionalNumber(formData, 'repetitions'),
        duration_seconds: optionalNumber(formData, 'duration_seconds'),
        load: text(formData, 'load'),
        frequency_per_week: optionalNumber(formData, 'frequency_per_week'),
        location: text(formData, 'location') || 'home',
        instructions: text(formData, 'instructions'),
        video_url: text(formData, 'video_url'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteProtocolExercise(formData: FormData) {
  await attempt(formData, () => api(`protocol-exercise/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

// Training

export async function createRoutine(formData: FormData) {
  const relationship = text(formData, 'relationship');
  let id = '';
  await attempt(formData, async () => {
    const routine = await api<{ id: number }>('routine/', {
      method: 'POST',
      body: {
        name: text(formData, 'name') || 'Treino',
        start: text(formData, 'start'),
        end: text(formData, 'end'),
        care_relationship: relationship,
      },
    });
    id = String(routine.id);
  });
  redirect(`/pro/pacientes/${relationship}/treino/${id}`);
}

export async function addDay(formData: FormData) {
  const isRest = formData.get('is_rest') === 'on';
  await attempt(formData, () =>
    api('day/', {
      method: 'POST',
      body: {
        routine: Number(text(formData, 'routine')),
        name: isRest ? '' : text(formData, 'name'),
        order: Number(text(formData, 'order') || 1),
        is_rest: isRest,
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteDay(formData: FormData) {
  await attempt(formData, () => api(`day/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

export async function addExerciseToDay(formData: FormData) {
  await attempt(formData, async () => {
    const slot = await api<{ id: number }>('slot/', {
      method: 'POST',
      body: { day: Number(text(formData, 'day')), order: Number(text(formData, 'order') || 1) },
    });
    const entry = await api<{ id: number }>('slot-entry/', {
      method: 'POST',
      body: {
        slot: slot.id,
        exercise: Number(text(formData, 'exercise')),
        order: 1,
        comment: text(formData, 'comment'),
        tempo: text(formData, 'tempo'),
        rpe: optionalNumber(formData, 'rpe'),
        range_of_motion: text(formData, 'range_of_motion'),
      },
    });
    const configs: [string, number | null][] = [
      ['sets-config', optionalNumber(formData, 'sets')],
      ['repetitions-config', optionalNumber(formData, 'repetitions')],
      ['weight-config', optionalNumber(formData, 'weight')],
      ['rir-config', optionalNumber(formData, 'rir')],
      ['rest-config', optionalNumber(formData, 'rest')],
    ];
    for (const [endpoint, value] of configs) {
      if (value !== null) {
        await api(`${endpoint}/`, { method: 'POST', body: { slot_entry: entry.id, iteration: 1, value } });
      }
    }
  });
  redirect(back(formData));
}

export async function deleteSlot(formData: FormData) {
  await attempt(formData, () => api(`slot/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

// Foods added by the nutritionists of the organization (shared with everyone)

function foodValues(formData: FormData) {
  const sodiumMg = optionalNumber(formData, 'sodium_mg');
  const values: Record<string, unknown> = {
    energy: optionalNumber(formData, 'energy'),
    protein: optionalNumber(formData, 'protein'),
    carbohydrates: optionalNumber(formData, 'carbohydrates'),
    fat: optionalNumber(formData, 'fat'),
    fiber: optionalNumber(formData, 'fiber'),
    sodium: sodiumMg === null ? null : sodiumMg / 1000,
  };
  // Empty fields of a correction take the values of the base food
  return Object.fromEntries(Object.entries(values).filter(([, v]) => v !== null));
}

export async function createFood(formData: FormData) {
  const basedOn = text(formData, 'based_on');
  await attempt(formData, () =>
    api('professional-food/', {
      method: 'POST',
      body: {
        organization: text(formData, 'organization'),
        name: text(formData, 'name'),
        brand: text(formData, 'brand'),
        based_on: basedOn ? Number(basedOn) : null,
        ...foodValues(formData),
      },
    }),
  );
  redirect(withParam(back(formData), 'salvo', '1'));
}

export async function updateFood(formData: FormData) {
  await attempt(formData, () =>
    api(`professional-food/${text(formData, 'id')}/`, {
      method: 'PATCH',
      body: { name: text(formData, 'name'), brand: text(formData, 'brand'), ...foodValues(formData) },
    }),
  );
  redirect(withParam(back(formData), 'salvo', '1'));
}

export async function deleteFood(formData: FormData) {
  await attempt(formData, () => api(`professional-food/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

// Agenda

export async function scheduleAppointment(formData: FormData) {
  const zone = await userZone();
  const local = `${text(formData, 'date')}T${text(formData, 'time')}`;
  await attempt(formData, () =>
    api('appointment/', {
      method: 'POST',
      body: {
        relationship: text(formData, 'relationship'),
        kind: text(formData, 'kind') || 'consultation',
        start: zonedToUtcIso(local, zone),
        duration_minutes: optionalNumber(formData, 'duration_minutes') ?? 60,
        location: text(formData, 'location'),
        notes: text(formData, 'notes'),
      },
    }),
  );
  redirect(withParam(back(formData), 'salvo', '1'));
}

export async function appointmentAction(formData: FormData) {
  const action = text(formData, 'action');
  if (!['cancel', 'done'].includes(action)) {
    return;
  }
  await attempt(formData, () => api(`appointment/${text(formData, 'id')}/${action}/`, { method: 'POST' }));
  redirect(back(formData));
}

// Periodization

export async function createTrainingPlan(formData: FormData) {
  const relationship = text(formData, 'relationship');
  let id = '';
  await attempt(formData, async () => {
    const plan = await api<{ id: string }>('training-plan/', {
      method: 'POST',
      body: {
        name: text(formData, 'name') || 'Periodização',
        goal: text(formData, 'goal') || 'hypertrophy',
        start: text(formData, 'start') || undefined,
        care_relationship: relationship,
      },
    });
    id = plan.id;
  });
  redirect(`/pro/pacientes/${relationship}/periodizacao/${id}`);
}

export async function updateTrainingPlan(formData: FormData) {
  await attempt(formData, () =>
    api(`training-plan/${text(formData, 'id')}/`, {
      method: 'PATCH',
      body: {
        name: text(formData, 'name'),
        goal: text(formData, 'goal'),
        start: text(formData, 'start'),
        description: text(formData, 'description'),
      },
    }),
  );
  redirect(back(formData));
}

export async function addTrainingBlock(formData: FormData) {
  const routine = text(formData, 'routine');
  await attempt(formData, () =>
    api('training-block/', {
      method: 'POST',
      body: {
        plan: text(formData, 'plan'),
        order: optionalNumber(formData, 'order') ?? 1,
        name: text(formData, 'name'),
        focus: text(formData, 'focus'),
        weeks: optionalNumber(formData, 'weeks'),
        routine: routine ? Number(routine) : null,
        intensity: text(formData, 'intensity'),
        volume: text(formData, 'volume'),
        weekly_sets: [...formData.entries()]
          .filter(([key, value]) => key.startsWith('sets_') && String(value).trim() !== '')
          .map(([key, value]) => ({ muscle: Number(key.slice('sets_'.length)), sets: Number(value) })),
        notes: text(formData, 'notes'),
      },
    }),
  );
  redirect(back(formData));
}

export async function deleteTrainingBlock(formData: FormData) {
  await attempt(formData, () => api(`training-block/${text(formData, 'id')}/`, { method: 'DELETE' }));
  redirect(back(formData));
}

'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { api, ApiError } from '@/lib/api';

export type FormState = { error?: string; ok?: string } | undefined;

function fail(error: unknown): FormState {
  if (error instanceof ApiError) {
    return { error: error.message };
  }
  throw error;
}

export async function addWater(formData: FormData) {
  const amount = Number(formData.get('amount_ml'));
  if (amount > 0) {
    await api('water-log/', { method: 'POST', body: { amount_ml: amount } });
  }
  revalidatePath('/app');
}

export async function setAdherence(formData: FormData) {
  await api('meal-adherence/', {
    method: 'POST',
    body: {
      meal: formData.get('meal'),
      date: formData.get('date'),
      status: formData.get('status'),
    },
  });
  revalidatePath('/app');
}

export async function logPrescribedMeal(formData: FormData) {
  // "Segui" also records the prescribed items in the food diary
  const plan = String(formData.get('plan'));
  const meal = String(formData.get('meal'));
  const date = String(formData.get('date'));
  const items = JSON.parse(String(formData.get('items') || '[]')) as { ingredient: number; amount: string; weight_unit: number | null }[];
  for (const item of items) {
    await api('nutritiondiary/', {
      method: 'POST',
      body: { plan, meal, ingredient: item.ingredient, amount: item.amount, weight_unit: item.weight_unit },
    });
  }
  await api('meal-adherence/', { method: 'POST', body: { meal, date, status: 'full' } });
  revalidatePath('/app');
}

export async function recordExercise(formData: FormData) {
  await api('exercise-record/', { method: 'POST', body: { protocol_exercise: formData.get('protocol_exercise') } });
  revalidatePath('/app');
}

export async function recordPain(_: FormState, formData: FormData): Promise<FormState> {
  try {
    await api('pain-record/', {
      method: 'POST',
      body: {
        protocol: formData.get('protocol') || null,
        moment: formData.get('moment'),
        value: Number(formData.get('value')),
        body_region: formData.get('body_region') || '',
        notes: formData.get('notes') || '',
      },
    });
  } catch (error) {
    return fail(error);
  }
  revalidatePath('/app');
  return { ok: 'Dor registrada.' };
}

export async function acceptInvitation(formData: FormData) {
  await api(`care-relationship/${formData.get('id')}/accept/`, { method: 'POST', body: { accept_terms: true } });
  revalidatePath('/app', 'layout');
  redirect('/app/compartilhamento');
}

export async function declineInvitation(formData: FormData) {
  await api(`care-relationship/${formData.get('id')}/decline/`, { method: 'POST' });
  revalidatePath('/app/convites');
}

export async function endRelationship(formData: FormData) {
  await api(`care-relationship/${formData.get('id')}/end/`, { method: 'POST' });
  revalidatePath('/app', 'layout');
}

export async function grantScope(formData: FormData) {
  await api('access-grant/', {
    method: 'POST',
    body: { relationship: formData.get('relationship'), scope: formData.get('scope') },
  });
  revalidatePath('/app/compartilhamento');
}

export async function revokeGrant(formData: FormData) {
  await api(`access-grant/${formData.get('id')}/`, { method: 'DELETE' });
  revalidatePath('/app/compartilhamento');
}

'use server';

import { revalidatePath } from 'next/cache';
import { api } from './api';

export async function deleteMessage(formData: FormData) {
  const id = String(formData.get('id') ?? '');
  if (/^[0-9a-f-]{36}$/.test(id)) {
    await api(`care-message/${id}/`, { method: 'DELETE' });
  }
  revalidatePath(String(formData.get('back') ?? '/app/mensagens'));
}

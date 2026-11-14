import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Chat } from '@/components/Chat';
import { api, ApiError } from '@/lib/api';
import { DISCIPLINE_LABELS } from '@/lib/brand';
import type { Relationship } from '@/lib/types';
import { userZone } from '@/lib/userZone';

export const metadata: Metadata = { title: 'Conversa' };

export default async function ProfessionalConversationPage({ params }: { params: Promise<{ rel: string }> }) {
  const { rel } = await params;
  const relationship = await api<Relationship>(`care-relationship/${rel}/`).catch(error => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) {
      notFound();
    }
    throw error;
  });
  if (relationship.my_role !== 'professional' || relationship.status === 'invited') {
    notFound();
  }
  const name = relationship.patient_name ?? relationship.invited_email;
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div>
        <Link href={`/pro/pacientes/${rel}`} className="text-sm text-navy-700 underline">
          ← Ficha do paciente
        </Link>
        <h1 className="mt-1 text-2xl font-bold">{name}</h1>
        <p className="text-sm text-gray-600">{DISCIPLINE_LABELS[relationship.discipline]}</p>
      </div>
      <Chat relationship={relationship} otherSide={name} zone={await userZone()} back={`/pro/mensagens/${rel}`} />
    </div>
  );
}

import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Chat } from '@/components/Chat';
import { api, ApiError } from '@/lib/api';
import { PROFESSION_LABELS } from '@/lib/brand';
import type { Relationship } from '@/lib/types';
import { userZone } from '@/lib/userZone';

export const metadata: Metadata = { title: 'Conversa' };

export default async function PatientConversationPage({ params }: { params: Promise<{ rel: string }> }) {
  const { rel } = await params;
  const relationship = await api<Relationship>(`care-relationship/${rel}/`).catch(error => {
    if (error instanceof ApiError && (error.status === 404 || error.status === 400)) {
      notFound();
    }
    throw error;
  });
  if (relationship.my_role !== 'patient') {
    notFound();
  }
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div>
        <Link href="/app/mensagens" className="text-sm text-navy-700 underline">
          ← Mensagens
        </Link>
        <h1 className="mt-1 text-2xl font-bold">{relationship.professional_name}</h1>
        <p className="text-sm text-gray-600">
          {PROFESSION_LABELS[relationship.discipline]} · {relationship.organization_name}
        </p>
      </div>
      <Chat relationship={relationship} otherSide={relationship.professional_name} zone={await userZone()} back={`/app/mensagens/${rel}`} />
    </div>
  );
}

import type { Metadata } from 'next';
import { AutoRefresh } from '@/components/AutoRefresh';
import { ConversationList } from '@/components/ConversationList';
import { api } from '@/lib/api';
import type { Paginated, Relationship } from '@/lib/types';

export const metadata: Metadata = { title: 'Mensagens' };

export default async function PatientMessagesPage() {
  const [relationships, unread] = await Promise.all([
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'patient', limit: 100 } }),
    api<Record<string, number>>('care-message/unread/', { query: { role: 'patient' } }),
  ]);
  return (
    <div className="flex flex-col gap-4">
      <AutoRefresh seconds={20} />
      <div>
        <h1 className="text-2xl font-bold">Mensagens</h1>
        <p className="text-sm text-gray-600">Converse com os seus profissionais e mande fotos ou vídeos dos exercícios.</p>
      </div>
      <ConversationList relationships={relationships.results} unread={unread} basePath="/app/mensagens" side="patient" />
    </div>
  );
}

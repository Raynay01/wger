import type { Metadata } from 'next';
import { AutoRefresh } from '@/components/AutoRefresh';
import { ConversationList } from '@/components/ConversationList';
import { api } from '@/lib/api';
import type { Paginated, Relationship } from '@/lib/types';

export const metadata: Metadata = { title: 'Mensagens' };

export default async function ProfessionalMessagesPage() {
  const [relationships, unread] = await Promise.all([
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'professional', limit: 200 } }),
    api<Record<string, number>>('care-message/unread/', { query: { role: 'professional' } }),
  ]);
  return (
    <div className="flex flex-col gap-4">
      <AutoRefresh seconds={20} />
      <h1 className="text-2xl font-bold">Mensagens</h1>
      <ConversationList relationships={relationships.results} unread={unread} basePath="/pro/mensagens" side="professional" />
    </div>
  );
}

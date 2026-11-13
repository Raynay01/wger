import type { Metadata } from 'next';
import { Button, Card, Empty } from '@/components/ui';
import { api } from '@/lib/api';
import { PROFESSION_LABELS } from '@/lib/brand';
import { SCOPE_LABELS } from '@/lib/format';
import type { Grant, Paginated, Relationship } from '@/lib/types';
import { grantScope, revokeGrant } from '../actions';

export const metadata: Metadata = { title: 'Compartilhamento' };

// A professional already sees their own module, so offering it again would be noise
const OWN_SCOPES: Record<string, string[]> = {
  training: ['training.schedule', 'training.adherence'],
  nutrition: ['nutrition.goals', 'nutrition.adherence'],
  physio: ['physio.pain'],
};

export default async function SharingPage() {
  const [relationships, grants] = await Promise.all([
    api<Paginated<Relationship>>('care-relationship/', { query: { role: 'patient', status: 'active', limit: 100 } }),
    api<Paginated<Grant>>('access-grant/', { query: { limit: 200 } }),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Compartilhamento</h1>
        <p className="mt-1 max-w-2xl text-sm text-gray-600">
          Cada profissional vê a própria área. Aqui você escolhe o que mais cada um pode ver para acompanhar você melhor.
          Você pode desligar a qualquer momento, e cada acesso fica registrado.
        </p>
      </div>

      {relationships.results.length === 0 && <Empty title="Nenhum profissional acompanha você ainda" />}

      {relationships.results.map(relationship => {
        const active = grants.results.filter(g => g.relationship === relationship.id && !g.revoked_at);
        const scopes = Object.keys(SCOPE_LABELS).filter(s => !OWN_SCOPES[relationship.discipline]?.includes(s));
        return (
          <Card key={relationship.id} title={relationship.professional_name} action={<span className="text-sm text-gray-500">{PROFESSION_LABELS[relationship.discipline]}</span>}>
            <ul className="flex flex-col divide-y divide-navy-100">
              {scopes.map(scope => {
                const grant = active.find(g => g.scope === scope);
                return (
                  <li key={scope} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div>
                      <p className="font-medium">{SCOPE_LABELS[scope].title}</p>
                      <p className="text-sm text-gray-600">{SCOPE_LABELS[scope].text}</p>
                    </div>
                    {grant ? (
                      <form action={revokeGrant}>
                        <input type="hidden" name="id" value={grant.id} />
                        <Button variant="ghost" className="border border-neon-500 text-neon-700" aria-label={`Parar de compartilhar ${SCOPE_LABELS[scope].title}`}>
                          Compartilhando · parar
                        </Button>
                      </form>
                    ) : (
                      <form action={grantScope}>
                        <input type="hidden" name="relationship" value={relationship.id} />
                        <input type="hidden" name="scope" value={scope} />
                        <Button variant="ghost" className="border border-navy-100" aria-label={`Compartilhar ${SCOPE_LABELS[scope].title}`}>
                          Compartilhar
                        </Button>
                      </form>
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>
        );
      })}
    </div>
  );
}

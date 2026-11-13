import type { Metadata } from 'next';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { Badge, Button, Card, Field, inputClass } from '@/components/ui';
import { COUNCIL_LABELS, PROFESSION_LABELS } from '@/lib/brand';
import { STATUS_LABELS } from '@/lib/format';
import { professionalContext } from '@/lib/roles';
import { addRegistration, createOrganization } from '../actions';

export const metadata: Metadata = { title: 'Configurações' };

const KIND_LABELS: Record<string, string> = {
  solo: 'Profissional independente',
  clinic: 'Clínica',
  team: 'Equipe multidisciplinar',
};

const STATES = 'AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split(' ');

export default async function SettingsPage({ searchParams }: { searchParams: Promise<{ erro?: string }> }) {
  const { erro } = await searchParams;
  const { organizations, registrations } = await professionalContext();
  const missing = Object.keys(PROFESSION_LABELS).filter(d => !registrations.some(r => r.discipline === d));

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <h1 className="text-2xl font-bold">Configurações profissionais</h1>
      <ErrorFromQuery erro={erro} />

      <Card title="Organização">
        {organizations.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {organizations.map(o => (
              <li key={o.id} className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold">{o.name}</span>
                <span className="text-sm text-gray-600">
                  {KIND_LABELS[o.kind]} · você é {o.my_role === 'owner' ? 'proprietário(a)' : o.my_role}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <form action={createOrganization} className="grid gap-3 sm:grid-cols-2">
            <input type="hidden" name="back" value="/pro/configurar" />
            <Field label="Nome (seu nome profissional ou da clínica)">
              <input name="name" required maxLength={120} className={inputClass} />
            </Field>
            <Field label="Tipo">
              <select name="kind" className={inputClass}>
                {Object.entries(KIND_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="CPF ou CNPJ (opcional)">
              <input name="document" maxLength={20} className={inputClass} />
            </Field>
            <div className="flex items-end">
              <Button type="submit">Criar organização</Button>
            </div>
          </form>
        )}
      </Card>

      <Card title="Registro no conselho">
        {registrations.length > 0 && (
          <ul className="mb-4 flex flex-col gap-2">
            {registrations.map(r => (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  <strong>{PROFESSION_LABELS[r.discipline]}</strong> · {r.council} {r.number}/{r.region}
                </span>
                <Badge tone={r.status === 'verified' ? 'neon' : r.status === 'rejected' ? 'red' : 'amber'}>{STATUS_LABELS[r.status]}</Badge>
              </li>
            ))}
          </ul>
        )}
        {missing.length > 0 && (
          <form action={addRegistration} className="grid gap-3 sm:grid-cols-4">
            <input type="hidden" name="back" value="/pro/configurar" />
            <Field label="Profissão">
              <select name="discipline" className={inputClass}>
                {missing.map(d => (
                  <option key={d} value={d}>
                    {PROFESSION_LABELS[d]} ({COUNCIL_LABELS[d]})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Número do registro">
              <input name="number" required maxLength={30} className={inputClass} />
            </Field>
            <Field label="Estado">
              <select name="region" className={inputClass} defaultValue="SP">
                {STATES.map(s => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <div className="flex items-end">
              <Button type="submit">Adicionar</Button>
            </div>
          </form>
        )}
        <p className="mt-3 text-xs text-gray-500">
          O registro é conferido pela equipe da plataforma. Só é possível prescrever na profissão registrada (por exemplo, dietas
          apenas com CRN).
        </p>
      </Card>
    </div>
  );
}

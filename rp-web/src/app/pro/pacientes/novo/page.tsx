import type { Metadata } from 'next';
import { headers } from 'next/headers';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { SendInvitation } from '@/components/SendInvitation';
import { Button, Card, Field, inputClass, Notice } from '@/components/ui';
import { api } from '@/lib/api';
import { PROFESSION_LABELS } from '@/lib/brand';
import { professionalContext } from '@/lib/roles';
import type { Relationship } from '@/lib/types';
import { invitePatient } from '../../actions';

export const metadata: Metadata = { title: 'Convidar paciente' };

export default async function InvitePage({ searchParams }: { searchParams: Promise<{ erro?: string; convite?: string; enviado?: string }> }) {
  const { erro, convite, enviado } = await searchParams;
  const { organizations, registrations } = await professionalContext();
  const disciplines = registrations.filter(r => r.status !== 'rejected').map(r => r.discipline);

  let link = '';
  let invited: Relationship | null = null;
  if (convite) {
    invited = await api<Relationship>(`care-relationship/${convite}/`);
    const h = await headers();
    const origin = `${h.get('x-forwarded-proto') ?? 'http'}://${h.get('host')}`;
    link = `${origin}/convite/${invited.id}?token=${invited.invitation_token}`;
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <h1 className="text-2xl font-bold">Convidar paciente</h1>
      <ErrorFromQuery erro={erro} />

      {invited && (
        <Card title="Convite criado">
          {enviado && <Notice tone="success">Convite enviado por e-mail para {invited.invited_email}.</Notice>}
          <p className="mt-2 text-sm text-gray-700">
            O paciente vê o convite ao entrar com o e-mail <strong>{invited.invited_email}</strong>. Nada é enviado
            automaticamente: envie por e-mail quando quiser, ou mande o link abaixo (por WhatsApp, por exemplo).
          </p>
          <div className="mt-3">
            <SendInvitation relationship={invited} back={`/pro/pacientes/novo?convite=${invited.id}`} />
          </div>
          <input readOnly value={link} className={`${inputClass} mt-3 font-mono text-xs`} aria-label="Link do convite" />
        </Card>
      )}

      {organizations.length === 0 || disciplines.length === 0 ? (
        <Notice>Antes de convidar, crie a sua organização e informe o seu registro em Configurações.</Notice>
      ) : (
        <Card>
          <form action={invitePatient} className="flex flex-col gap-4">
            <input type="hidden" name="back" value="/pro/pacientes/novo" />
            <Field label="E-mail do paciente (de preferência o Gmail que ele usa para entrar)">
              <input name="invited_email" type="email" required className={inputClass} />
            </Field>
            <Field label="Acompanhamento">
              <select name="discipline" className={inputClass}>
                {disciplines.map(d => (
                  <option key={d} value={d}>
                    {PROFESSION_LABELS[d]}
                  </option>
                ))}
              </select>
            </Field>
            {organizations.length > 1 ? (
              <Field label="Organização">
                <select name="organization" className={inputClass}>
                  {organizations.map(o => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : (
              <input type="hidden" name="organization" value={organizations[0].id} />
            )}
            <Button type="submit" variant="secondary">
              Enviar convite
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}

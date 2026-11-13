import { sendInvitationEmail } from '@/app/pro/actions';
import { dateTime } from '@/lib/format';
import type { Relationship } from '@/lib/types';
import { Button } from './ui';

/** Sends the invitation email on demand; creating an invitation sends nothing */
export function SendInvitation({ relationship, back }: { relationship: Relationship; back: string }) {
  return (
    <form action={sendInvitationEmail} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="back" value={back} />
      <input type="hidden" name="id" value={relationship.id} />
      <Button variant={relationship.invitation_sent_at ? 'ghost' : 'secondary'} className={relationship.invitation_sent_at ? 'border border-navy-100' : ''}>
        {relationship.invitation_sent_at ? 'Reenviar por e-mail' : 'Enviar convite por e-mail'}
      </Button>
      <span className="text-xs text-gray-500">
        {relationship.invitation_sent_at ? `Último envio: ${dateTime(relationship.invitation_sent_at)}` : 'Ainda não enviado'}
      </span>
    </form>
  );
}

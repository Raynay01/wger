import { api } from '@/lib/api';
import { deleteMessage } from '@/lib/chatActions';
import type { Message, Paginated, Relationship } from '@/lib/types';
import { formatTime, todayIn } from '@/lib/zone';
import { AutoRefresh, RefreshOnce } from './AutoRefresh';
import { ChatComposer } from './ChatComposer';
import { Notice } from './ui';

const SHOWN = 100;

function dayOf(iso: string, zone: string): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: zone }).format(new Date(iso));
}

function dayLabel(day: string, today: string): string {
  const yesterday = new Date(`${today}T12:00:00Z`);
  yesterday.setUTCDate(yesterday.getUTCDate() - 1);
  if (day === today) {
    return 'Hoje';
  }
  if (day === yesterday.toISOString().slice(0, 10)) {
    return 'Ontem';
  }
  return new Date(`${day}T12:00:00Z`).toLocaleDateString('pt-BR', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'UTC' });
}

function Attachment({ message }: { message: Message }) {
  const src = `/api/anexos/${message.id}`;
  if (message.attachment_kind === 'image') {
    return (
      <a href={src} target="_blank" rel="noreferrer" className="block">
        <img src={src} alt={message.attachment_name || 'Foto'} loading="lazy" className="max-h-72 rounded-xl object-contain" />
      </a>
    );
  }
  if (message.attachment_kind === 'video') {
    return (
      <video src={src} controls preload="metadata" playsInline className="max-h-80 w-full max-w-sm rounded-xl bg-black">
        <a href={src}>{message.attachment_name || 'Vídeo'}</a>
      </video>
    );
  }
  return null;
}

/** The conversation of a follow-up; marks what the other side sent as read */
export async function Chat({
  relationship,
  otherSide,
  zone,
  back,
  exercises,
}: {
  relationship: Relationship;
  otherSide: string;
  zone: string;
  back: string;
  exercises?: { id: number; name: string }[];
}) {
  const page = await api<Paginated<Message>>('care-message/', {
    query: { relationship: relationship.id, ordering: '-created', limit: SHOWN },
  });
  const unread = page.results.some(m => !m.mine && !m.read_at);
  if (unread) {
    await api('care-message/read/', { method: 'POST', body: { relationship: relationship.id } });
  }
  const today = todayIn(zone);
  const open = relationship.status === 'active' || relationship.status === 'paused';

  // Newest first, shown bottom-up by flex-col-reverse, so the view starts at the latest message
  const rows: React.ReactNode[] = [];
  page.results.forEach((message, index) => {
    const day = dayOf(message.created, zone);
    const fromPatient = relationship.my_role === 'patient' ? message.mine : !message.mine;
    const patientVideo = message.attachment_kind === 'video' && fromPatient;
    rows.push(
      <li key={message.id} className={`flex ${message.mine ? 'justify-end' : 'justify-start'}`}>
        <div className={`flex max-w-[85%] flex-col gap-1 rounded-2xl px-3 py-2 text-sm shadow-sm ${message.mine ? 'bg-navy-900 text-white' : 'border border-navy-100 bg-white text-navy-900'}`}>
          {message.exercise_name && <p className="text-xs font-semibold">Execução: {message.exercise_name}</p>}
          <Attachment message={message} />
          {message.text && <p className="whitespace-pre-wrap break-words">{message.text}</p>}
          <div className={`flex items-center justify-end gap-2 text-[11px] ${message.mine ? 'text-navy-100' : 'text-gray-500'}`}>
            {message.mine && (
              <form action={deleteMessage}>
                <input type="hidden" name="id" value={message.id} />
                <input type="hidden" name="back" value={back} />
                <button type="submit" className="underline opacity-70 hover:opacity-100">
                  apagar
                </button>
              </form>
            )}
            {patientVideo && <span>{message.reviewed_at ? 'vídeo revisado' : 'aguardando revisão'}</span>}
            <span>{formatTime(message.created, zone)}</span>
            {message.mine && <span>{message.read_at ? '✓✓ lida' : '✓ enviada'}</span>}
          </div>
        </div>
      </li>,
    );
    const next = page.results[index + 1];
    if (!next || dayOf(next.created, zone) !== day) {
      rows.push(
        <li key={`day-${day}`} className="my-2 text-center text-xs font-semibold capitalize text-gray-500">
          {dayLabel(day, today)}
        </li>,
      );
    }
  });

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-navy-100 bg-navy-100/30 p-3">
      <AutoRefresh seconds={10} />
      {unread && <RefreshOnce />}
      {page.count > SHOWN && <p className="text-center text-xs text-gray-500">Mostrando as últimas {SHOWN} mensagens.</p>}
      {page.results.length === 0 ? (
        <p className="py-10 text-center text-sm text-gray-500">Nenhuma mensagem ainda. Escreva a primeira.</p>
      ) : (
        <ol aria-label="Mensagens" className="flex max-h-[60dvh] flex-col-reverse gap-2 overflow-y-auto p-1">
          {rows}
        </ol>
      )}
      {open ? (
        <ChatComposer relationship={relationship.id} otherSide={otherSide} exercises={exercises} />
      ) : (
        <Notice>Este acompanhamento foi encerrado. O histórico continua disponível, mas não é possível enviar mensagens.</Notice>
      )}
    </div>
  );
}

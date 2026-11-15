import type { Metadata } from 'next';
import Link from 'next/link';
import { ErrorFromQuery } from '@/components/ErrorFromQuery';
import { Button, Card, Empty, inputClass } from '@/components/ui';
import { reviewVideo } from '@/app/pro/actions';
import { api } from '@/lib/api';
import type { Paginated, Video } from '@/lib/types';
import { userZone } from '@/lib/userZone';
import { formatDateTime } from '@/lib/zone';

export const metadata: Metadata = { title: 'Vídeos para revisar' };

function Player({ video }: { video: Video }) {
  const src = `/api/anexos/${video.id}`;
  return (
    <video src={src} controls preload="metadata" playsInline className="max-h-80 w-full max-w-sm rounded-xl bg-black">
      <a href={src}>{video.attachment_name || 'Vídeo'}</a>
    </video>
  );
}

function Heading({ video, zone }: { video: Video; zone: string }) {
  return (
    <div>
      <Link href={`/pro/mensagens/${video.relationship}`} className="font-semibold underline">
        {video.patient_name}
      </Link>
      <p className="text-sm text-gray-600">
        {video.exercise_name ? `${video.exercise_name} · ` : ''}enviado em {formatDateTime(video.created, zone)}
      </p>
      {video.text && <p className="mt-1 whitespace-pre-wrap text-sm">“{video.text}”</p>}
    </div>
  );
}

export default async function VideosPage({ searchParams }: { searchParams: Promise<{ erro?: string }> }) {
  const { erro } = await searchParams;
  const [pending, reviewed, zone] = await Promise.all([
    api<Paginated<Video>>('care-message/videos/', { query: { limit: 50 } }),
    api<Paginated<Video>>('care-message/videos/', { query: { reviewed: 'true', limit: 10 } }),
    userZone(),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Vídeos para revisar</h1>
        <p className="text-sm text-gray-600">
          Vídeos que os seus pacientes mandaram na conversa, do mais antigo para o mais novo. O comentário vai para a conversa com o paciente.
        </p>
      </div>
      <ErrorFromQuery erro={erro} />
      <Card title={`A revisar (${pending.count})`}>
        {pending.results.length === 0 ? (
          <Empty title="Nenhum vídeo para revisar" />
        ) : (
          <ul className="flex flex-col divide-y divide-navy-100">
            {pending.results.map(video => (
              <li key={video.id} className="grid gap-4 py-4 md:grid-cols-[minmax(0,24rem)_1fr]">
                <Player video={video} />
                <div className="flex flex-col gap-3">
                  <Heading video={video} zone={zone} />
                  <form action={reviewVideo} className="flex flex-col gap-2">
                    <input type="hidden" name="id" value={video.id} />
                    <input type="hidden" name="back" value="/pro/videos" />
                    <label className="flex flex-col gap-1 text-sm font-medium">
                      Comentário para o paciente (opcional)
                      <textarea name="feedback" rows={3} maxLength={4000} className={inputClass} />
                    </label>
                    <div>
                      <Button type="submit">Marcar como revisado</Button>
                    </div>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
      {reviewed.results.length > 0 && (
        <Card title="Revisados recentemente">
          <ul className="flex flex-col divide-y divide-navy-100">
            {reviewed.results.map(video => (
              <li key={video.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <Heading video={video} zone={zone} />
                <span className="text-sm text-gray-600">revisado em {formatDateTime(video.reviewed_at!, zone)}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

import Link from 'next/link';
import { prescriptionAction, deletePrescription } from '@/app/pro/actions';
import { STATUS_LABELS, dateTime } from '@/lib/format';
import type { Prescription } from '@/lib/types';
import { Badge, Button, Notice } from './ui';

/** Title, status, version actions and version history of a prescription */
export function PrescriptionHeader({
  kind,
  relationship,
  prescription,
  title,
  versions,
  path,
  back,
}: {
  kind: 'nutrition' | 'training' | 'physio' | 'periodization';
  relationship: string;
  prescription: Prescription;
  title: string;
  versions: Prescription[];
  path: string;
  back: string;
}) {
  const hidden = (
    <>
      <input type="hidden" name="back" value={back} />
      <input type="hidden" name="kind" value={kind} />
      <input type="hidden" name="id" value={String(prescription.id)} />
      <input type="hidden" name="relationship" value={relationship} />
    </>
  );
  const status = prescription.status;

  return (
    <div className="flex flex-col gap-3">
      <Link href={`/pro/pacientes/${relationship}`} className="text-sm text-navy-700 underline">
        ← Ficha do paciente
      </Link>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold">{title}</h1>
          <Badge tone="gray">versão {prescription.version}</Badge>
          <Badge tone={status === 'published' ? 'neon' : status === 'draft' ? 'amber' : 'gray'}>{STATUS_LABELS[status]}</Badge>
        </div>
        <div className="flex flex-wrap gap-2">
          {status === 'draft' && (
            <>
              <form action={prescriptionAction}>
                {hidden}
                <Button name="action" value="publish" variant="secondary">
                  Publicar para o paciente
                </Button>
              </form>
              <form action={deletePrescription}>
                {hidden}
                <Button variant="danger">Excluir rascunho</Button>
              </form>
            </>
          )}
          {status !== 'draft' && !versions.some(v => v.status === 'draft') && (
            <form action={prescriptionAction}>
              {hidden}
              <Button name="action" value="new-version">
                Criar nova versão para editar
              </Button>
            </form>
          )}
          {status === 'published' && (
            <form action={prescriptionAction}>
              {hidden}
              <Button name="action" value="archive" variant="ghost" className="border border-navy-100">
                Arquivar
              </Button>
            </form>
          )}
        </div>
      </div>

      {status === 'draft' ? (
        <Notice>Rascunho: o paciente ainda não vê. Edite à vontade e publique quando estiver pronto.</Notice>
      ) : (
        <Notice>
          Versão publicada em {dateTime(prescription.published_at)}. Versões publicadas não mudam: para
          alterar, crie uma nova versão.
        </Notice>
      )}

      {versions.length > 1 && (
        <nav aria-label="Versões" className="flex flex-wrap gap-2 text-sm">
          {[...versions]
            .sort((a, b) => b.version - a.version)
            .map(v => (
              <Link
                key={v.id}
                href={`/pro/pacientes/${relationship}/${path}/${v.id}`}
                aria-current={v.id === prescription.id ? 'page' : undefined}
                className={`rounded-lg border px-2.5 py-1 ${v.id === prescription.id ? 'border-navy-900 bg-navy-900 text-white' : 'border-navy-100 bg-white'}`}
              >
                v{v.version} · {STATUS_LABELS[v.status]}
              </Link>
            ))}
        </nav>
      )}
    </div>
  );
}

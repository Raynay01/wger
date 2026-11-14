import { FOCUS_COLORS, FOCUS_LABELS, date } from '@/lib/format';
import type { TrainingBlock } from '@/lib/types';

/** The blocks of a periodization as a bar, each as wide as its weeks; marks today */
export function PeriodizationTimeline({ blocks, today }: { blocks: TrainingBlock[]; today?: string }) {
  const total = blocks.reduce((sum, b) => sum + b.weeks, 0);
  if (total === 0) {
    return null;
  }
  return (
    <div className="flex flex-col gap-2">
      <ol aria-label="Fases" className="flex w-full overflow-hidden rounded-xl border border-navy-100">
        {blocks.map(block => {
          const current = today !== undefined && block.start <= today && today <= block.end;
          return (
            <li
              key={block.id}
              style={{ flexGrow: block.weeks, flexBasis: 0 }}
              className={`min-w-0 border-r border-white/60 px-2 py-2 text-xs last:border-r-0 ${FOCUS_COLORS[block.focus] ?? 'bg-gray-100'} ${current ? 'ring-2 ring-inset ring-neon-500' : ''}`}
              title={`${FOCUS_LABELS[block.focus]}: ${date(block.start)} a ${date(block.end)}`}
            >
              <p className="truncate font-semibold">{block.name || FOCUS_LABELS[block.focus]}</p>
              <p className="truncate opacity-80">
                {block.weeks} {block.weeks === 1 ? 'semana' : 'semanas'}
                {current && ' · agora'}
              </p>
            </li>
          );
        })}
      </ol>
      <p className="flex justify-between text-xs text-gray-500">
        <span>{date(blocks[0].start)}</span>
        <span>
          {total} semanas · até {date(blocks[blocks.length - 1].end)}
        </span>
      </p>
    </div>
  );
}

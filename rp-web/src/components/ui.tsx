import Link from 'next/link';

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 font-bold tracking-tight ${dark ? 'text-white' : 'text-navy-900'}`}>
      <span aria-hidden className="grid size-8 place-items-center rounded-lg bg-neon-500 text-navy-900">K</span>
      <span className="text-lg">{process.env.NEXT_PUBLIC_APP_NAME || 'Kinutri'}</span>
    </span>
  );
}

export function Card({
  title,
  action,
  children,
  className = '',
}: {
  title?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl border border-navy-100 bg-white p-5 shadow-sm ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-base font-semibold text-navy-900">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
};

const VARIANTS = {
  primary: 'bg-navy-900 text-white hover:bg-navy-700',
  secondary: 'bg-neon-500 text-navy-900 hover:bg-neon-600',
  ghost: 'bg-transparent text-navy-700 hover:bg-navy-100',
  danger: 'bg-white text-red-700 border border-red-200 hover:bg-red-50',
};

export function Button({ variant = 'primary', className = '', ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    />
  );
}

export function LinkButton({
  href,
  variant = 'primary',
  children,
  className = '',
}: {
  href: string;
  variant?: keyof typeof VARIANTS;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </Link>
  );
}

export function Badge({ children, tone = 'navy' }: { children: React.ReactNode; tone?: 'navy' | 'neon' | 'gray' | 'red' | 'amber' }) {
  const tones = {
    navy: 'bg-navy-100 text-navy-800',
    neon: 'bg-neon-100 text-neon-700',
    gray: 'bg-gray-100 text-gray-600',
    red: 'bg-red-100 text-red-700',
    amber: 'bg-amber-100 text-amber-800',
  };
  return <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-medium text-navy-800">{label}</span>
      {children}
      {hint && <span className="text-xs text-gray-500">{hint}</span>}
    </label>
  );
}

export const inputClass =
  'w-full rounded-xl border border-navy-100 bg-white px-3 py-2 text-sm text-navy-900 placeholder:text-gray-400 focus:border-navy-700 focus:outline-none';

export function Notice({ children, tone = 'info' }: { children: React.ReactNode; tone?: 'info' | 'error' | 'success' }) {
  const tones = {
    info: 'border-navy-100 bg-navy-100/50 text-navy-800',
    error: 'border-red-200 bg-red-50 text-red-800',
    success: 'border-neon-500/40 bg-neon-100 text-navy-900',
  };
  return (
    <p role={tone === 'error' ? 'alert' : 'status'} className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>
      {children}
    </p>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-navy-100 bg-white/60 p-6 text-center">
      <p className="font-semibold text-navy-800">{title}</p>
      {children && <div className="mt-1 text-sm text-gray-500">{children}</div>}
    </div>
  );
}

/** Horizontal progress bar, e.g. consumed versus goal */
export function Meter({
  label,
  value,
  goal,
  unit,
  color = 'bg-neon-600',
}: {
  label: string;
  value: number;
  goal: number | null | undefined;
  unit: string;
  color?: string;
}) {
  const percent = goal ? Math.min(100, Math.round((value / goal) * 100)) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-navy-800">{label}</span>
        <span className="tabular-nums text-gray-600">
          {Math.round(value)}
          {goal ? ` / ${Math.round(goal)}` : ''} {unit}
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-navy-100" role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={goal ?? undefined} aria-label={label}>
        <div className={`h-full rounded-full ${color}`} style={{ width: `${goal ? percent : 0}%` }} />
      </div>
    </div>
  );
}

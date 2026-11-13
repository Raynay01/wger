import { Button, Field, inputClass } from '@/components/ui';

export function DevLoginForm({ next }: { next: string }) {
  return (
    <form action="/api/auth/password" method="post" className="mt-3 flex flex-col gap-3">
      <input type="hidden" name="next" value={next} />
      <Field label="Usuário ou e-mail">
        <input name="username" required autoComplete="username" className={inputClass} />
      </Field>
      <Field label="Senha">
        <input name="password" type="password" required autoComplete="current-password" className={inputClass} />
      </Field>
      <Button type="submit">Entrar</Button>
    </form>
  );
}

import type { Metadata } from 'next';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { Button, LinkButton, Logo } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { REFRESH_COOKIE } from '@/lib/session';

export const metadata: Metadata = { title: 'Convite' };

async function accept(formData: FormData) {
  'use server';
  const id = String(formData.get('id'));
  try {
    await api(`care-relationship/${id}/accept/`, {
      method: 'POST',
      body: { accept_terms: true, token: String(formData.get('token')) },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      redirect(`/convite/${id}?token=${formData.get('token')}&erro=${encodeURIComponent(error.message)}`);
    }
    throw error;
  }
  redirect('/app/compartilhamento');
}

/** Invitation link for patients who log in with another email than the invited one */
export default async function InvitationLinkPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ token?: string; erro?: string }>;
}) {
  const { id } = await params;
  const { token, erro } = await searchParams;
  const loggedIn = Boolean((await cookies()).get(REFRESH_COOKIE));

  return (
    <main className="grid min-h-dvh place-items-center bg-navy-900 px-4">
      <div className="w-full max-w-md rounded-3xl bg-white p-8">
        <Logo />
        <h1 className="mt-6 text-2xl font-bold">Você recebeu um convite</h1>
        <p className="mt-2 text-sm text-gray-600">
          Um profissional quer acompanhar você. Ao aceitar, você autoriza que ele prescreva e veja o que você registrar na área
          dele. Você pode encerrar quando quiser.
        </p>
        {erro && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {erro}
          </p>
        )}
        <div className="mt-6">
          {loggedIn ? (
            <form action={accept}>
              <input type="hidden" name="id" value={id} />
              <input type="hidden" name="token" value={token ?? ''} />
              <Button variant="secondary" className="w-full">
                Aceitar e autorizar
              </Button>
            </form>
          ) : (
            <LinkButton href={`/entrar?${new URLSearchParams({ next: `/convite/${id}?token=${token ?? ''}` })}`} className="w-full">
              Entrar para aceitar
            </LinkButton>
          )}
        </div>
      </div>
    </main>
  );
}

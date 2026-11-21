import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage, List, Section } from '@/components/LegalPage';
import { APP_NAME } from '@/lib/brand';
import { legalInfo } from '@/lib/legal';

export const metadata: Metadata = { title: 'Excluir a conta' };

export default async function DeleteAccountPage() {
  const info = await legalInfo();

  return (
    <LegalPage title={`Como excluir a sua conta do ${APP_NAME}`} updated="21 de novembro de 2026" info={info}>
      <Section title="No app">
        <p>
          Abra <strong>Configurações</strong> e depois <strong>Privacidade e seus dados</strong>. Digite EXCLUIR para
          confirmar e toque em pedir a exclusão.
        </p>
      </Section>

      <Section title="No site">
        <p>
          Entre na sua conta e abra{' '}
          <Link className="underline" href="/app/privacidade">
            Privacidade
          </Link>
          . Digite EXCLUIR para confirmar e peça a exclusão.
        </p>
        <p>Sem acesso à conta? Escreva para {info.contact} a partir do e-mail cadastrado.</p>
      </Section>

      <Section title="O que acontece">
        <List>
          <li>
            Na hora, os seus acompanhamentos são encerrados e os profissionais deixam de ver os seus dados, inclusive o
            que você tinha compartilhado.
          </li>
          <li>
            Depois a equipe do {APP_NAME} exclui a conta com os seus dados: perfil, treinos, alimentação, medidas,
            fotos, mensagens e avisos. Enquanto o pedido estiver em análise, você pode desistir na mesma tela, onde
            também aparece o andamento.
          </li>
          <li>
            Se algum profissional tiver registros clínicos sobre você que a norma do conselho obriga a guardar (por
            exemplo, avaliações), a equipe combina com ele o que fica guardado, e por quanto tempo, antes de concluir.
          </li>
          <li>Ficam guardados também o próprio pedido e os consentimentos, como prova.</li>
          <li>As cópias de segurança criptografadas que ainda contiverem os dados são apagadas em até 30 dias.</li>
        </List>
        <p>
          Antes de excluir, você pode baixar uma cópia dos seus dados na mesma tela (&quot;Baixar meus dados&quot;).
        </p>
      </Section>
    </LegalPage>
  );
}

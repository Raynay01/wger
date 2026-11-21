import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage, List, Section } from '@/components/LegalPage';
import { APP_NAME } from '@/lib/brand';
import { legalInfo } from '@/lib/legal';

export const metadata: Metadata = { title: 'Política de privacidade' };

export default async function PrivacyPolicyPage() {
  const info = await legalInfo();

  return (
    <LegalPage title="Política de privacidade" updated="21 de novembro de 2026" info={info}>
      <p>
        O {APP_NAME} reúne o acompanhamento de treino, fisioterapia e nutrição entre você e os profissionais que você
        escolher. Esta política explica quais dados guardamos, para quê, com quem eles são compartilhados e como você
        controla tudo isso, conforme a Lei Geral de Proteção de Dados (Lei 13.709/2018, LGPD).
      </p>

      <Section title="1. Quem cuida dos seus dados">
        <p>
          Controlador: <strong>{info.name}</strong>, CNPJ {info.document}. Para qualquer assunto sobre os seus dados,
          inclusive para falar com o encarregado (DPO): <strong>{info.contact}</strong>.
        </p>
        <p>
          Os profissionais que acompanham você (personal trainer, fisioterapeuta, nutricionista) também decidem sobre os
          registros que fazem no atendimento e respondem por eles perante os seus conselhos profissionais.
        </p>
      </Section>

      <Section title="2. Quais dados guardamos">
        <List>
          <li>
            <strong>Conta:</strong> nome, e-mail e, se você entrar com o Google, o identificador da conta Google. Para
            profissionais, também a profissão e o registro no conselho.
          </li>
          <li>
            <strong>Saúde e treino:</strong> anamnese, avaliações, medidas, peso, fotos de progresso, treinos com cargas e
            repetições, exercícios de fisioterapia, registros de dor, plano alimentar, diário alimentar e água.
          </li>
          <li>
            <strong>Comunicação e agenda:</strong> mensagens com os profissionais, com fotos e vídeos anexados, e os
            atendimentos marcados.
          </li>
          <li>
            <strong>Registros de controle:</strong> os consentimentos que você deu ou retirou, cada acesso de um
            profissional aos seus dados, os pedidos de exportação ou exclusão e, no celular, o código que permite
            enviar avisos ao aparelho.
          </li>
          <li>
            <strong>Registros técnicos:</strong> endereço IP e horário dos acessos ao servidor, usados para segurança.
            O endereço completo das páginas não é guardado nesses registros.
          </li>
        </List>
        <p>
          No site, usamos só os cookies necessários para manter você conectado (por até 120 dias sem uso) e para
          lembrar o seu fuso horário. Não usamos cookies de publicidade nem ferramentas de análise de comportamento, e o
          app não contém anúncios.
        </p>
      </Section>

      <Section title="3. Para que usamos">
        <List>
          <li>Prestar o serviço: mostrar o seu dia, guardar seus registros e sincronizar o app com o site.</li>
          <li>
            Permitir que os profissionais que você aceitou acompanhem você, cada um na área dele: o personal vê o treino,
            o fisioterapeuta a fisioterapia, o nutricionista a alimentação.
          </li>
          <li>Enviar avisos sobre mensagens, atendimentos e planos novos, por e-mail ou no celular.</li>
          <li>Manter a segurança da plataforma e cumprir obrigações legais.</li>
        </List>
        <p>
          Os dados de saúde são tratados com o seu consentimento específico, dado ao aceitar o convite de cada
          profissional e ao ligar cada compartilhamento, e para a tutela da sua saúde pelos profissionais que
          acompanham você (LGPD, art. 11). Os demais dados são tratados para executar o serviço que você contratou e
          para cumprir obrigações legais (LGPD, art. 7º).
        </p>
      </Section>

      <Section title="4. Com quem compartilhamos">
        <List>
          <li>
            <strong>Seus profissionais:</strong> só depois que você aceita o convite, só a área de cada um e o que você
            ligar em <em>Compartilhamento</em>. Você pode desligar quando quiser, e cada acesso fica registrado.
          </li>
          <li>
            <strong>Prestadores de serviço</strong> que tratam os dados em nosso nome e sob contrato: hospedagem dos
            servidores, envio de e-mails, Google (login com a conta Google) e Firebase, do Google (avisos no celular). O
            texto dos avisos não contém dados de saúde: ele só diz que há algo novo e pede para abrir o app.
          </li>
          <li>Autoridades, quando a lei ou uma ordem judicial exigir.</li>
        </List>
        <p>Não vendemos seus dados e não os usamos para publicidade.</p>
      </Section>

      <Section title="5. Por quanto tempo guardamos">
        <List>
          <li>Enquanto a sua conta existir.</li>
          <li>
            As cópias de segurança são criptografadas e apagadas depois de 30 dias, então um dado excluído pode ficar
            nelas até esse prazo.
          </li>
          <li>
            Os registros de consentimento e os pedidos de exclusão são guardados como prova, mesmo depois que a conta
            é excluída.
          </li>
          <li>
            Registros clínicos que a norma do conselho obriga o profissional a guardar ficam pelo prazo que essa norma
            exigir.
          </li>
        </List>
      </Section>

      <Section title="6. Como protegemos">
        <List>
          <li>Conexão sempre criptografada (HTTPS) e cópias de segurança criptografadas.</li>
          <li>
            Profissionais precisam de verificação em duas etapas e de um novo login a cada 30 dias; cada leitura que
            fazem dos seus dados fica registrada.
          </li>
          <li>Arquivos enviados passam por verificação de vírus; fotos ficam em área privada, sem endereço público.</li>
        </List>
      </Section>

      <Section title="7. Seus direitos">
        <p>Pela LGPD (art. 18), você pode, a qualquer momento:</p>
        <List>
          <li>
            Saber quais dados temos e receber uma cópia: em <em>Privacidade</em>, &quot;Baixar meus dados&quot; gera um
            arquivo com a sua conta, consentimentos, profissionais, o que você compartilhou e quem acessou.
          </li>
          <li>Corrigir dados incompletos ou errados, no próprio app ou no site.</li>
          <li>
            Retirar o consentimento: desligar um compartilhamento ou encerrar o acompanhamento com um profissional.
          </li>
          <li>
            Pedir a exclusão da conta e dos dados (veja <Link className="underline" href="/excluir-conta">como excluir a conta</Link>).
          </li>
          <li>Reclamar à Autoridade Nacional de Proteção de Dados (ANPD).</li>
        </List>
        <p>Para os demais pedidos, escreva para {info.contact}.</p>
      </Section>

      <Section title="8. Menores de idade">
        <p>
          O {APP_NAME} é destinado a maiores de 18 anos. O acompanhamento de menores depende do consentimento de um dos
          pais ou do responsável legal.
        </p>
      </Section>

      <Section title="9. Mudanças nesta política">
        <p>
          Quando esta política mudar, a data no início da página é atualizada. Mudanças importantes serão comunicadas
          antes de valer.
        </p>
      </Section>
    </LegalPage>
  );
}

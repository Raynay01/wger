import type { Metadata } from 'next';
import Link from 'next/link';
import { LegalPage, List, Section } from '@/components/LegalPage';
import { APP_NAME } from '@/lib/brand';
import { legalInfo } from '@/lib/legal';

export const metadata: Metadata = { title: 'Termos de uso' };

export default async function TermsPage() {
  const info = await legalInfo();

  return (
    <LegalPage title="Termos de uso" updated="21 de novembro de 2026" info={info}>
      <p>
        Estes termos valem para o site e o app {APP_NAME}, oferecidos por <strong>{info.name}</strong>, CNPJ{' '}
        {info.document}. Ao criar uma conta, você concorda com eles e com a{' '}
        <Link className="underline" href="/privacidade">
          política de privacidade
        </Link>
        .
      </p>

      <Section title="1. O que é o serviço">
        <p>
          Uma plataforma para pacientes e alunos acompanharem treino, fisioterapia e nutrição junto com os profissionais
          que escolherem, e para esses profissionais prescreverem e acompanharem. Também é possível usar o {APP_NAME}{' '}
          sem profissional, para registrar os próprios treinos, medidas e alimentação.
        </p>
      </Section>

      <Section title="2. Não substitui atendimento">
        <p>
          O {APP_NAME} é uma ferramenta de acompanhamento: não faz diagnóstico e não substitui consulta. As prescrições
          são de responsabilidade dos profissionais que as fazem. Em caso de dor intensa, mal-estar ou emergência,
          interrompa a atividade e procure atendimento (SAMU: 192).
        </p>
      </Section>

      <Section title="3. Profissionais">
        <List>
          <li>
            Declaram estar regularmente inscritos no conselho da sua profissão (CREF, CREFITO ou CRN) e respondem pelo
            atendimento que prestam e pelos registros que fazem.
          </li>
          <li>Só acessam a área da própria profissão e o que o paciente autorizar a mais.</li>
          <li>Usam a verificação em duas etapas e mantêm o acesso à conta em sigilo.</li>
        </List>
      </Section>

      <Section title="4. Sua conta">
        <List>
          <li>Você é responsável pelas informações que registra e por manter o acesso à sua conta em segurança.</li>
          <li>
            Não é permitido usar o serviço para fins ilegais, enviar conteúdo ofensivo ou de terceiros sem autorização,
            nem tentar acessar dados de outras pessoas.
          </li>
          <li>
            Contas que descumprirem estes termos podem ser suspensas. Você pode excluir a sua conta a qualquer momento (
            <Link className="underline" href="/excluir-conta">
              como excluir
            </Link>
            ).
          </li>
        </List>
      </Section>

      <Section title="5. Disponibilidade">
        <p>
          Trabalhamos para manter o serviço disponível e os dados protegidos, mas pode haver interrupções para
          manutenção ou por falhas. O app guarda os registros no celular e sincroniza quando a conexão volta.
        </p>
      </Section>

      <Section title="6. Código aberto">
        <p>
          O {APP_NAME} é baseado no projeto de código aberto wger e distribuído sob a licença AGPL-3.0. O código-fonte
          está disponível a quem usa o serviço.
        </p>
      </Section>

      <Section title="7. Mudanças e foro">
        <p>
          Estes termos podem mudar; a data no início da página mostra a versão em vigor, e mudanças importantes serão
          comunicadas antes de valer. Vale a lei brasileira, e fica eleito o foro de {info.court}, ressalvados os
          direitos do consumidor.
        </p>
        <p>Dúvidas: {info.contact}.</p>
      </Section>
    </LegalPage>
  );
}

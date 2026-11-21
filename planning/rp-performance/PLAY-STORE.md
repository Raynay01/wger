# ALMOVA na Play Store: o que preparar

O app Android já cumpre as exigências técnicas: identificador próprio
(`br.com.almova.app`), Android 16 como alvo (API 36), exclusão da conta dentro
do app, conexão só por HTTPS e avisos sem dados de saúde no texto. Este guia
reúne o resto: a conta, os textos da loja e as respostas dos formulários do
Play Console, conferidas com o que o app faz de fato.

## 1. Conta de desenvolvedor

| Opção | Custo | Observação |
|---|---|---|
| **Organização (recomendado)** | US$ 25, uma vez | Pede CNPJ e o número **D-U-N-S** (gratuito, pedido em dnb.com, leva alguns dias). A loja mostra o nome da empresa, o que passa mais confiança num app de saúde, e não exige o teste fechado abaixo. |
| Pessoa física | US$ 25, uma vez | Antes de publicar para todos, o Google exige um **teste fechado com pelo menos 12 testadores por 14 dias seguidos**. |

Em ambos os casos o Google confirma a identidade (documento) e um telefone.

## 2. Saúde (Health Connect): fora da primeira versão

O app herdou do wger a importação de peso, gordura corporal, passos, sono e
outros dados do **Health Connect** (relógios e balanças). A Play Store revisa
essas permissões à parte, com um formulário por permissão. Por isso a
primeira versão sai sem a importação: o APK não declara nenhuma permissão de
saúde (conferido no pacote gerado). Ela volta numa versão seguinte, com a
política de privacidade já citando cada dado (item 16 do README do app em
`extras/flutter-almova`).

## 3. Textos da loja (pt-BR)

**Nome do app** (até 30 caracteres): `ALMOVA`

**Descrição curta** (até 80 caracteres):

> Treino, fisioterapia e nutrição com seus profissionais, num só app.

**Descrição completa:**

> O ALMOVA reúne o acompanhamento do seu personal trainer, do seu
> fisioterapeuta e do seu nutricionista num só lugar.
>
> **Com seus profissionais**
> - Receba o treino, os exercícios de fisioterapia e o plano alimentar que eles
>   prescreverem.
> - Converse com cada profissional, com texto, fotos e vídeos.
> - Veja e cancele seus atendimentos na agenda.
> - Registre a dor dos exercícios: seu fisioterapeuta é avisado quando ela
>   passa do limite combinado.
> - Marque as refeições que seguiu e a água do dia.
>
> **Você decide o que cada um vê**
> Cada profissional vê só a área dele. Para que o nutricionista veja seu
> treino, por exemplo, você liga o compartilhamento, e pode desligar quando
> quiser. Seus dados podem ser baixados ou excluídos pelo próprio app.
>
> **Também sem profissional**
> Monte seus treinos, registre cargas e repetições, acompanhe peso, medidas e
> fotos de progresso. Funciona sem internet e sincroniza depois.
>
> O ALMOVA não substitui consulta: siga as orientações dos seus
> profissionais.

**Categoria:** Saúde e fitness. **Público-alvo:** 18 anos ou mais (evita as
regras de apps para crianças; dados de saúde de menores pedem o consentimento
dos responsáveis, a combinar com o advogado).

**Imagens exigidas:** ícone 512 × 512, imagem de destaque 1024 × 500 e pelo
menos duas capturas de tela do celular.

- **Capturas de tela: prontas.** Cinco, em 1080 × 2424, com dados de exemplo
  (fisioterapia, alimentação, conversa, agenda e compartilhamento), em
  `extras/flutter-almova/play-store/`. Os textos desta seção já estão no app
  (`fastlane/metadata/android/pt-BR`).
- **Ícone (512 × 512) e imagem de destaque (1024 × 500): prontos, provisórios**,
  com o "A" do ícone do app, na mesma pasta. Com o logotipo oficial, eu gero os
  dois de novo.

Só a página em pt-BR é do ALMOVA: as pastas dos outros idiomas em
`fastlane/metadata/android` ainda têm os textos do wger e não devem ser
enviadas.

## 4. Endereços exigidos

| Campo do Play Console | Endereço |
|---|---|
| Política de privacidade | `https://<domínio>/privacidade` (pública; minuta pronta, a revisar com o advogado) |
| Exclusão da conta pela web | `https://<domínio>/excluir-conta` (pública: explica o pedido pelo app e pelo site e o que é apagado) |
| E-mail de contato | um e-mail de suporte do ALMOVA (aparece na loja) |

## 5. Formulário "Segurança dos dados"

Respostas gerais:

- **Coleta ou compartilha dados?** Sim.
- **Os dados são criptografados em trânsito?** Sim (HTTPS).
- **O usuário pode pedir a exclusão?** Sim (no app e no site).
- **Compartilhamento com terceiros:** não. O envio ao profissional acontece
  só por convite aceito pelo paciente e com o compartilhamento que ele liga,
  o que o Google não conta como compartilhamento. Firebase (avisos) e o
  serviço de e-mail atuam como prestadores de serviço.

Dados coletados (todos **obrigatórios para o funcionamento**, nenhum para
publicidade ou análise, nenhum vendido):

| Tipo no formulário | O que é no ALMOVA | Finalidade |
|---|---|---|
| Informações pessoais: nome | nome do perfil | Funcionalidade, gerenciamento da conta |
| Informações pessoais: endereço de e-mail | login, convites, recuperação de senha | Gerenciamento da conta, comunicações |
| Informações pessoais: IDs do usuário | conta no servidor | Gerenciamento da conta |
| Saúde e fitness: informações de saúde | dor, fisioterapia, anamnese, avaliação, peso e medidas | Funcionalidade |
| Saúde e fitness: informações de fitness | treinos, cargas, repetições, diário alimentar | Funcionalidade |
| Mensagens: outras mensagens no app | conversa com o profissional | Funcionalidade |
| Fotos e vídeos | fotos de progresso, anexos da conversa | Funcionalidade |
| IDs do dispositivo ou outros IDs | token dos avisos do Firebase | Funcionalidade (avisos) |

Não coletados: localização, contatos, dados financeiros, histórico de
navegação, registros de falhas e diagnósticos automáticos (o app não tem
ferramenta de análise; os registros só saem quando o usuário os copia).

## 6. Outros formulários do Play Console

- **Classificação de conteúdo (IARC):** categoria "Utilidades, produtividade,
  comunicação e outros". Responda **sim** para "os usuários podem interagir ou
  trocar conteúdo" (a conversa) e não para o resto.
- **Apps de saúde:** marque as funções de condicionamento físico, nutrição e
  acompanhamento por profissionais de saúde. O app não é dispositivo médico e
  não faz diagnóstico.
- **Permissões sensíveis:** câmera e microfone (foto e vídeo na conversa e na
  galeria), avisos, alarme exato (lembrete do treino; o usuário autoriza).
- **Anúncios:** não contém anúncios.
- **Acesso ao app:** o revisor do Google precisa de uma conta de teste. Crie
  um paciente e um profissional de teste no servidor de homologação e informe
  usuário e senha só no formulário do Play Console.

## 7. Antes do envio, do meu lado

- A versão segue a numeração do wger (`2.1.2`): o servidor confere a versão
  mínima do app (`MIN_APP_VERSION`, hoje 2.1.0) e bloquearia um `1.0.0`. Para a
  loja só importa que o código da versão aumente a cada envio.
- Chave de assinatura definitiva (o Google guarda uma cópia com o "Play App
  Signing"; a chave de envio fica com você, fora do repositório).
- Construir o pacote `.aab` com o endereço definitivo do servidor e os dados
  do Firebase (a construção já foi conferida: 104 MB com todos os
  processadores; cada celular baixa cerca de 38 MB).

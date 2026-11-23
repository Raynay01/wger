# ALMOVA no ar de graça (homologação)

Para testar o site e o app no celular sem gastar nada: servidor gratuito da
Oracle, endereço gratuito do DuckDNS e HTTPS gratuito do Let's Encrypt. O
script `extras/docker/almova/instalar.sh` faz a parte técnica; você cria duas
contas e cola dois comandos.

Use só dados de teste nesta fase. Para pacientes de verdade: domínio próprio,
documentos de LGPD e backups conferidos (veja `ROTEIRO-HOMOLOGACAO.md`).

**No Brasil, o cadastro da Oracle pede CNPJ** (só oferece o tipo de cliente
"Corporate"). Sem CNPJ, teste de graça no GitHub Codespaces:
`TESTE-CODESPACES.md`. Não use CNPJ de outra pessoa ou empresa.

## 1. Conta na Oracle Cloud (gratuita)

1. Acesse **cloud.oracle.com** e clique em **Start for free** (Comece
   gratuitamente).
2. Preencha os dados. Em **Home Region** escolha **Brazil East (Sao Paulo)**.
   Não dá para trocar depois, e os recursos gratuitos ficam nela.
3. A Oracle pede um cartão **só para confirmar a identidade**. A conta fica
   no plano gratuito ("Always Free") e não cobra nada enquanto você não clicar
   em **Upgrade**. Pode aparecer uma reserva pequena e temporária no cartão,
   que some sozinha.

## 2. Criar o servidor

No painel da Oracle: **Menu > Compute > Instances > Create instance**.

| Campo | Valor |
|---|---|
| Name | `almova-homolog` |
| Image | **Canonical Ubuntu 24.04** (botão *Change image*) |
| Shape | **Ampere > VM.Standard.A1.Flex**, **4 OCPUs** e **24 GB** de memória (*Change shape*) |
| Networking | deixe o padrão, com **Assign a public IPv4 address** marcado |
| Add SSH keys | **Generate a key pair for me** e clique em **Save private key** (guarde esse arquivo) |
| Boot volume | marque *Specify a custom boot volume size* e use **100 GB** |

Clique em **Create**. Se aparecer *Out of capacity*, troque o
*Availability domain* ou tente de novo mais tarde: é comum em São Paulo.

Quando ficar **Running**, anote o **Public IP address**.

### Abrir as portas do site

**Menu > Networking > Virtual cloud networks**, clique na rede criada,
depois em **Security Lists > Default Security List > Add Ingress Rules**:

| Source CIDR | IP Protocol | Destination Port Range |
|---|---|---|
| `0.0.0.0/0` | TCP | `80,443` |

## 3. Endereço gratuito no DuckDNS

1. Acesse **duckdns.org** e entre com a conta do Google ou do GitHub.
2. Em *sub domain* digite `almova` (se estiver ocupado, por exemplo
   `almova-homolog`) e clique em **add domain**.
3. No campo *current ip* do endereço, coloque o **IP do servidor** e clique em
   **update ip**.
4. Copie o **token** que aparece no alto da página.

O endereço fica `https://almova.duckdns.org` (ou o nome que você escolheu).

## 4. Login com Google (gratuito)

O site entra com a conta Google das pessoas. Para isso o Google precisa
conhecer o endereço do ALMOVA:

1. Acesse **console.cloud.google.com** com a sua conta Google e crie um projeto
   chamado `ALMOVA` (seletor de projetos no alto > **Novo projeto**).
2. No menu, abra **APIs e serviços > Tela de consentimento OAuth** (em algumas
   contas aparece como **Google Auth Platform**). Preencha:
   - nome do app: `ALMOVA`; e-mail de suporte: o seu;
   - público: **Externo**;
   - e-mail de contato: o seu. Conclua.
3. Ainda ali, em **Público**, clique em **Publicar app** (senão só as contas
   cadastradas como teste conseguem entrar). O ALMOVA só pede nome e e-mail,
   então o Google não exige verificação.
4. Em **Clientes** (ou **Credenciais > Criar credenciais > ID do cliente
   OAuth**): tipo **Aplicativo da Web**, nome `ALMOVA site`, e em **Origens
   JavaScript autorizadas** adicione `https://almova.duckdns.org` (o seu
   endereço). Não precisa de URI de redirecionamento. Clique em **Criar**.
5. Copie o **ID do cliente** (termina em `.apps.googleusercontent.com`). Ele não
   é senha: o script do passo 5 pede ele. A "chave secreta do cliente" não é
   usada; não copie para lugar nenhum.

## 5. Instalar (dois comandos)

Entre no servidor pelo terminal. No Windows, abra o **PowerShell**, na pasta
onde salvou a chave:

```bash
ssh -i ssh-key.key ubuntu@IP-DO-SERVIDOR
```

(Se o Windows reclamar das permissões da chave: clique com o botão direito no
arquivo > Propriedades > Segurança > Avançado > Desabilitar herança, e deixe só
o seu usuário com leitura.)

Já dentro do servidor:

```bash
git clone -b claude/happy-goldberg-8nupoc https://github.com/Raynay01/wger.git almova
```

```bash
sudo bash almova/extras/docker/almova/instalar.sh
```

O script pergunta o endereço (`almova.duckdns.org`), seu e-mail, o token do
DuckDNS e o ID do cliente Google (passo 4). Depois ele instala o Docker, abre as
portas, gera as senhas e chaves, constrói e sobe tudo com HTTPS, e carrega
exercícios e a tabela TACO. A primeira vez leva de 15 a 30 minutos. No fim ele
mostra o endereço.

Para atualizar depois de mudanças no ALMOVA (não pergunta nada de novo):

```bash
cd almova && git pull && sudo bash extras/docker/almova/instalar.sh
```

## 6. Usar e instalar no celular

1. No computador ou no celular, abra o endereço e toque em **Entrar com
   Google**. A conta é criada na hora.
2. Para ser profissional: **Sou profissional**, crie a organização e o registro
   no conselho. Profissionais precisam da verificação em duas etapas: instale
   no celular um app autenticador (Google Authenticator, por exemplo) e leia o
   QR code que o site mostra. Guarde os códigos de recuperação.
3. Instalar como app, pelo link, sem loja:
   - **Android (Chrome):** na área do paciente aparece "Use o ALMOVA como app":
     toque em **Instalar o app** (ou menu ⋮ > **Instalar app**).
   - **iPhone (Safari):** **Compartilhar** > **Adicionar à Tela de Início** >
     **Adicionar**.
4. Teste: o ícone na tela inicial abre em tela cheia; com o modo avião, aparece
   "Sem conexão".

Para convidar um paciente de teste: na área profissional, **Convidar paciente**,
e mande o link do convite (WhatsApp serve).

## 7. Depois (opcional nesta fase)

- O app Android completo (funciona sem internet): me passe o endereço e eu gero
  o APK. Instala direto pelo arquivo, sem Play Store.
- E-mails (convites, senha esquecida) ficam desligados até configurar um
  serviço de envio. Gratuito: **Brevo** (300 e-mails por dia). Com os dados
  dele, coloque no `homolog.env` do servidor `ENABLE_EMAIL=True`,
  `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e rode
  `sudo docker compose up -d` na pasta `almova/extras/docker/almova`.
- Avisos no celular (mensagem nova, consulta marcada): gratuitos pelo
  **Firebase**. Crie um projeto em console.firebase.google.com, adicione um app
  Android com o pacote `br.com.almova.app` e me passe os quatro identificadores
  do app (não são senhas): eu gero o APK com eles. A chave da conta de serviço
  é secreta e vai só para o servidor (seção "Celular (push)" do `README.md` da
  pilha), nunca para o chat.

## Limites do gratuito

- A Oracle pode recuperar servidores gratuitos que ficam parados (uso muito
  baixo por vários dias). Para testes isso basta; para produção, use o
  roteiro com servidor contratado.
- O DuckDNS é um endereço de teste. Para os pacientes, o domínio próprio
  (`almova.com.br`, cerca de R$ 40 por ano) passa mais confiança.
- Na Play Store, a publicação exige a conta de desenvolvedor do Google
  (US$ 25, uma vez só). Até lá, o site é instalado como app pelo link (Android
  e iPhone), e o app Android completo, direto pelo arquivo APK.
- Use só dados de teste até a revisão jurídica (`O-QUE-FALTA.md`, fase 2).

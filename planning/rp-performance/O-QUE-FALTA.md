# ALMOVA: o que falta, na ordem

A parte técnica está pronta: servidor, site, app Android, segurança, backups,
página da loja e as minutas dos textos legais. O que falta depende de contas,
dados da empresa e decisões suas. Siga na ordem; cada passo diz o que me passar.

**Nunca cole senhas, chaves ou tokens no chat.** Onde houver um segredo, o
passo diz onde ele entra.

## Fase 1: homologação gratuita (testar no celular)

**Sem CNPJ:** a Oracle não aceita o cadastro (no Brasil, só como empresa). Para
testar já, de graça, siga `TESTE-CODESPACES.md` no lugar dos passos 2, 3 e 5;
o passo 4 (Google) continua. Com CNPJ, os passos abaixo deixam o ALMOVA no ar o
tempo todo.

| # | O que fazer | Onde está explicado | O que me passar |
|---|---|---|---|
| 1 | Criar o fork do app: abra github.com/wger-project/flutter e clique em **Fork** (deixe o nome `flutter`) | | só avisar: eu passo o app para lá |
| 2 | Conta na Oracle Cloud, servidor gratuito e portas 80/443 | `HOMOLOGACAO-GRATUITA.md`, seções 1 e 2 | nada |
| 3 | Endereço gratuito no DuckDNS | `HOMOLOGACAO-GRATUITA.md`, seção 3 | nada |
| 4 | ID do cliente Google para o login do site (gratuito) | `HOMOLOGACAO-GRATUITA.md`, seção 4 | nada: o script pede |
| 5 | Rodar o `instalar.sh` no servidor (dois comandos) | `HOMOLOGACAO-GRATUITA.md`, seção 5 | o endereço (ex.: `almova.duckdns.org`) |
| 6 | Entrar no site, instalar como app no celular e testar | `HOMOLOGACAO-GRATUITA.md`, seção 6 | o que estranhar |
| 7 | Projeto no Firebase (gratuito), app Android `br.com.almova.app` | `HOMOLOGACAO-GRATUITA.md`, seção 7 | os 4 identificadores do app (não são senhas) |
| 8 | E-mail gratuito no Brevo, dados no `homolog.env` do servidor | `HOMOLOGACAO-GRATUITA.md`, seção 7 | nada |

O site instalado pelo link já serve no Android e no iPhone. Com o endereço
(passo 5), eu gero também o APK do app Android completo. Roteiro de teste:
`ROTEIRO-HOMOLOGACAO.md`, seção 6.

## Fase 2: antes de pacientes de verdade

| # | O que fazer | Onde está explicado | O que me passar |
|---|---|---|---|
| 9 | Abrir a empresa (CNPJ) e criar um e-mail para assuntos de privacidade | | o nome, o CNPJ e o e-mail (são públicos nas páginas) |
| 10 | Advogado revisa a política de privacidade, os termos e a página de exclusão (já no ar em `/privacidade`, `/termos` e `/excluir-conta`), e o texto de consentimento dos convites | | as mudanças que ele pedir: eu aplico |
| 11 | Logotipo oficial (arquivo SVG ou PNG grande) | | o arquivo: eu troco no app, no site e na loja |
| 12 | Domínio próprio, ex.: `almova.com.br` no registro.br (cerca de R$ 40/ano), conferindo a marca no INPI | `ROTEIRO-HOMOLOGACAO.md`, seção 2 | o domínio |
| 13 | Chave do backup e teste de restauração | `extras/backup/README.md` | nada: a chave privada fica só com você |

Depois do passo 10, no `homolog.env` do servidor: `ALMOVA_LEGAL_NAME`,
`ALMOVA_LEGAL_DOCUMENT`, `ALMOVA_PRIVACY_EMAIL`, `ALMOVA_LEGAL_COURT` e
`ALMOVA_LEGAL_APPROVED=1` (README da pilha, "Política de privacidade e termos de
uso").

## Fase 3: Play Store

| # | O que fazer | Onde está explicado | O que me passar |
|---|---|---|---|
| 14 | Número D-U-N-S da empresa (gratuito, alguns dias) e conta de desenvolvedor do Google como organização (US$ 25) | `PLAY-STORE.md`, seção 1 | nada |
| 15 | Chave de envio do app e os segredos no GitHub (abaixo) | esta página | só avisar |
| 16 | Rodar a construção no GitHub e enviar o `.aab` no Play Console | esta página | nada |
| 17 | Preencher os formulários do Play Console | `PLAY-STORE.md`, seções 3 a 6 (respostas prontas) | dúvidas |

### Passo 15: chave de envio

A chave assina o app que você envia ao Google; o Google guarda a chave final
("Play App Signing"). Gere a sua no servidor da Oracle, que já tem o Docker:

```bash
sudo docker run --rm -it -v "$HOME:/chave" eclipse-temurin:21 keytool -genkeypair -keystore /chave/almova-upload.jks -alias upload -keyalg RSA -keysize 4096 -validity 10000 -dname "CN=ALMOVA"
```

Ele pede uma senha: guarde-a num gerenciador de senhas. Depois, copie o arquivo
para um lugar seguro fora do servidor e gere o texto para o GitHub:

```bash
base64 -w0 ~/almova-upload.jks
```

No fork do app no GitHub: **Settings > Secrets and variables > Actions**:

- em *Secrets*: `ALMOVA_UPLOAD_KEYSTORE` (o texto do `base64`) e
  `ALMOVA_UPLOAD_PASSWORD` (a senha);
- em *Variables*: `FCM_API_KEY`, `FCM_APP_ID`, `FCM_SENDER_ID` e
  `FCM_PROJECT_ID` (os identificadores do Firebase, passo 7).

Depois apague o arquivo do servidor (`rm ~/almova-upload.jks`), mantendo a
cópia segura.

### Passo 16: construir e enviar

No fork: **Actions > ALMOVA Android > Run workflow**, com o endereço do
servidor. Em uns 15 minutos, a execução oferece para baixar `almova-play-store`
(o `.aab` para o Play Console) e `almova-apk` (APKs para instalar direto).

## O que eu faço quando você me passar algo

- **Endereço do servidor:** APK de teste apontando para ele.
- **Fork criado:** passo os 21 patches do app para lá, com as imagens da loja.
- **Firebase:** confiro os avisos no celular de ponta a ponta.
- **Logotipo:** ícone do app, ícone e imagem da loja, capturas de tela e site.
- **Mudanças do advogado:** aplico nos textos e nos consentimentos.
- **Domínio:** ajusto o servidor e gero o app definitivo.

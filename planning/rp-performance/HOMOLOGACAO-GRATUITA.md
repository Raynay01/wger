# ALMOVA no ar de graça (homologação)

Para testar o site e o app no celular sem gastar nada: servidor gratuito da
Oracle, endereço gratuito do DuckDNS e HTTPS gratuito do Let's Encrypt. O
script `extras/docker/almova/instalar.sh` faz a parte técnica; você cria duas
contas e cola dois comandos.

Use só dados de teste nesta fase. Para pacientes de verdade: domínio próprio,
documentos de LGPD e backups conferidos (veja `ROTEIRO-HOMOLOGACAO.md`).

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

## 4. Instalar (dois comandos)

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

O script pergunta o endereço (`almova.duckdns.org`), seu e-mail e o token do
DuckDNS. Depois ele instala o Docker, abre as portas, gera as senhas e chaves,
constrói e sobe tudo com HTTPS, e carrega exercícios e a tabela TACO. A primeira
vez leva de 15 a 30 minutos. No fim ele mostra o endereço.

Para atualizar depois de mudanças no ALMOVA:

```bash
cd almova && git pull && sudo bash extras/docker/almova/instalar.sh
```

## 5. Depois de instalado

- Abra o endereço no navegador e crie uma conta.
- Me passe o endereço: eu gero o APK apontando para ele e você instala no
  celular (sem Play Store nesta fase).
- E-mails (convites, senha esquecida) ficam desligados até configurar um
  serviço de envio. Gratuito: **Brevo** (300 e-mails por dia). Com os dados
  dele, coloque no `homolog.env` do servidor `ENABLE_EMAIL=True`,
  `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` e rode
  `sudo docker compose up -d` na pasta `almova/extras/docker/almova`.

## Limites do gratuito

- A Oracle pode recuperar servidores gratuitos que ficam parados (uso muito
  baixo por vários dias). Para testes isso basta; para produção, use o
  roteiro com servidor contratado.
- O DuckDNS é um endereço de teste. Para os pacientes, o domínio próprio
  (`almova.com.br`, cerca de R$ 40 por ano) passa mais confiança.
- Na Play Store, a publicação exige a conta de desenvolvedor do Google
  (US$ 25, uma vez só). Até lá, o app é instalado direto pelo arquivo APK.

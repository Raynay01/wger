# ALMOVA: homologação e produção com Docker

O mesmo `compose.yml` serve para homologação e produção; muda só o arquivo de
ambiente. Primeiro tudo roda em homologação; só depois de aprovado vai para
produção.

## Versões fixadas (16/11/2026)

Cada imagem de terceiros está fixada por versão **e** digest (a impressão do
conteúdo). Assim, uma reinstalação usa exatamente os mesmos arquivos.

| Serviço | Imagem |
|---|---|
| Banco | `postgres:18.7-alpine` |
| Cache e filas | `redis:8.10.3-alpine` |
| Sincronização offline | `journeyapps/powersync-service:1.28.3` |
| Antivírus | `clamav/clamav:1.5.4` |
| Proxy | `nginx:1.30.6-alpine3.24` |
| Servidor (construído daqui) | base `wger/base:2026-11-01` (Ubuntu 24.04, Python 3.12), Node 24.22.3 só na construção, dependências Python exatamente as do `uv.lock`, conferidas por hash |
| Site (construído daqui) | `node:24.22.3-alpine` (Node 24 LTS), dependências exatamente as do `package-lock.json` |
| Backup | `postgres:18.7-alpine` + `age` 1.3.2 compilado de `golang:1.27.4-alpine` |

Para atualizar uma versão: troque a etiqueta e o digest, construa, rode em
homologação os testes da seção 4 e só então leve para produção.

## 1. Preparar

```bash
cp homolog.env.example homolog.env
```

Preencha no `homolog.env` (nunca vai para o Git):

- `SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `JWT_PUBLIC_KEY` e `JWT_PRIVATE_KEY`: saída de `python3 manage.py generate-jwt-keys`
- `POSTGRES_PASSWORD`: `openssl rand -hex 16`
- `BACKUP_AGE_RECIPIENTS`: a chave pública do backup (ver `extras/backup/README.md`)

Em produção use outro arquivo (`ALMOVA_ENV_FILE=production.env`) com os
endereços reais, `X_FORWARDED_PROTO_HEADER_SET=True`, `SECURE_HSTS_SECONDS=63072000`
e `KINUTRI_DEV_LOGIN=0`.

## 2. Subir

```bash
docker compose build
docker compose up -d
docker compose exec web python3 manage.py setup-powersync-storage
docker compose restart powersync
```

Dados de base (uma vez):

```bash
docker compose exec web python3 manage.py import-taco-products
docker compose exec web python3 manage.py import-exercise-names-pt
```

Fotos de progresso (galeria) enviadas antes desta versão: copie para o
armazenamento privado. Os originais na pasta pública só saem com
`--delete-public`, depois de conferir o backup:

```bash
docker compose exec web python3 manage.py copy-gallery-to-private
```

O site fica em `http://localhost:8080` (`ALMOVA_HTTP_PORT`). O HTTPS fica na
frente (balanceador ou proxy do servidor), que manda `X-Forwarded-Proto`.

O que fica público: o site, `/api/v2/` e `/allauth/` (app do celular), `/ps/`
(sincronização) e os arquivos estáticos. As páginas próprias do wger e o admin
do Django ficam só na rede interna (acesse por SSH ou VPN).

## Avisos fora do app

- **E-mail:** configure o servidor de e-mail (`ENABLE_EMAIL=True`, `EMAIL_HOST`,
  `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `FROM_EMAIL`). O aviso de
  mensagens sem ler roda sozinho a cada 5 minutos (`celery_beat`).
- **Celular (push):** crie um projeto no Firebase, gere a chave de uma conta de
  serviço com o papel "Firebase Cloud Messaging API Admin" e monte o arquivo no
  servidor, por exemplo acrescentando ao serviço `web` e `celery_worker`:

  ```yaml
      volumes:
        - /caminho/seguro/firebase.json:/run/secrets/firebase.json:ro
  ```

  e no `.env`: `FCM_PROJECT_ID=<id do projeto>` e
  `FCM_SERVICE_ACCOUNT_FILE=/run/secrets/firebase.json`. Os avisos passam pelos
  servidores do Google, por isso só levam o texto genérico, sem dados de saúde.

## 3. Backup

```bash
docker compose --profile backup run --rm backup
```

Agende no cron do servidor (todo dia) e copie a pasta `BACKUP_HOST_DIR` para
fora do servidor. Restauração e teste: `extras/backup/README.md`.

## 4. Testes de homologação

1. Teste completo no navegador contra a pilha (no repositório, pasta `rp-web`,
   com `KINUTRI_DEV_LOGIN=1` só em homologação):

   ```bash
   KINUTRI_WEB_URL=http://localhost:8080 KINUTRI_EXPECT_PRODUCTION=1 \
   KINUTRI_MANAGE="docker compose -f ../extras/docker/almova/compose.yml exec -T web python3 manage.py" \
   npm run test:e2e
   ```

2. Teste de restauração do backup:

   ```bash
   docker compose --profile backup run --rm --entrypoint test-restore.sh \
     -e BACKUP_AGE_IDENTITY=/keys/almova-backup.key -v /caminho/da/chave:/keys:ro \
     -e RESTORE_TEST_DB=almova_teste_restauracao backup
   ```

Resultado em 16/11/2026: os 37 passos do teste no navegador passaram; o teste de
restauração deu 137 tabelas e 24.212 linhas idênticas, além dos anexos do chat.

## Construir atrás de um proxy que reassina HTTPS

Passe a autoridade certificadora do proxy como segredo de construção (não fica
na imagem):

```bash
docker build --secret id=build_ca,src=/caminho/ca.crt ...
```

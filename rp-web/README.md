# ALMOVA web

App web do ALMOVA (treino, reabilitação e nutrição) para pacientes e profissionais, sobre a API do backend Django
deste repositório. Next.js 16 (App Router), React 19 e Tailwind CSS 4, tudo em português.

- **Paciente** (`/app`): Meu Dia (treino, refeições, metas, água e fisioterapia do dia), convites com consentimento,
  compartilhamento por escopo, evolução e privacidade (baixar os dados, pedir a exclusão da conta).
- **Profissional** (`/pro`): organização e registro no conselho, convites, ficha do paciente (prescrições, diário,
  registros de treino e dor, dados compartilhados, observações), construtores de dieta, treino e protocolo,
  publicação e versões, e alertas de dor.

O nome do app fica em `src/lib/brand.ts` (ou `NEXT_PUBLIC_APP_NAME`).

## Login

O login é com a conta Google. O navegador recebe o ID token do Google (Google Identity Services); o servidor web o
envia para `POST /allauth/app/v1/auth/provider/token` do Django, que valida o token com o Google e devolve os JWT da
API. Os tokens ficam em cookies `httpOnly`; o `src/proxy.ts` os renova antes de expirarem.

Configuração do Google:

1. No Google Cloud Console, crie um "ID do cliente OAuth" do tipo **Aplicativo da Web** e cadastre a origem do app
   (ex.: `https://app.almova.com.br` e `http://localhost:3000`).
2. No Django: `GOOGLE_CLIENT_ID` (e `GOOGLE_CLIENT_SECRET`).
3. No app web: `NEXT_PUBLIC_GOOGLE_CLIENT_ID` com o mesmo ID.

`KINUTRI_DEV_LOGIN=1` mostra também um formulário de usuário e senha, para desenvolvimento e testes. Não use em
produção.

## Convites por e-mail

Criar um convite não envia nada. O profissional envia quando quiser, pelo botão "Enviar convite por e-mail"
(reenvio no máximo a cada 10 minutos), ou copia o link do convite e manda por outro canal. O e-mail sai pelo
servidor de e-mail configurado no Django (variáveis de SMTP do wger) e o link aponta para `WEB_APP_URL`
(ex.: `https://app.almova.com.br`). Em desenvolvimento os e-mails só aparecem no terminal do Django.

## Rodar localmente

```bash
# Backend (na raiz do repositório)
uv sync --group dev
mkdir -p db
DJANGO_SETTINGS_MODULE=settings.local_dev uv run ./manage.py migrate
DJANGO_SETTINGS_MODULE=settings.local_dev uv run ./manage.py loaddata languages licenses setting_repetition_units setting_weight_units groups gym_config categories equipment muscles exercise-base-data translations test-ingredients
DJANGO_SETTINGS_MODULE=settings.local_dev uv run ./manage.py import-taco-products   # alimentos da TACO
DJANGO_SETTINGS_MODULE=settings.local_dev uv run ./manage.py import-exercise-names-pt   # nomes dos exercícios em português
DJANGO_SETTINGS_MODULE=settings.local_dev uv run ./manage.py runserver 127.0.0.1:8100
```

O login headless precisa de um par de chaves JWT: gere com `uv run ./manage.py generate-jwt-keys` e coloque em
`settings/local_dev_extra.py` (veja `settings/ci.py` para o formato), arquivo que o Git ignora.

```bash
# App web
cd rp-web
cp .env.example .env.local   # ajuste as variáveis
npm install
npm run dev                  # http://127.0.0.1:3000
```

## Testes

- `npm run check:types`: TypeScript.
- `npm run test:e2e`: percorre o uso real no navegador (Playwright) com os dois servidores rodando e
  `KINUTRI_DEV_LOGIN=1`. Cria um nutricionista que também é personal, uma fisioterapeuta e uma paciente. Eles se
  configuram, convidam, aceitam, montam e publicam dieta, treino e protocolo; a paciente usa o Meu Dia (refeição,
  água, exercício, dor) e compartilha dados; depois o teste confere o diário, os alertas e as versões. As capturas
  ficam em `e2e/screenshots/`.

## Licença

AGPL-3.0, como o wger. Quem usa o app pela rede tem direito ao código-fonte da versão em uso.

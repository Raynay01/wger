#!/bin/bash
# ALMOVA: installs the staging (homologação) stack on a fresh Ubuntu 24.04
# server, ARM (Oracle Cloud Always Free) or x86, with HTTPS from Let's Encrypt.
#
#   git clone -b claude/happy-goldberg-8nupoc https://github.com/Raynay01/wger.git almova
#   sudo bash almova/extras/docker/almova/instalar.sh
#
# It asks for the address (e.g. almova.duckdns.org), an email for the
# certificate and, optionally, the DuckDNS token. Run it again after an
# update: the passwords and keys of homolog.env are kept.
#
# ALMOVA_SKIP_SYSTEM=1 skips the packages, firewall and DuckDNS, and
# ALMOVA_SKIP_BUILD=1 uses the images already built (tests).
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31mErro: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || fail "rode com sudo: sudo bash $0"

# --- Address and email -------------------------------------------------------
if [ -f .env ]; then
    # shellcheck disable=SC1091
    set -a; . ./.env; set +a
fi
if [ -z "${ALMOVA_DOMAIN:-}" ]; then
    read -rp "Endereço do ALMOVA (ex.: almova.duckdns.org): " ALMOVA_DOMAIN
fi
if [ -z "${ACME_EMAIL:-}" ]; then
    read -rp "Seu e-mail (avisos do certificado HTTPS): " ACME_EMAIL
fi
[[ "$ALMOVA_DOMAIN" =~ ^[a-z0-9.-]+\.[a-z]{2,}$ ]] || fail "endereço inválido: $ALMOVA_DOMAIN"
[[ "$ACME_EMAIL" == *@* ]] || fail "e-mail inválido: $ACME_EMAIL"
# Asked once: the cron entry of the first run keeps the address up to date
if [[ "$ALMOVA_DOMAIN" == *.duckdns.org && -z "${DUCKDNS_TOKEN:-}" && ! -f /etc/cron.d/almova-duckdns ]]; then
    read -rp "Token do DuckDNS (Enter para pular): " DUCKDNS_TOKEN
fi
# The web app logs in with the Google account: without the client ID nobody can log in
if [ -z "${NEXT_PUBLIC_GOOGLE_CLIENT_ID:-}" ]; then
    echo "O login no site é com a conta Google. O ID do cliente é gratuito (guia HOMOLOGACAO-GRATUITA.md, passo 4)."
    read -rp "ID do cliente Google (termina em .apps.googleusercontent.com; Enter para pular): " NEXT_PUBLIC_GOOGLE_CLIENT_ID
fi
NEXT_PUBLIC_GOOGLE_CLIENT_ID="${NEXT_PUBLIC_GOOGLE_CLIENT_ID// /}"
if [ -n "$NEXT_PUBLIC_GOOGLE_CLIENT_ID" ]; then
    [[ "$NEXT_PUBLIC_GOOGLE_CLIENT_ID" =~ ^[0-9a-z-]+\.apps\.googleusercontent\.com$ ]] \
        || fail "ID do cliente Google inválido: $NEXT_PUBLIC_GOOGLE_CLIENT_ID"
fi

# --- System: Docker, firewall, DuckDNS -----------------------------------------
if [ "${ALMOVA_SKIP_SYSTEM:-0}" != 1 ]; then
    say "Instalando o Docker"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io docker-compose-v2 git curl openssl >/dev/null
    systemctl enable --now docker

    say "Abrindo as portas 80 e 443"
    # Oracle's Ubuntu images reject everything but SSH in iptables
    if iptables -S INPUT 2>/dev/null | grep -q -- '-j REJECT'; then
        for port in 80 443; do
            iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
                || iptables -I INPUT 1 -p tcp --dport "$port" -j ACCEPT
        done
        iptables -C INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null \
            || iptables -I INPUT 1 -p udp --dport 443 -j ACCEPT
        if command -v netfilter-persistent >/dev/null; then netfilter-persistent save >/dev/null; fi
    fi
    if command -v ufw >/dev/null && ufw status | grep -q active; then
        ufw allow 80/tcp >/dev/null; ufw allow 443 >/dev/null
    fi

    if [ -n "${DUCKDNS_TOKEN:-}" ]; then
        say "Apontando $ALMOVA_DOMAIN para este servidor (DuckDNS)"
        name="${ALMOVA_DOMAIN%.duckdns.org}"
        answer=$(curl -fsS "https://www.duckdns.org/update?domains=$name&token=$DUCKDNS_TOKEN&ip=")
        [ "$answer" = OK ] || fail "o DuckDNS recusou: confira o nome e o token"
        # Keep the address up to date if the IP changes
        echo "*/5 * * * * root curl -fsS 'https://www.duckdns.org/update?domains=$name&token=$DUCKDNS_TOKEN&ip=' >/dev/null" \
            > /etc/cron.d/almova-duckdns
        chmod 600 /etc/cron.d/almova-duckdns
    fi
fi

# --- Configuration ---------------------------------------------------------------
say "Gravando a configuração"
compose_file=compose.yml
if [ "$(uname -m)" = aarch64 ]; then
    # The official ClamAV image has no arm64 build
    compose_file=compose.yml:compose.arm64.yml
fi
cat > .env <<EOF
ALMOVA_DOMAIN=$ALMOVA_DOMAIN
ACME_EMAIL=$ACME_EMAIL
ALMOVA_HTTP_PORT=127.0.0.1:8080
COMPOSE_FILE=$compose_file
NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID
${ACME_CA_OPTION:+ACME_CA_OPTION=$ACME_CA_OPTION}
EOF
chmod 600 .env

set_env() {
    # set_env NAME VALUE: replaces the line NAME=... of homolog.env
    python3 - "$1" "$2" <<'PY'
import re, sys
name, value = sys.argv[1], sys.argv[2]
text = open('homolog.env').read()
line = f'{name}={value}'
pattern = re.compile(rf'^{re.escape(name)}=.*$', re.M)
text = pattern.sub(lambda m: line, text, count=1) if pattern.search(text) else text.rstrip('\n') + f'\n{line}\n'
open('homolog.env', 'w').write(text)
PY
}

if [ ! -f homolog.env ]; then
    # New passwords would not open an existing database
    if docker compose ps -a -q db 2>/dev/null | grep -q . \
        || docker volume ls -q | grep -qx "$(docker compose config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["name"])')_postgres-data"; then
        fail "já existe um banco do ALMOVA neste servidor, mas não o homolog.env com a senha dele. Restaure o homolog.env do backup."
    fi
    cp homolog.env.example homolog.env
    set_env SECRET_KEY "$(openssl rand -base64 48 | tr -d '\n/+=' | cut -c1-60)"
    set_env POSTGRES_PASSWORD "$(openssl rand -hex 16)"
fi
chmod 600 homolog.env
url="https://$ALMOVA_DOMAIN"
set_env SITE_URL "$url"
set_env WEB_APP_URL "$url"
set_env CSRF_TRUSTED_ORIGINS "$url"
set_env DJANGO_ALLOWED_HOSTS "$ALMOVA_DOMAIN,localhost,web"
set_env X_FORWARDED_PROTO_HEADER_SET True
set_env KINUTRI_DEV_LOGIN 0
# The same client ID for the server, which checks the Google login (public, not a secret)
set_env GOOGLE_CLIENT_ID "$NEXT_PUBLIC_GOOGLE_CLIENT_ID"

# --- Build and start -----------------------------------------------------------
if [ "${ALMOVA_SKIP_BUILD:-0}" != 1 ]; then
    say "Construindo as imagens (a primeira vez leva de 10 a 20 minutos)"
    docker compose build
fi

if ! grep -q '^JWT_PRIVATE_KEY=.' homolog.env; then
    say "Gerando as chaves de login"
    keys=$(docker compose run --rm --no-deps -T --entrypoint python3 web manage.py generate-jwt-keys)
    set_env JWT_PRIVATE_KEY "$(sed -n 's/^JWT_PRIVATE_KEY=//p' <<<"$keys")"
    set_env JWT_PUBLIC_KEY "$(sed -n 's/^JWT_PUBLIC_KEY=//p' <<<"$keys")"
    grep -q '^JWT_PRIVATE_KEY=.' homolog.env || fail "não consegui gerar as chaves de login"
fi

say "Subindo o ALMOVA"
docker compose --profile https up -d

say "Esperando o servidor ficar pronto"
for _ in $(seq 1 90); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q web)" 2>/dev/null)" = healthy ] && break
    sleep 5
done
[ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q web)")" = healthy ] \
    || fail "o servidor não ficou pronto: docker compose logs web"

docker compose exec -T web python3 manage.py setup-powersync-storage
docker compose restart powersync >/dev/null
if [ ! -f .dados-base ]; then
    say "Carregando os dados de base"
    # wger's load-fixtures also creates an admin with a known password: not that one
    docker compose exec -T web python3 manage.py loaddata languages groups licenses \
        setting_repetition_units setting_weight_units gym gym_config \
        equipment muscles categories exercise-base-data translations
    say "Atualizando os exercícios do wger.de (alguns minutos)"
    docker compose exec -T web python3 manage.py sync-exercises \
        || echo "Aviso: wger.de não respondeu, os exercícios ficam os da instalação"
    say "Carregando alimentos (TACO) e nomes dos exercícios em português"
    docker compose exec -T web python3 manage.py import-taco-products \
        || echo "Aviso: a tabela TACO não baixou, rode de novo: docker compose exec web python3 manage.py import-taco-products"
    docker compose exec -T web python3 manage.py import-exercise-names-pt
    touch .dados-base
fi

say "Pronto"
cat <<EOF

  O ALMOVA está no ar em: $url
  (o certificado HTTPS sai em alguns segundos na primeira vez)

  O antivírus baixa a base de vírus na primeira vez: até lá, envios de
  arquivos são recusados por alguns minutos.

  Próximos passos (README.md desta pasta):
  - backup automático: chave age e agendamento no cron (seção 3)
  - e-mail: ENABLE_EMAIL e os dados do serviço de envio em homolog.env,
    depois: sudo docker compose up -d
EOF
if [ -z "$NEXT_PUBLIC_GOOGLE_CLIENT_ID" ]; then
    printf '\n\033[1;33m  Atenção: sem o ID do cliente Google ninguém entra pelo site.\n  Crie o ID (guia, passo 4) e rode o script de novo.\033[0m\n'
fi

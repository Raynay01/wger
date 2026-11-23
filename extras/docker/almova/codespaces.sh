#!/bin/bash
# ALMOVA for testing in GitHub Codespaces, free and without a server: the
# stack runs in the codespace and GitHub serves it over HTTPS at
# https://<codespace>-8080.app.github.dev. Test data only: the codespace
# runs outside Brazil and stops when idle (it comes back when reopened).
#
#   bash extras/docker/almova/codespaces.sh
#
# Asks for the Google client ID of the login (guide, step 4) and runs
# instalar.sh without the Caddy of its own.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

say() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

if [ -z "${CODESPACE_NAME:-}" ]; then
    echo "Rode este script dentro de um GitHub Codespace (num servidor, use instalar.sh)." >&2
    exit 1
fi

domain="${CODESPACE_NAME}-8080.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
url="https://$domain"

if ! grep -q '^NEXT_PUBLIC_GOOGLE_CLIENT_ID=.' .env 2>/dev/null; then
    cat <<EOF

  O endereço deste ALMOVA de teste é:

    $url

  No Google (guia HOMOLOGACAO-GRATUITA.md, passo 4), em
  "Origens JavaScript autorizadas", adicione exatamente esse endereço.
  Depois cole aqui o ID do cliente.
EOF
fi

as_root() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

as_root env ALMOVA_DOMAIN="$domain" ALMOVA_SKIP_SYSTEM=1 ALMOVA_NO_HTTPS=1 \
    ${NEXT_PUBLIC_GOOGLE_CLIENT_ID:+NEXT_PUBLIC_GOOGLE_CLIENT_ID="$NEXT_PUBLIC_GOOGLE_CLIENT_ID"} \
    bash instalar.sh

say "Abrindo o endereço para o celular e o Google"
# Private ports only open for the owner, logged in to GitHub
if ! gh codespace ports visibility 8080:public -c "$CODESPACE_NAME" >/dev/null 2>&1; then
    cat <<EOF
  Não consegui tornar a porta pública sozinho. Na aba PORTAS (embaixo), clique
  com o botão direito na porta 8080 > Visibilidade da porta > Pública.
EOF
fi

cat <<EOF

  Abra no celular: $url

  O Codespace desliga sozinho quando fica sem uso. Para voltar, abra o
  Codespace de novo no GitHub: o ALMOVA sobe sozinho com os mesmos dados.
EOF

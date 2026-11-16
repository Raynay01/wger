# ALMOVA: primeira fase de segurança (15 e 16/11/2026)

Cada conjunto de mudanças tem a sua branch (`almova/seguranca-01` a `10`),
juntada depois em `claude/happy-goldberg-8nupoc`. Nenhuma migração de banco,
nenhum dado de paciente alterado.

## Feito

| # | O que | Como foi verificado |
|---|---|---|
| 1 | Rascunhos de treinos e dietas não vão mais para o celular do paciente (`extras/powersync/sync_rules.yaml`) | Teste roda as consultas da regra; falha com a regra original do wger. Compilador oficial do PowerSync sem erros. Conferido em PostgreSQL 16 e no serviço PowerSync 1.28.3 da homologação |
| 2 | CORS só para origens listadas (nenhuma por padrão); `DJANGO_ALLOWED_HOSTS` configurável | Teste carrega as configurações de produção; na homologação, site não autorizado sem CORS e Host falso recusado (400) |
| 3 | CSP com nonce por página no site e HSTS em produção; no Django, `SecurityMiddleware` (antes ausente), CSP básica aplicada e a completa em modo de observação | Teste completo no navegador falha com qualquer violação de CSP: passa em desenvolvimento, no build de produção e na homologação |
| 4 | Verificação em duas etapas obrigatória para profissionais (aplicativo autenticador, QR code, códigos de recuperação, código no login, também depois do Google) | 10 testes do servidor (sessão, JWT, chave de API e OIDC recusados) e o fluxo completo no navegador |
| 5 | Antivírus (ClamAV) em todos os envios de arquivos; recusa se o antivírus estiver fora do ar | Testes com um ClamAV simulado e com o ClamAV 1.5.4 de verdade (arquivo de teste EICAR) |
| 6 | Backups criptografados (age) do banco e dos anexos, restauração só em banco novo, teste de restauração | 126 tabelas idênticas (PostgreSQL 16) e 137 tabelas / 24.212 linhas idênticas (PostgreSQL 18 da homologação) |
| 7 | Versões fixadas por versão e digest; imagem do servidor com exatamente as versões do `uv.lock`, conferidas por hash; pilha de homologação em `extras/docker/almova` | Os 37 passos do teste no navegador contra a homologação (PostgreSQL 18.7, configurações de produção) |
| 8 | Fotos do chat sem metadados (localização GPS, câmera); teste que impede qualquer lista da API de mostrar dados de outra pessoa | 173 tentativas de ler ou alterar registros de outras pessoas sem sucesso; o novo teste falha se uma lista vazar |
| 9 | Política de conteúdo do Django aplicada por completo: scripts embutidos dos modelos de página com nonce, sem `onclick`, Swagger e Redoc ajustados, reCAPTCHA sem script embutido (`almova/seguranca-09-csp-django`) | Teste que varre todos os modelos de página (falha com um script sem nonce ou um `onclick`); navegador percorreu 37 páginas, a API navegável, o Swagger e o Redoc com as configurações de produção, sem nenhum bloqueio além do logotipo externo do Redoc |
| 10 | Login dos profissionais dura no máximo 30 dias a partir da entrada, mesmo com renovação do token (`CARE_PROFESSIONAL_LOGIN_DAYS`); pacientes continuam com 120 dias (`almova/seguranca-10-login-profissional`) | Testes: renovação no dia 29 funciona, no dia 31 é recusada e o token antigo também; paciente segue entrando; sessão do navegador sai; desligado com 0 |

Problemas encontrados e corrigidos no caminho:

- Página protegida sem login dava erro 500.
- A imagem do servidor não criava a pasta dos anexos privados: em produção,
  todo envio de foto ou vídeo no chat falharia.
- O Dockerfile instalava o Node por um script remoto que falhava em silêncio.

## Depende de decisão sua

1. **Fotos de progresso (galeria do wger)** ficam na pasta pública de mídia,
   protegidas só pelo nome aleatório do arquivo. O certo é passá-las para o
   armazenamento privado, como os anexos do chat, mas isso muda onde os arquivos
   existentes ficam (precisa da sua aprovação). O site do ALMOVA ainda não usa a
   galeria; o app do celular do wger usa.
2. **Admin do Django desligado**: o `admin.py` registra os modelos, mas o admin
   não está instalado, então a verificação do registro no conselho e a exclusão de
   conta pedida pelo paciente não têm tela. Opções: ligar o admin só na rede
   interna e com verificação em duas etapas, ou fazer essas telas na área
   profissional/administrativa do site.
3. **Consentimento para dados de saúde (LGPD, art. 11)**: o aceite do convite
   registra o consentimento do acompanhamento, mas não há registro separado e
   destacado para o tratamento de dados de saúde nem do aceite dos termos. O texto
   depende dos documentos de LGPD (advogado). Quando houver o texto, a tela e o
   registro são simples de fazer.
4. **Vídeos do chat** podem ter a localização gravada pelo celular. Remover
   exige o ffmpeg no servidor (troca de dependência).
5. **Registro de acesso**: hoje fica registrado quando o profissional lê dados
   compartilhados por outra área; leituras na própria área (diário, treinos) não.

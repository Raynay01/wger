# ALMOVA: roteiro para colocar a homologação no ar

A homologação é uma cópia completa do ALMOVA num servidor de verdade, com
endereço público e HTTPS, para testar o site e o app no celular antes de abrir
para pacientes. O que já está pronto do lado técnico: a pilha Docker
(`extras/docker/almova`), o HTTPS automático (perfil `https`), os backups
criptografados e o app Android, que só precisa do endereço para ser gerado.

## 1. O que você contrata (uma vez)

| Item | O que pedir | Para quê |
|---|---|---|
| Domínio | `almova.com.br` no registro.br (confira antes a marca no INPI) | endereço do site e do app |
| Servidor (VPS) | Ubuntu 24.04, 4 vCPU, 8 GB de RAM, 80 GB de SSD, **de preferência no Brasil** | roda tudo: banco, servidor, site, sincronização, antivírus |
| Envio de e-mail | Amazon SES (região São Paulo), Brevo ou Resend | convites, recuperação de senha, avisos |
| Armazenamento para backup | um "bucket" S3 compatível, em outra empresa ou região | cópia dos backups fora do servidor |
| Firebase (opcional nesta fase) | projeto no console do Firebase | avisos no celular |

Servidor no Brasil: os dados de saúde não saem do país, o que evita as regras
de transferência internacional da LGPD (art. 33). Confirme com o advogado.

## 2. Apontar o domínio

No painel do domínio, crie um registro do tipo **A**:

| Nome | Tipo | Valor |
|---|---|---|
| `homolog` | A | o IP do servidor |

O endereço da homologação fica `https://homolog.almova.com.br`. Para o e-mail,
o serviço escolhido pede alguns registros a mais (SPF, DKIM); copie os que ele
mostrar.

## 3. Preparar o servidor (uma vez, por SSH)

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git ufw
sudo ufw allow OpenSSH && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
git clone https://github.com/Raynay01/wger.git almova
cd almova/extras/docker/almova
cp homolog.env.example homolog.env
```

Preencha o `homolog.env` (os segredos novos, gerados como no `README.md` desta
pasta) e troque:

```bash
SITE_URL=https://homolog.almova.com.br
WEB_APP_URL=https://homolog.almova.com.br
CSRF_TRUSTED_ORIGINS=https://homolog.almova.com.br
DJANGO_ALLOWED_HOSTS=homolog.almova.com.br,localhost,web
X_FORWARDED_PROTO_HEADER_SET=True
KINUTRI_DEV_LOGIN=0
# E-mail: os dados que o serviço de envio fornecer
ENABLE_EMAIL=True
EMAIL_HOST=...
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
FROM_EMAIL=ALMOVA <nao-responda@almova.com.br>
```

E crie o arquivo `.env` na mesma pasta:

```bash
ALMOVA_DOMAIN=homolog.almova.com.br
ACME_EMAIL=seu-email@almova.com.br
ALMOVA_HTTP_PORT=127.0.0.1:8080
```

## 4. Subir

```bash
docker compose build
docker compose --profile https up -d
docker compose exec web python3 manage.py setup-powersync-storage
docker compose restart powersync
docker compose exec web python3 manage.py import-taco-products
docker compose exec web python3 manage.py import-exercise-names-pt
```

Na primeira vez o Caddy pede o certificado (alguns segundos). Teste:
`https://homolog.almova.com.br` abre o site com o cadeado.

## 5. Backup automático

Siga `extras/backup/README.md` para criar a chave (a parte privada fica com
você, fora do servidor) e agende no servidor:

```bash
crontab -e
# todo dia às 3h
0 3 * * * cd ~/almova/extras/docker/almova && docker compose --profile backup run --rm backup
```

Depois copie a pasta de backups para o armazenamento externo (o serviço
escolhido fornece o comando, por exemplo `rclone`). Faça um teste de
restauração (seção 4 do `README.md` da pilha) antes de pôr pacientes.

## 6. App no celular

Com o endereço no ar, eu gero o APK apontando para ele:

```bash
flutter build apk --release --dart-define=ALMOVA_SERVER=https://homolog.almova.com.br
```

Para instalar num Android de teste: copie o APK para o celular e permita
"instalar apps desconhecidos" para o gerenciador de arquivos. Roteiro de teste
no celular:

1. Criar conta e entrar.
2. Profissional convida pelo site; paciente aceita no app.
3. Conversa: texto, foto e vídeo nos dois sentidos.
4. Agenda: profissional marca, paciente vê e cancela.
5. Fisioterapia: marcar exercício como feito e registrar dor (o alerta chega
   ao fisioterapeuta).
6. Treino e dieta prescritos aparecem no app, também sem internet.
7. Foto de progresso na galeria.

## 7. Quem faz o quê

| Passo | Você | Eu |
|---|---|---|
| Domínio, servidor, e-mail, armazenamento, Firebase | contratar e me passar os dados (sem senhas no chat) | dizer exatamente o que pedir |
| Preparar e subir o servidor | rodar os comandos acima (ou me dar acesso) | ajustar o que falhar |
| APK de teste | instalar no celular e testar | gerar o APK e corrigir o que aparecer |
| Antes dos pacientes | documentos de LGPD com o advogado | telas de consentimento e termos |

Conferido em 16/11/2026 nesta máquina: a pilha com o perfil `https` (certificado
local de teste no lugar do Let's Encrypt) redirecionou HTTP para HTTPS, serviu o
site, a API e o login do app por HTTP/2, o servidor montou os endereços com
`https://`, e os registros de acesso não guardaram o token passado num endereço.

# Backups criptografados do ALMOVA

`backup.sh` copia o banco (PostgreSQL, `pg_dump`) e as pastas de arquivos (fotos,
vídeos e anexos do chat) já criptografados com [age](https://age-encryption.org).
O arquivo sem criptografia nunca é gravado em disco. `restore.sh` restaura em um
banco **novo**, nunca por cima de um existente. `test-restore.sh` faz o ciclo
inteiro e compara tabela por tabela.

## 1. Chaves (uma vez)

```bash
age-keygen -o almova-backup.key
```

- A linha `Public key: age1...` vai para o servidor, em `BACKUP_AGE_RECIPIENTS`.
- O arquivo `almova-backup.key` (chave privada) **não fica no servidor**. Guarde em
  dois lugares seguros e separados (por exemplo, o gerenciador de senhas da
  empresa e um pendrive em cofre). Sem ela, nenhum backup pode ser aberto; com
  ela, todos podem. É possível ter mais de uma pessoa com chave: liste várias
  chaves públicas em `BACKUP_AGE_RECIPIENTS`, separadas por espaço.

## 2. Backup diário

Variáveis: `BACKUP_AGE_RECIPIENTS`, `BACKUP_DIR`, `BACKUP_KEEP_DAYS` (padrão 30),
`BACKUP_MEDIA_DIRS` (a pasta de mídia e a `DJANGO_PRIVATE_MEDIA_ROOT`) e as do
PostgreSQL (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`).

Exemplo de agendamento (todo dia às 3h10):

```cron
10 3 * * * /opt/almova/extras/backup/backup.sh >> /var/log/almova-backup.log 2>&1
```

Cada execução gera `almova-<data>.db.age`, `almova-<data>.media.tar.gz.age` e
`almova-<data>.sha256` (somas para conferir a integridade). Copie a pasta para
fora do servidor (armazenamento de objetos em outra região ou outro provedor):
os arquivos já estão criptografados, então o destino não vê os dados.

## 3. Restaurar

```bash
BACKUP_AGE_IDENTITY=almova-backup.key RESTORE_MEDIA_TO=/srv/restauracao/media \
  extras/backup/restore.sh /srv/backups almova-20261115T031000Z almova_restaurado
```

Confere as somas, cria o banco `almova_restaurado` (recusa se já existir) e
extrai os arquivos numa pasta vazia. Depois, aponte o servidor de homologação
para esse banco e confira antes de qualquer troca em produção.

## 4. Teste de restauração (mensal, e antes de cada mudança de versão)

```bash
BACKUP_AGE_IDENTITY=almova-backup.key RESTORE_TEST_DB=almova_teste_restauracao \
  extras/backup/test-restore.sh
```

Faz um backup, restaura num banco temporário, compara todas as tabelas linha por
linha e todos os arquivos, confere que outra chave não abre o backup e que um
arquivo corrompido é recusado. O banco temporário é apagado no fim; o banco de
origem não é alterado.

Resultado em 15/11/2026 (PostgreSQL 16, banco de homologação com todas as
migrações): 126 tabelas idênticas, anexo do chat idêntico, chave errada e arquivo
corrompido recusados.

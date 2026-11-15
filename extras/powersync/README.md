# Regras de sincronização do ALMOVA (PowerSync)

`sync_rules.yaml` substitui o arquivo `services/config-powersync/sync_rules.yaml`
do repositório docker do wger. Ele é igual ao original, com uma diferença:
rascunhos de treinos e planos alimentares feitos por um profissional não vão
para o celular do paciente. Só sincronizam o que o próprio paciente criou
(`author_id IS NULL`) e o que já saiu de rascunho (publicado, substituído ou
arquivado), a mesma regra que a API aplica (`visible_prescriptions_q`).

## Instalar

Copie o arquivo para a configuração do serviço PowerSync e reinicie o serviço
(o PowerSync não relê o arquivo sozinho). A mudança faz o serviço reprocessar
os dados: os rascunhos que já estavam em celulares somem na próxima
sincronização.

## Verificar

- `DJANGO_SETTINGS_MODULE=settings.ci uv run ./manage.py test wger.care.tests.test_sync_rules`
  roda as consultas do arquivo no banco de testes e confere que nenhum
  rascunho aparece.
- O compilador oficial (`@powersync/service-sync-rules`, precisa de Node 24)
  valida a sintaxe:

  ```js
  import { readFileSync } from 'node:fs';
  import { validateSyncConfig } from '@powersync/service-sync-rules';
  console.log(validateSyncConfig(readFileSync('sync_rules.yaml', 'utf8'), {
    defaultSchema: 'public',
    throwOnError: false,
  }));
  ```

Ao trazer uma versão nova do arquivo do wger, reaplique os filtros
`(author_id IS NULL OR status != 'draft')` e rode os dois passos acima.

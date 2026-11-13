# RP PERFORMANCE: estado da implementação

> Complementa `PLANO-ARQUITETURA.md`. Atualizado em 13/11/2026 (versão da API `2.8.0-dev.6`).

## 1. O que já funciona no backend

| Área | Situação | Onde |
|---|---|---|
| Organizações (profissional independente, clínica, equipe) e membros com papéis | Pronto | `wger/care` |
| Registro no conselho (CREF, CREFITO, CRN) com verificação pelo admin | Pronto (verificação manual no admin do Django) | `wger/care` |
| Convite de paciente por e-mail ou link, aceite com consentimento registrado | Pronto. O e-mail só sai quando o profissional clica em "Enviar convite por e-mail" (reenvio a cada 10 min no máximo); em produção depende do servidor de e-mail (SMTP) configurado | `wger/care` |
| Módulos visíveis conforme os profissionais do paciente (Testes 1 a 4) | Pronto | `GET /api/v2/care/modules/` |
| Tela Meu Dia (treino, refeições, totais, água, fisioterapia) | Pronto | `GET /api/v2/care/my-day/` |
| Compartilhamento por escopo, revogável, com log de acesso (Testes 5 e 8) | Pronto | `wger/care` |
| Observações multidisciplinares | Pronto | `wger/care` |
| Autoria e versões de dietas, treinos e protocolos (Testes 6, 7 e 9) | Pronto, também na sincronização offline (PowerSync) | `wger/care/prescription.py` |
| Nutrição: orientações por refeição e item, substituições, adesão por refeição, hidratação, meta de água | Pronto | `wger/nutrition` |
| Treino: RPE alvo, cadência, amplitude; RPE realizado | Pronto (campos; o motor de progressão continua usando RIR) | `wger/manager` |
| Fisioterapia: protocolos, exercícios com dosagem e vídeo, dor 0 a 10 por momento, alertas, exercícios realizados, avaliações funcionais | Pronto | `wger/physio` |

Testes: 59 novos testes em `wger/care/tests` e `wger/physio/tests`. A suíte completa (2.569 testes) passa, exceto `test_sync_exercises`, que depende de acesso a `wger.de` (bloqueado nesta sessão; falha igual sem as mudanças).

## 1.1 App web Kinutri (`rp-web/`)

Nome escolhido: **Kinutri** (cinesioterapia/movimento + nutrição), subtítulo "Treino, reabilitação e nutrição". Na busca feita em 13/11/2026 não apareceu app, marca ou site com esse nome. Antes de registrar, confirme no INPI (classes 9, 42 e 44) e a disponibilidade dos domínios. O nome fica só em `rp-web/src/lib/brand.ts`.

| Área | Telas |
|---|---|
| Entrada | Página inicial, login com Google (Gmail), escolha entre área do paciente e profissional |
| Paciente | Meu Dia (treino, refeições com "segui / segui parcialmente / não segui", metas e restante, água, fisioterapia com vídeo e "feito", dor 0 a 10), visão Treino + alimentação / Só treino / Só alimentação, profissionais e convites, compartilhamento por escopo, evolução (avaliações, dor, água) |
| Profissional | Painel com pacientes, convites e alertas; configurações (organização e CREF/CREFITO/CRN); convite por e-mail ou link; ficha do paciente (prescrições e versões, diário alimentar, planejado x realizado no treino, dor, avaliações funcionais, dados compartilhados, observações) |
| Construtores | Dieta (refeições, busca de alimentos, gramas, orientações, substituições, totais, distribuição de macros, metas), treino (dias do ciclo, exercícios da biblioteca, séries, repetições, carga, descanso, RIR, RPE, cadência, amplitude), protocolo (exercícios com dosagem, local e vídeo, momentos de dor e limites de alerta), publicar, nova versão, arquivar |

O teste ponta a ponta (`npm run test:e2e`) percorre esses fluxos no navegador com três usuários e passa nos 15 passos.

Para o login com Google funcionar em produção, crie o ID do cliente OAuth no Google Cloud e configure `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` no Django e `NEXT_PUBLIC_GOOGLE_CLIENT_ID` no app web (passo a passo em `rp-web/README.md`).

## 2. Como os critérios de aceitação estão cobertos

| Critério | Teste automatizado |
|---|---|
| 1. Só musculação | `care/tests/test_acceptance.py::ModulesTestCase::test_training_only` |
| 2. Só nutrição | `test_nutrition_only` e `care/tests/test_my_day.py::test_nutrition_only_has_no_training` |
| 3. Fisioterapia | `physio/tests/test_physio.py` (protocolo, vídeo, dor, evolução funcional) |
| 4. Treino + nutrição no Meu Dia | `test_training_and_nutrition` e `test_my_day.py::test_training_and_nutrition_together` |
| 5. Três profissionais com compartilhamento | `SharingTestCase`, `test_pain_shared_with_trainer` |
| 6. Nutricionista não altera treino | `PrescriptionTestCase::test_nutritionist_cannot_change_training` |
| 7. Personal não altera dieta | `PrescriptionTestCase::test_trainer_cannot_change_diet` |
| 8. Só dados autorizados | `SharingTestCase` (padrão vazio, revogação imediata, log de acesso, notas) |
| 9. Histórico de versões | `test_new_version_keeps_history`, `test_routine_new_version_copies_days`, `test_new_version_copies_exercises` |
| 10. Dados reais, segurança, persistência | Parcial: testes de API e permissões; faltam testes em PostgreSQL e de carga |

## 3. Fluxo pela API (exemplo com um nutricionista)

1. Criar a organização: `POST /api/v2/organization/` `{"name": "Clínica RP", "kind": "solo"}` (quem cria vira proprietário).
2. Registrar o CRN: `POST /api/v2/professional-registration/` `{"discipline": "nutrition", "number": "12345", "region": "SP"}`.
3. Convidar o paciente: `POST /api/v2/care-relationship/` `{"organization": "<id>", "discipline": "nutrition", "invited_email": "paciente@exemplo.com"}`.
4. Paciente aceita: `POST /api/v2/care-relationship/<id>/accept/` `{"accept_terms": true}` (ou com `"token"` do link).
5. Criar a dieta como rascunho: `POST /api/v2/nutritionplan/` `{"description": "Hipertrofia", "care_relationship": "<id>", "goal_energy": 2500, "goal_water_ml": 2500}`.
6. Montar refeições e itens: `POST /api/v2/meal/`, `POST /api/v2/mealitem/`, `POST /api/v2/substitution-option/`.
7. Publicar: `POST /api/v2/nutritionplan/<id>/publish/`. Para alterar depois: `POST .../new-version/`, editar e publicar de novo.
8. Paciente usa o app: `GET /api/v2/care/my-day/`, registra o diário (`/api/v2/nutritiondiary/`), a adesão (`/api/v2/meal-adherence/`) e a água (`/api/v2/water-log/`).
9. Nutricionista acompanha: `GET /api/v2/care-relationship/<id>/nutrition-diary/?date=2026-11-13` e, se autorizado, `GET .../shared/`.

O mesmo vale para treino (`/api/v2/routine/`, vínculo `training`) e fisioterapia (`/api/v2/physio-protocol/`, vínculo `physio`). Esquema completo em `/api/v2/schema/ui`.

## 4. O que falta para o produto completo

### Clientes (maior bloco de trabalho)
- **App do paciente (Flutter)**: o app do wger não está nesta sessão. É preciso fazer um fork de `wger-project/flutter` na sua conta e adicioná-lo aqui. Telas a criar: Meu Dia, convites e consentimento, autorizações de compartilhamento, adesão e água, fisioterapia (protocolo, dor), identidade visual RP.
- **Painel profissional e site comercial**: feitos em `rp-web/` (Next.js), com login do Django via Google. O `Raynay01/SaaS-Boilerplate` foi clonado, mas a sessão não teve permissão de escrita nele; o código pode ser movido para lá depois.

### Backend
- Regras de sincronização do PowerSync (repositório docker) para as colunas e tabelas novas; até lá, o app offline não recebe autoria, versões, orientações nem as tabelas novas.
- Envio do convite pelo WhatsApp (Cloud API, com modelos aprovados pela Meta). O envio por e-mail já existe.
- Bases de alimentos TACO (e TBCA, após autorização), nutrientes anuláveis e alimentos próprios da organização.
- Anamnese e avaliação nutricional, antropometria, cálculo de necessidades energéticas.
- Periodização (macro e mesociclos), vídeos de execução enviados pelo aluno.
- Agenda e calendário integrado, chat com mídia.
- RP Intelligence (Fase 5), assinaturas e pagamentos (Fase 6), exportação e exclusão de dados (LGPD), Row Level Security.
- Traduções em português: as novas mensagens estão nos arquivos `.po`, traduzidas via Weblate. Em um fork próprio, as traduções `pt_BR` podem ser feitas direto no arquivo.

### Infraestrutura e legal
- Hospedagem, domínio, chaves (Anthropic, Meta, gateway de pagamento) e as decisões da seção 13 do plano.
- Documentos LGPD (termos, política, contrato de operador, RIPD) antes de atender pacientes reais.

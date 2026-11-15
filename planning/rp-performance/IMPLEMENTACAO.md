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
| Banco de alimentos TACO: 590 alimentos brasileiros em português, com categoria, fibra e sódio, fonte citada | Pronto: `manage.py import-taco-products` (rodar uma vez em cada servidor; rodar de novo atualiza). Ficam de fora os 7 itens sem valores na própria TACO (6 laticínios e a aguardente). Óleos recebem proteína e carboidrato 0 por balanço de massa (99,5 g ou mais de gordura em 100 g). Inclui 688 medidas caseiras (colher de sopa, concha, xícara...) com os gramas da POF/IBGE, que o nutricionista escolhe no construtor de dietas | `wger/nutrition/extract_info/taco.py` |
| Alimentos cadastrados por nutricionistas (novos ou correções de alimentos existentes), compartilhados com todos e marcados com a organização como autora | Pronto: tela Alimentos na área profissional. A correção copia valores e medidas do original, que não muda; edição e exclusão só enquanto o alimento não estiver em dietas publicadas ou diários | `wger/nutrition/professional_foods.py` |
| Agenda e calendário integrado: consultas, sessões e avaliações marcadas pelo profissional; calendário mensal do paciente com treino ou descanso, plano alimentar, fisioterapia e consultas, com filtros por área | Pronto. O app web grava o fuso do navegador no perfil, e os dias contam no fuso do paciente | `wger/care/agenda.py` |
| Chat entre paciente e cada profissional, com fotos e vídeos (ex.: execução de exercício), aviso de mensagens não lidas no menu e confirmação de leitura | Pronto. Os anexos ficam fora da pasta pública de mídia e só são entregues às duas pessoas do acompanhamento; vídeos tocam com avanço/retrocesso (requisições por partes). Fotos até 20 MB, vídeos até 50 MB. A conversa atualiza sozinha a cada 10 s. Depois do fim do acompanhamento, os dois continuam lendo o histórico, mas não escrevem. Em produção, `DJANGO_PRIVATE_MEDIA_ROOT` precisa de um volume persistente no docker | `wger/care/messages.py` |
| Vídeos de execução: o aluno escolhe o exercício do treino ao mandar um vídeo na conversa; o profissional tem a tela Vídeos com os vídeos dos pacientes a revisar (do mais antigo para o mais novo) e marca como revisado, com um comentário opcional que vai para a conversa | Pronto. Vale para todas as áreas (o exercício só no vídeo para o personal); o menu mostra quantos vídeos faltam revisar; o paciente vê "aguardando revisão" ou "vídeo revisado". Vídeos de acompanhamentos encerrados saem da fila | `wger/care/messages.py` |
| Periodização do treino: macrociclo com objetivo e fases (mesociclos) com foco, semanas, treino da fase, intensidade e volume; linha do tempo para o personal e para o aluno, fase e semana no calendário | Pronto. Versões e publicação iguais às do treino; a fase mostra sempre a versão publicada atual do treino ligado. Gráfico de planejado x realizado por semana de cada fase (sessões, séries e tonelagem, com RIR e RPE médios), para o personal e na Evolução do aluno. Metas de séries por semana por músculo em cada fase, comparadas com o treino ligado e com o realizado em cada semana | `wger/manager/models/periodization.py` |
| Anamnese e avaliação nutricional: anamnese datada (objetivo, histórico, medicamentos, alergias, preferências, hábitos, sono, água, atividade física); antropometria (peso, altura, cintura, quadril, % de gordura medido ou calculado por dobras cutâneas: Jackson-Pollock 3 ou 7 dobras, Durnin-Womersley) com IMC e classificação, relação cintura-quadril e massa magra; taxa metabólica basal (Mifflin-St Jeor, Harris-Benedict revisada ou Katch-McArdle), gasto total pelo fator de atividade e meta diária com o ajuste do objetivo, dividida em proteínas (g/kg), gorduras (% das calorias) e carboidratos (o restante); botão para criar o plano alimentar já com essas metas | Pronto. O paciente vê a última avaliação e a evolução do peso em Evolução. Sexo e idade ficam gravados na avaliação, para o resultado não mudar se o perfil mudar. Entra na exportação e bloqueia a exclusão da conta como as avaliações funcionais. Se o paciente compartilhar "Peso e medidas", o personal e o fisioterapeuta veem as medidas (não as anotações, a meta nem os macros) | `wger/nutrition/models/assessment.py` |
| Constância (gamificação, parte 1): calendário das últimas semanas por área (treino feito, previsto sem registro ou descanso; refeições registradas; meta de água; fisioterapia), resumo da semana e sequência de dias com registro | Pronto, na área do paciente. Conta só o registro, nunca a quantidade (nenhum dia vale mais por comer menos ou pesar menos); dias de descanso do treino e o dia de hoje não quebram a sequência; registrar "não segui" também conta | `wger/care/consistency.py` |
| Conquistas (gamificação, parte 2): conquistas de treino do wger em português, com as conquistadas e as próximas; regras de segurança | Pronto. Nenhuma conquista por comer menos, jejum ou perda de peso; conquistas de treino pausam por 14 dias após dor no limite de alerta do protocolo de fisioterapia; a sequência de treinos não quebra nos dias de descanso do treino; o paciente desativa na tela Constância e qualquer profissional do acompanhamento desativa na ficha do paciente | `wger/care/gamification.py` |
| LGPD: exportar todos os dados (JSON) e pedir a exclusão da conta | Pronto. O pedido encerra os acompanhamentos na hora; a exclusão é feita pelo administrador no admin do Django, que bloqueia enquanto houver registros clínicos de profissionais (avaliações, observações) | `wger/care/export.py`, `wger/care/deletion.py` |

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
- TBCA (após autorização) e nutrientes anuláveis.
- Aviso de mensagem nova fora do app (push no celular, e-mail opcional) e chat em tempo real (hoje a conversa atualiza a cada 10 s).
- Volume `private-media` no docker para os anexos do chat.
- RP Intelligence (Fase 5), assinaturas e pagamentos (Fase 6), Row Level Security.
- Política de guarda de prontuário: decidir com um advogado o que fazer com avaliações e observações clínicas quando o paciente pede a exclusão (hoje a exclusão fica bloqueada até essa decisão).
- Traduções em português: as novas mensagens estão no arquivo `pt`. O arquivo `pt_BR` (`wger/locale/pt_BR`) só traz o que muda no Brasil (hoje, os nomes e descrições das conquistas); o resto vem do `pt`. O app web pede `pt-BR`.

### Infraestrutura e legal
- Hospedagem, domínio, chaves (Anthropic, Meta, gateway de pagamento) e as decisões da seção 13 do plano.
- Documentos LGPD (termos, política, contrato de operador, RIPD) antes de atender pacientes reais.

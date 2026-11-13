# RP PERFORMANCE: arquitetura, fluxos, banco de dados, telas, custos e planejamento

> Treinamento, Reabilitação e Nutrição.
> Documento de planejamento (pré-programação). Versão 0.1, 13/11/2026.
> Base técnica: este repositório (fork do **wger**, Django + DRF, AGPL-3.0).

---

## 0. Resumo executivo

| Tema | Recomendação |
|---|---|
| Base do produto | Evoluir o fork do **wger** (backend Django/DRF + app Flutter + front React) em vez de começar do zero. Economiza de 35 a 45% das fases 2 e 3. |
| Licença | wger é **AGPL-3.0**: o SaaS pode ser comercializado, mas o código-fonte modificado precisa ser oferecido aos usuários da plataforma. Marca, dados, conteúdo, vídeos e base de clientes continuam seus. **Decisão necessária antes da Fase 1** (seção 13). |
| Arquitetura | Monólito modular (Django), PostgreSQL, Redis + Celery, armazenamento privado S3 compatível, PowerSync para uso offline no app. Sem microsserviços. |
| Multi-tenant | Banco compartilhado com `organization_id` em todas as tabelas clínicas, filtro obrigatório na camada de acesso e, na Fase 6, Row Level Security do PostgreSQL como defesa adicional. |
| Paciente | App **Flutter** (iOS, Android, web), reaproveitando o app do wger. |
| Profissionais e admin | Painel web **React** (reaproveitando o front do wger), responsivo, com perfis por especialidade. |
| Integração entre profissionais | Vínculo de cuidado (`CareRelationship`) + **autorizações por escopo** concedidas pelo paciente (`AccessGrant`). Cada profissional só escreve no próprio módulo. |
| Histórico | Prescrições (dieta, treino, protocolo de fisioterapia) são **versionadas e imutáveis após publicação**. Execução (diário, logs de treino, dor) aponta para a versão vigente. |
| IA | RP Intelligence no backend via API da Anthropic (Claude). Fatos calculados por SQL, texto gerado pela IA, sempre separado em "fatos / interpretações / sugestões", sem escrever em planos. |
| Primeiro marco útil | Fim da Fase 1 + parte da 3 (6 a 10 semanas): você usando o sistema com seus próprios pacientes, em um único tenant. |

---

## 1. Diagnóstico: o que o wger já entrega e o que falta

Levantamento feito no código atual (`wger/<app>/models`).

### 1.1 Já existe (reaproveitável)

| Requisito RP | Onde está no wger | Observação |
|---|---|---|
| Biblioteca de exercícios com vídeo, imagens, músculos, equipamentos, variações, histórico de alterações | `exercises` (`Exercise`, `Translation`, `ExerciseVideo`, `ExerciseImage`, `Equipment`, `Muscle`, `simple_history`) | Base pública CC-BY-SA, multilíngue. Falta: exercícios privados por organização, erros comuns, dificuldade, tags de reabilitação. |
| Prescrição de treino com séries, repetições, carga, RIR, descanso, faixas (mín./máx.), tipos (aquecimento, drop-set, isometria, TUT...) | `manager` (`Routine`, `Day`, `Slot`, `SlotEntry`, `*Config`) | Já tem **progressão automática de carga** por iteração com requisitos. Falta: RPE explícito, cadência, tempo de isometria, amplitude, periodização macro/meso/micro. |
| Planejado x realizado no treino | `WorkoutLog` (`weight` x `weight_target`, `repetitions` x `repetitions_target`, `rir` x `rir_target`, `rest` x `rest_target`), `WorkoutSession` | Excelente base para o painel de evolução de cargas. |
| Modelos de treino, duplicação | `Routine.is_template`, `is_public`, cópia de rotinas | Pronto. |
| Plano alimentar por refeições, itens com quantidade e medida caseira | `nutrition` (`NutritionPlan`, `Meal`, `MealItem`, `IngredientWeightUnit`) | Falta: autoria profissional, versão, horários-alvo, orientações, substituições. |
| Metas de calorias e macros | `NutritionPlan.goal_energy/protein/carbohydrates/fat/fiber` | Falta histórico de metas e metas de micronutrientes. |
| Diário alimentar | `LogItem` (com `meal`, `datetime`, `comment`) | Falta: adesão por refeição (integral/parcial/não seguiu), refeições reutilizáveis, favoritos. |
| Banco de alimentos com código de barras, marca, categoria, fonte e licença | `Ingredient` (`code`, `brand`, `category`, `source_name`, `source_url`, `license`), integração **Open Food Facts** e importação **USDA** | Falta: TACO/TBCA, nutrientes adicionais, estado (cru/cozido), alimentos próprios por organização. Atenção: `energy`, `protein`, `carbohydrates` e `fat` são NOT NULL hoje (ver 7.1). |
| Medidas corporais e peso, com gráficos | `measurements` (`Category`, `Measurement`, tipos de métrica e gráfico) | Base boa para antropometria e escalas de dor. |
| Fotos de progresso | `gallery` | Reaproveitar com armazenamento privado. |
| Conquistas | `trophies` | Reaproveitar com regras de segurança (seção 4.12). |
| Academia com treinadores e gestores | `gym` (`Gym`, permissões `gym_trainer`, `manage_gym`, `Contract`) | Embrião de multi-tenant, mas acoplado a "um usuário, uma academia". Será substituído por `tenancy`. |
| Offline e sincronização | PowerSync (`powersync.py` por app) | Essencial para o diário alimentar e para o treino na academia sem sinal. |
| API REST, JWT, schema OpenAPI | `/api/v2/`, SimpleJWT, allauth headless, drf-spectacular | Pronto. |
| Fila de e-mails, Celery | `mailer`, `tasks.py` | Base para notificações. |

### 1.2 Não existe (a construir)

- Organizações (tenants), papéis profissionais, registro em conselho (CREF, CREFITO, CRN).
- Vínculo profissional-paciente, consentimentos e autorizações de compartilhamento.
- Versionamento de prescrições.
- Módulo de fisioterapia (protocolos, dor, avaliações funcionais, questionários padronizados).
- Motor de avaliações e anamneses (formulários configuráveis com pontuação).
- Substituições alimentares, receitas, hidratação, adesão por refeição.
- Tela "Meu Dia", calendário integrado, agenda de consultas.
- Chat com mídia, WhatsApp, notificações push.
- RP Intelligence.
- Assinaturas, pagamentos, white-label, painel administrativo global.
- Auditoria de acesso, exportação e exclusão de dados (LGPD).

---

## 2. Arquitetura técnica

### 2.1 Visão geral

```text
                ┌──────────────────────────┐      ┌───────────────────────────┐
                │  App Paciente (Flutter)  │      │ Painel Profissional/Admin │
                │  iOS · Android · Web     │      │ (React, responsivo)       │
                │  SQLite local (PowerSync)│      └─────────────┬─────────────┘
                └───────┬───────────┬──────┘                    │ HTTPS/JWT
                        │ sync      │ HTTPS/JWT                 │
                ┌───────▼─────┐ ┌───▼─────────────────────────▼────────────┐
                │  PowerSync  │ │  Backend Django + DRF  (monólito modular)│
                │  Service    │ │  apps: tenancy · care · manager · physio │
                └──────┬──────┘ │  nutrition · assessments · agenda ·      │
                       │        │  messaging · intelligence · billing ·    │
                       │        │  audit · branding · exercises · core     │
                       │        └───┬───────────┬───────────┬──────────────┘
                ┌──────▼────────────▼──┐  ┌─────▼─────┐  ┌──▼───────────────────┐
                │ PostgreSQL 16        │  │ Redis     │  │ Celery workers       │
                │ (+ RLS na Fase 6)    │  │ cache/fila│  │ IA · WhatsApp · push │
                └──────────────────────┘  └───────────┘  │ importação alimentos │
                                                         └──────────┬───────────┘
                                                                    │
   Serviços externos: Storage privado S3 (URLs assinadas) · Vídeo com streaming e URL assinada ·
   Anthropic API (RP Intelligence) · WhatsApp Cloud API · FCM/APNs (push) · Gateway de pagamento
```

### 2.2 Escolhas e justificativas

| Camada | Escolha | Por que | Alternativa avaliada |
|---|---|---|---|
| Backend | Django 5 + DRF (wger) | Já tem 60% do domínio de treino e nutrição, admin, migrações, testes, i18n | Supabase: rápido para CRUD, mas regras de autorização entre profissionais, versionamento e IA ficariam espalhadas em RLS + Edge Functions; reescrever todo o domínio |
| Banco | PostgreSQL 16 | Relacional, JSONB para formulários, RLS, extensões (`pg_trgm` para busca de alimentos, `unaccent`) | - |
| App paciente | Flutter (fork do app wger) | Um código para iOS/Android/web, já integrado com a API e PowerSync | React Native: exigiria reescrever o app |
| Painel profissional | React (fork do front wger) | SPA autenticada não precisa de SSR. Componentes de rotinas e nutrição já existem | Next.js: útil só para o site institucional/landing, que pode ser separado |
| Offline | PowerSync | Já usado pelo wger. Diário e treino funcionam sem internet | - |
| Tarefas | Celery + Redis | IA, envio de WhatsApp, importação de bases, relatórios | - |
| Arquivos | S3 compatível privado (AWS S3 sa-east-1 ou Cloudflare R2) | Fotos, documentos, áudios, vídeos de execução, sempre com URL assinada de curta duração | - |
| Vídeo | Cloudflare Stream ou AWS MediaConvert + CloudFront signed URLs | Transcodificação e streaming adaptativo, URLs assinadas | Servir MP4 direto do S3 (aceitável na Fase 2, migrar depois) |
| Busca | PostgreSQL full-text + `pg_trgm` + `unaccent` | Suficiente até centenas de milhares de alimentos | Meilisearch/OpenSearch apenas se a busca ficar lenta |
| Infra | Docker Compose (Fase 1) → contêineres gerenciados (Fase 6) | Começa barato, escala sem reescrever | Kubernetes: desnecessário no início |

### 2.3 Princípios de domínio (valem para todos os módulos)

1. **Prescrição ≠ execução ≠ avaliação ≠ feedback.** Tabelas separadas, nunca reaproveitar uma para a outra.
2. **Toda prescrição tem autor, especialidade, organização, versão e status** (`draft` → `published` → `superseded`/`archived`).
3. **Publicado é imutável.** Editar um plano publicado cria uma nova versão rascunho.
4. **Execução aponta para a versão.** Um registro do diário de março continua apontando para a dieta de março.
5. **Autonomia por módulo.** A permissão de escrita depende da especialidade do autor; um nutricionista nunca altera um treino e vice-versa (Testes 6 e 7).
6. **Nada é compartilhado por padrão.** O paciente concede escopos a profissionais específicos, revogáveis a qualquer momento.
7. **Todo acesso a dado sensível de terceiro gera log de auditoria.**
8. **Valores desconhecidos são nulos, nunca zero.** Vale para nutrientes, medidas e escalas.

---

## 3. Multi-tenant, papéis e permissões

### 3.1 Entidades de organização

- **Organization**: `type` (`solo`, `clinic`, `team`), nome, CNPJ/CPF, plano, configurações de white-label, região de dados.
- **Membership**: usuário ↔ organização, com papéis múltiplos: `owner`, `admin`, `trainer`, `physio`, `nutritionist`, `reception`.
- **ProfessionalProfile**: especialidades, número de registro (CREF/CREFITO/CRN + UF), status de verificação (`pending`, `verified`, `rejected`), documento comprobatório.
- **PlatformStaff**: equipe do RP (você), com acesso ao painel global. Acesso a dados clínicos de pacientes só via fluxo de suporte com consentimento e log ("break-glass").

Um profissional independente é uma organização `solo` com um único membro. Uma clínica é uma organização com vários membros. Um paciente pode ser atendido por profissionais de **organizações diferentes** (ex.: nutricionista autônoma + personal de outra academia), por isso o vínculo é com o profissional, e não só com a organização.

### 3.2 Paciente e vínculo de cuidado

- **Patient** = usuário Django com `UserProfile` (já existente). Pode existir antes de ter conta (cadastro feito pelo profissional, convite por e-mail/WhatsApp para ativar).
- **CareRelationship**: `patient`, `professional`, `organization`, `discipline` (`training`, `physio`, `nutrition`), `status` (`invited`, `active`, `paused`, `ended`), datas.
- Os módulos que o paciente vê no app são **derivados dos vínculos ativos com plano publicado** (Testes 1 a 5):
  - só `training` ativo → só treino;
  - só `nutrition` → dieta, diário, calorias e macros;
  - `physio` → protocolo, vídeos, dor e evolução funcional;
  - `training` + `nutrition` → tela **Meu Dia** com as duas colunas.
- Usuários sem profissional (uso pessoal, como hoje no wger) continuam funcionando com planos próprios.

### 3.3 Autorizações de compartilhamento (consentimento granular)

**AccessGrant**: `patient`, `grantee` (CareRelationship), `scope`, `purpose`, `granted_at`, `revoked_at`, `consent_text_version`, `granted_via` (app/presencial).

Catálogo inicial de escopos (somente leitura, sempre):

| Escopo | Conteúdo | Típico para |
|---|---|---|
| `training.schedule` | Dias, horários, tipo de atividade, duração prevista, frequência semanal | Nutricionista, fisioterapeuta |
| `training.adherence` | Sessões realizadas x planejadas, RPE médio | Fisioterapeuta, nutricionista |
| `training.goals` | Objetivo esportivo declarado | Nutricionista |
| `nutrition.shared_guidance` | Orientações que o nutricionista marcou como "compartilháveis" (ex.: "pré-treino 60 min antes") | Personal, fisioterapeuta |
| `nutrition.restrictions` | Alergias e restrições relevantes ao treino | Personal, fisioterapeuta |
| `nutrition.adherence_summary` | Percentual de adesão, sem o diário detalhado | Personal, fisioterapeuta |
| `physio.functional_summary` | Evolução funcional, restrições de movimento, liberações | Personal |
| `physio.pain_summary` | Tendência de dor | Personal |
| `body.measurements` | Peso e medidas | Todos |
| `notes.multidisciplinary` | Mural de observações conjuntas | Todos os vinculados |

O prontuário completo (anamnese clínica, avaliação completa, diário alimentar detalhado) **não** é compartilhável por escopo: cada profissional vê o próprio prontuário (Teste 8).

### 3.4 Onde a regra é aplicada

1. **Serviço central de política** (`wger/care/policy.py`): `can(user, action, obj)` e `visible_queryset(user, model)`. Única fonte de verdade.
2. **ViewSets DRF** usam permissões e querysets do serviço. Nenhuma view filtra "na mão".
3. **PowerSync**: regras de sincronização por paciente e por vínculo; uploads passam por `check_fk_ownership` estendido para considerar autoria profissional.
4. **PostgreSQL RLS** (Fase 6): `organization_id = current_setting('app.org_id')` como rede de segurança.
5. **Auditoria**: leitura de dado de outro módulo ou de outro tenant grava `AccessLog`.

### 3.5 Adaptação do modelo de dono do wger

Hoje todo objeto tem um único dono (`get_owner_object()` → usuário). Na RP:

- A prescrição continua tendo `user = paciente` (o app do paciente e o PowerSync seguem funcionando).
- Ganha `organization`, `author` (profissional), `care_relationship`, `discipline`, `status`, `version`, `lineage_id`.
- Se `author` ≠ paciente, o paciente tem **somente leitura** na prescrição e escrita apenas nos registros de execução.
- Escrita do profissional exige: vínculo ativo + especialidade compatível com `discipline` + autoria do plano (ou papel `admin` da mesma organização, configurável).

---

## 4. Módulos funcionais

### 4.1 Nutrição (prioridade do documento)

**Painel do nutricionista**
- Cadastro de paciente, anamnese nutricional (formulário configurável), avaliação (peso, altura, circunferências, dobras, bioimpedância quando houver), objetivos, preferências, restrições, alergias, intolerâncias, rotina e horários.
- Cálculo de necessidades energéticas **transparente**: o sistema mostra a equação escolhida (ex.: Harris-Benedict, Mifflin-St Jeor, Cunningham, Henry/Oxford), os insumos, o fator de atividade e o resultado; o nutricionista pode sobrescrever qualquer valor. Nada é imposto.
- Metas: calorias, proteína (g ou g/kg), carboidratos, gorduras, fibras e micronutrientes escolhidos. Sem distribuição universal.

**Construtor de dietas**
- Refeições padrão (café da manhã, lanche da manhã, almoço, lanche da tarde, pré-treino, pós-treino, jantar, ceia), editáveis, reordenáveis (arrastar e soltar), com horário-alvo e orientações.
- Itens: alimento, quantidade, unidade (g, ml, unidade, medida caseira, porção), equivalente em gramas, orientações.
- Totais recalculados em tempo real (por refeição e por dia) e comparados às metas, com gráfico de distribuição de macros.
- Variações por tipo de dia (ex.: "dia de treino" e "dia de descanso"), vinculáveis ao calendário de treino quando autorizado.
- Duplicar plano, salvar como modelo, publicar (gera versão imutável e notifica o paciente).

**Substituições**
- `SubstitutionGroup` por item prescrito, com opções e quantidades equivalentes.
- Modos: equivalência energética, equivalência por macronutriente-alvo (ex.: mesmo carboidrato), manual, por preferência, por disponibilidade.
- O sistema **sugere** quantidades equivalentes; **só o nutricionista aprova**. O paciente vê apenas as opções aprovadas.

**Diário alimentar (estilo diário de registro)**
- Por refeição, com alimento, quantidade, calorias, macros, horário e comparação com o prescrito.
- Atalhos: "segui esta refeição" (registra o prescrito com um toque), "segui parcialmente" (edita quantidades), "não segui", "registrar outra coisa".
- Busca, recentes, favoritos, refeições salvas, copiar refeição de outro dia, código de barras.
- Extras, bebidas, observações.
- Adesão por refeição e por dia, calculada com regra explícita e visível.
- Foto da refeição (Fase 5): estimativa marcada como **aproximada**, sempre confirmada pelo paciente antes de entrar no diário.

**Hidratação**
- Registro por copo (tamanho configurável) ou ml, total diário, histórico.
- Meta individual definida pelo nutricionista (ou pelo próprio usuário sem acompanhamento). Sem meta universal obrigatória.

**Evolução**
- Gráficos de peso, medidas, circunferências, composição corporal (quando mensurada), adesão, consumo médio x meta.
- Comparação entre avaliações de datas diferentes.
- Textos do sistema evitam afirmar ganho/perda de gordura a partir do peso; mostram "variação de peso corporal".

### 4.2 Treinamento físico

Reaproveita o motor de rotinas do wger e acrescenta:
- **RPE** (além do RIR já existente), **cadência** (ex.: `3-1-1-0`), **tempo de isometria**, **amplitude** (completa, parcial, faixa em graus), **vídeo e orientação por exercício na prescrição**.
- **Periodização**: `TrainingCycle` (macrociclo) → mesociclos (rotinas existentes, ordenadas) → microciclos (semanas, já calculadas pelo wger por iteração), com objetivo e volume-alvo por fase.
- Planejado x realizado (já existe) + volume por grupo muscular, tonelagem, RPE médio, frequência.
- Modelos, duplicação, histórico de versões (mesmo mecanismo de versionamento).
- Upload de vídeo de execução pelo aluno, vinculado ao exercício/sessão, com fila de "vídeos pendentes" para o profissional.

### 4.3 Fisioterapia

- **Avaliação**: anamnese, testes funcionais, goniometria (ADM por articulação e lado), força (escala de Oxford/MRC ou dinamometria), mobilidade, equilíbrio, coordenação. Tudo via motor de avaliações (4.5).
- **Protocolo terapêutico** (`PhysioProtocol`, versionado): exercícios da biblioteca com dosagem (séries, repetições, tempo, carga, frequência semanal, local: domicílio/academia/clínica), progressões e critérios de avanço.
- **Dor**: Escala Numérica de 0 a 10 configurável por protocolo (antes, durante, depois, 24 h depois), local da dor, e alertas configuráveis para o fisioterapeuta (ex.: dor ≥ 7 ou aumento de 3 pontos).
- **Questionários padronizados**: LEFS, QuickDASH, Oswestry (ODI), KOOS, HOOS, além de testes como TUG. Cada um com versão validada em português, regra de pontuação e **status de licença** (ver 7.3). Só entram no catálogo após verificação.
- **Sessões**: registro de atendimento presencial (evolução clínica), separado da execução domiciliar.
- Gráficos de dor, função e adesão.

### 4.4 Biblioteca unificada

- Exercícios: base wger (pública) + **exercícios privados da organização** (com vídeos próprios). Campos novos: erros comuns, nível de dificuldade, contexto (`strength`, `rehab`, `mobility`, `conditioning`), região corporal, precauções.
- ExRx, MuscleWiki, Physitrack: **conteúdo protegido**. Integração somente com contrato/licença; até lá, usar a base wger + vídeos próprios.
- Alimentos, receitas e preparações: ver 7.1.

### 4.5 Motor de avaliações e anamneses (transversal)

Um único mecanismo para anamnese nutricional, avaliação fisioterapêutica, questionários padronizados e reavaliações:
- `AssessmentTemplate` (schema JSON de perguntas, tipos, regra de pontuação, versão, licença, especialidade).
- `Assessment` (instância por paciente e data, autor, status), `AssessmentAnswer`, `AssessmentScore`.
- Pode ser preenchido pelo profissional ou enviado ao paciente pelo app.

### 4.6 Tela "Meu Dia"

- Mostra as áreas dos módulos ativos do paciente; nunca mostra área vazia.
- Celular: cartões empilhados ou abas "Treino | Alimentação"; tablet/desktop: duas colunas.
- Linha do tempo do dia (opcional): refeições e treino ordenados por horário (07h café, 12h almoço, 16h lanche, 18h treino, 20h jantar).
- Seletor de visualização: Treino / Alimentação / Treino + Alimentação (só aparece com os dois ativos).
- Abrir exercício ou refeição em painel sobreposto, sem perder o contexto.

### 4.7 Calendário integrado

Visões semanal e mensal com: treinos programados, descanso, refeições (resumo), avaliações, sessões de fisioterapia, consultas, metas. Filtros por modalidade. Eventos derivados das prescrições (não duplicados em tabela) + compromissos explícitos (`Appointment`).

### 4.8 Comunicação

- Chat por vínculo de cuidado (cada profissional tem sua conversa com o paciente) + **mural multidisciplinar** por paciente (autoria, data, especialidade).
- Texto, áudio, imagem, vídeo, documento, com armazenamento privado e antivírus nos uploads.
- Feedback estruturado: sobre refeição, sobre exercício (com vídeo), dúvidas de prescrição.
- **WhatsApp Business Platform (Cloud API)**: notificações por modelos aprovados (lembrete de registro, nova dieta publicada, consulta marcada), com opt-in explícito. A conversa clínica fica dentro do app (histórico, auditoria e LGPD sob controle).
- Push (FCM/APNs) e e-mail (já existe `mailer`).

### 4.9 RP Intelligence

- **Pipeline**: (1) consultas SQL calculam fatos do período (sessões, adesão, médias de RPE, dor, consumo x meta); (2) os fatos, já filtrados pelas autorizações de quem pede, são enviados ao modelo; (3) a resposta vem em formato estruturado com três seções: **Fatos registrados**, **Interpretações** e **Pontos para o profissional avaliar**; (4) o profissional revisa, edita e só então compartilha.
- Restrições codificadas: sem diagnóstico, sem prescrição autônoma, sem alteração de planos (a IA não tem ferramenta de escrita).
- Cada relatório guarda os insumos usados (rastreabilidade), o modelo e o custo.
- Fase 5 também: análise assistida de vídeo de execução (observações para o profissional, não laudo) e estimativa de porção por foto (marcada como aproximada).
- Modelo padrão: `claude-opus-5-5` (US$ 4 / US$ 20 por milhão de tokens de entrada/saída). Relatórios semanais podem usar a Batch API (50% mais barata). Custos na seção 9.

### 4.10 Painéis

| Painel | Indicadores |
|---|---|
| Paciente | Meu Dia, progresso semanal, calorias e macros consumidos x meta, hidratação, exercícios concluídos, mensagens, evolução |
| Personal | Alunos ativos, treinos realizados, evolução de cargas, RPE, frequência, vídeos pendentes, alunos sem treino há N dias |
| Fisioterapeuta | Pacientes ativos, evolução funcional, registros de dor e alertas, sessões, exercícios realizados, feedbacks |
| Nutricionista | Pacientes ativos, dietas publicadas, avaliações pendentes, adesão registrada, evolução, diários sem registro, mensagens pendentes |
| Admin da clínica | Profissionais, pacientes por profissional, ocupação, assinatura |
| Admin global | Organizações, assinaturas, MRR, churn, inadimplência, verificação de registros, suporte, incidentes |

### 4.11 Gamificação

Metas semanais, calendário de consistência, conquistas, hábitos, hidratação, treinos concluídos, refeições registradas. Regras de segurança codificadas:
- Nenhuma conquista por déficit calórico, ingestão abaixo da meta mínima, jejum ou peso perdido.
- Conquistas de treino suspensas quando há dor registrada acima do limite do protocolo.
- "Sequências" não punem dias de descanso prescritos.
- Desativável pelo paciente e pelo profissional (já existe `trophies_enabled` no perfil).

### 4.12 SaaS e comercialização

- Planos por especialidade (Personal, Fisio, Nutri), combinados e Clínica, com limites (pacientes ativos, profissionais, armazenamento de vídeo, relatórios de IA).
- Assinatura recorrente (cartão e PIX), período de teste, cupons, upgrade/downgrade, inadimplência com período de carência e modo somente leitura (dados nunca são apagados por falta de pagamento sem aviso e prazo de exportação).
- White-label: logo, cores, nome no app web e e-mails; app nativo com marca própria é serviço adicional (publicação separada nas lojas).
- Painel global com métricas comerciais.

---

## 5. Modelo de dados

### 5.1 Novos apps Django

| App | Entidades principais |
|---|---|
| `tenancy` | `Organization`, `Membership`, `ProfessionalProfile`, `Invitation`, `BrandingSettings` |
| `care` | `CareRelationship`, `AccessGrant`, `ConsentRecord`, `MultidisciplinaryNote`, `PatientIntake` |
| `assessments` | `AssessmentTemplate`, `Assessment`, `AssessmentAnswer`, `AssessmentScore`, `AnthropometricRecord` |
| `physio` | `PhysioProtocol`, `ProtocolExercise`, `PainScaleConfig`, `PainRecord`, `ClinicalSession`, `FunctionalTestResult` |
| `agenda` | `Appointment`, `AvailabilitySlot`, `Reminder` |
| `messaging` | `Conversation`, `Message`, `Attachment`, `ReadReceipt`, `NotificationPreference`, `WhatsAppTemplate`, `OutboundMessageLog` |
| `intelligence` | `AIReport`, `AIReportInput`, `AIUsage` |
| `billing` | `Product`, `Price`, `Subscription`, `Invoice`, `PaymentEvent`, `Entitlement` |
| `audit` | `AccessLog`, `ChangeLog`, `DataExportRequest`, `DataDeletionRequest`, `IncidentRecord`, `RetentionPolicy` |

### 5.2 Extensões nos apps existentes

**`nutrition`**
- `FoodSource` (TACO, TBCA, USDA, Open Food Facts, organização, usuário) com versão da base e licença.
- `Ingredient` ganha: `food_source`, `source_version`, `preparation_state` (cru, cozido, grelhado...), `organization` (nulo = público), `verified_by`, `verified_at`. Nutrientes extras em `Nutrient` + `IngredientNutrient` (valor por 100 g, nulo = não informado).
- `Brand` (normalizar o atual campo texto, mantendo compatibilidade).
- `Recipe`, `RecipeItem`, rendimento e porções (gera nutrientes por porção).
- `FavoriteFood`, `SavedMeal`.
- `NutritionPlan` ganha: `organization`, `author`, `care_relationship`, `status`, `version`, `lineage_id`, `previous_version`, `published_at`, `day_type`.
- `Meal` ganha: `target_time`, `meal_kind` (café, almoço, pré-treino...), `instructions`.
- `MealItem` ganha: `instructions`, `household_measure_text`.
- `SubstitutionGroup`, `SubstitutionOption` (alimento, quantidade, unidade, critério, aprovado por).
- `NutritionGoal` (histórico de metas com vigência).
- `LogItem` ganha: `plan_version` (implícito pelo FK do plano versionado), `source` (`prescribed`, `substitution`, `extra`), `meal_kind`.
- `MealAdherence` (paciente, data, refeição prescrita, `full`/`partial`/`skipped`, observação).
- `HydrationGoal`, `WaterLog`.

**`manager`**
- `Routine` ganha os mesmos campos de autoria/versão/status/organização.
- `SlotEntry` ganha `rpe` e `max_rpe` (configs de progressão), `tempo`, `iso_hold_seconds`, `range_of_motion`, `video_override`.
- `WorkoutLog` ganha `rpe`, `pain` (opcional, quando há vínculo de fisioterapia).
- `TrainingCycle`, `TrainingCyclePhase` (macro e mesociclos).
- `ExecutionVideo` (vídeo enviado pelo aluno, status de revisão, feedback).

**`exercises`**
- `organization` (exercício privado), `common_errors`, `difficulty`, `context`, `body_region`, `precautions`. Como `simple_history` rastreia esses modelos, cada campo novo também altera a tabela histórica na migração.

**`core`**
- `UserProfile` ganha consentimentos de termos (versão aceita), preferências de visualização do Meu Dia; fuso horário já existe.

### 5.3 Relações principais (resumo ER)

```text
Organization 1─* Membership *─1 User(profissional) 1─1 ProfessionalProfile
Organization 1─* CareRelationship *─1 User(paciente)
CareRelationship 1─* AccessGrant
CareRelationship 1─* {NutritionPlan, Routine, PhysioProtocol}  (prescrições versionadas, lineage_id)
NutritionPlan 1─* Meal 1─* MealItem 1─* SubstitutionGroup 1─* SubstitutionOption
NutritionPlan 1─* LogItem (diário)        Meal 1─* MealAdherence
Routine 1─* Day 1─* Slot 1─* SlotEntry      Routine 1─* WorkoutSession 1─* WorkoutLog
PhysioProtocol 1─* ProtocolExercise         PhysioProtocol 1─* PainRecord
User(paciente) 1─* Assessment *─1 AssessmentTemplate
CareRelationship 1─1 Conversation 1─* Message 1─* Attachment
User(paciente) 1─* MultidisciplinaryNote (autor = profissional)
Organization 1─* Subscription 1─* Invoice
* ─ AccessLog (quem, o quê, quando, por qual escopo)
```

### 5.4 Versionamento (Teste 9)

```text
Plano "Hipertrofia - Jan" v1 (published 01/01)  ← LogItems de jan apontam aqui
          │ nutricionista clica "editar"
          ▼
Plano v2 (draft, previous_version=v1, mesmo lineage_id)
          │ "publicar"
          ▼
v1 → superseded (somente leitura, continua consultável)
v2 → published (paciente passa a ver v2; diário novo aponta para v2)
```

- Ao publicar, grava-se também um **snapshot JSON assinado por hash** (valor de registro, útil em auditoria e conselho profissional).
- O mesmo mecanismo vale para `Routine` e `PhysioProtocol`.

### 5.5 Regras de migração

- Novos campos de autoria nascem **nulos** (dados atuais do wger são planos próprios do usuário).
- Restrições NOT NULL/únicas só com migração de dados que corrija linhas existentes.
- Campos novos em tabelas sincronizadas pelo PowerSync exigem atualizar as regras de sync e o handler de upload.

---

## 6. Fluxos principais

**F1. Cadastro do profissional**
Cadastro → escolha de especialidade(s) → dados de registro no conselho → criação da organização `solo` (ou convite para clínica) → escolha de plano/teste → verificação do registro (manual pelo admin no início) → painel liberado (antes da verificação: uso limitado).

**F2. Cadastro e convite do paciente**
Profissional cria paciente (nome, contato, data de nascimento) → sistema cria `CareRelationship(invited)` → convite por e-mail/WhatsApp → paciente ativa a conta, aceita termos e **consentimento específico para dados de saúde** → vínculo `active`. Se o paciente já tem conta (atendido por outro profissional), o convite só adiciona o vínculo.

**F3. Prescrição de dieta**
Anamnese → avaliação → cálculo de necessidades (editável) → metas → construtor (refeições, itens, substituições, orientações) → pré-visualização "como o paciente vê" → publicar → notificação → paciente vê a dieta no app.

**F4. Diário e adesão**
Paciente abre a refeição → "segui" / "segui parcialmente" / "não segui" / "outra coisa" → registros entram no diário (offline, sincroniza depois) → painel do paciente atualiza totais → painel do nutricionista atualiza adesão.

**F5. Treino**
Personal monta rotina/ciclo → publica → aluno executa na academia (offline), registra carga, repetições, RIR/RPE → envia vídeo de execução (opcional) → personal vê planejado x realizado e vídeos pendentes → feedback.

**F6. Fisioterapia com dor**
Avaliação → protocolo publicado com configuração de dor → paciente registra dor antes/durante/depois → alerta ao fisioterapeuta se passar o limite → questionário reaplicado na reavaliação → gráfico de evolução.

**F7. Compartilhamento multidisciplinar**
Paciente (ou profissional, que pede) → tela de autorizações → escolhe profissional e escopos → registro de consentimento → o outro profissional passa a ver o cartão compartilhado no seu painel → revogação imediata a qualquer momento.

**F8. Relatório de IA**
Profissional pede "resumo da semana" → fatos calculados com os escopos dele → IA gera texto estruturado → profissional revisa e edita → opcional: compartilha no mural ou com o paciente.

**F9. Assinatura**
Escolha de plano → checkout (cartão/PIX) → webhook do gateway → `Subscription(active)` → `Entitlement` libera limites → inadimplência: aviso, carência, modo somente leitura, exportação.

**F10. Direitos do titular (LGPD)**
Paciente pede exportação → arquivo gerado (JSON + PDF) em até X dias → link assinado. Pedido de exclusão → verificação de obrigações legais de guarda (prontuário) → exclusão/anonimização do que for possível → registro do atendimento.

---

## 7. Integrações e fontes de dados

### 7.1 Alimentos

| Base | Conteúdo | Licença/condições (verificar antes de importar) | Uso |
|---|---|---|---|
| **TACO** (NEPA/UNICAMP) | Cerca de 600 alimentos brasileiros, crus e preparados | Uso livre com citação da fonte | Base principal de alimentos in natura |
| **TBCA** (FoRC/USP) | Milhares de alimentos e preparações brasileiras, vários micronutrientes | Termos de uso próprios; **confirmar permissão para uso comercial/redistribuição** com os responsáveis | Complemento; importar só após autorização |
| **USDA FoodData Central** | Grande base americana | Domínio público (CC0) | Complemento; o wger já tem importador |
| **Open Food Facts** | Industrializados com código de barras | ODbL (compartilhamento pela mesma licença da base derivada) | Código de barras; o wger já integra |
| **Alimentos da organização** | Cadastrados/corrigidos pelo nutricionista | Da organização | Visíveis só na organização (ou compartilhados, se ela quiser) |

Regras:
- Cada alimento mostra a fonte, a versão da base e o estado de preparo.
- Nutriente ausente fica **nulo** e aparece como "não informado"; nunca é estimado silenciosamente.
- No wger atual, `energy`, `protein`, `carbohydrates` e `fat` são obrigatórios. Para alimentos de bases com lacunas, a migração precisa torná-los anuláveis e ajustar os cálculos de totais para indicar "total parcial" quando algum item não tiver o valor.
- Correções feitas por nutricionistas criam um alimento derivado da organização, sem sobrescrever a base pública.

### 7.2 Exercícios e vídeos

- Base wger (CC-BY-SA: exige atribuição; conteúdo derivado segue a mesma licença).
- Vídeos próprios gravados por você/organização: propriedade sua, armazenamento privado.
- ExRx, MuscleWiki, Physitrack: somente com contrato. Não importar conteúdo sem licença.

### 7.3 Instrumentos clínicos

| Instrumento | Situação usual de licença (confirmar com o detentor) |
|---|---|
| KOOS / HOOS | Geralmente de uso livre, com versões oficiais em português no site dos autores |
| LEFS | Amplamente usado; verificar termos da versão brasileira validada |
| QuickDASH | Detentor: Institute for Work & Health; uso comercial pode exigir licença |
| Oswestry (ODI) | Detido via Mapi Research Trust; uso em software comercial normalmente exige licença |
| TUG | Teste de desempenho, sem questionário protegido |
| END (0 a 10) | Escala de domínio público |

Cada instrumento só entra no catálogo após verificação da licença e da versão validada em português, com registro no `AssessmentTemplate`.

### 7.4 WhatsApp Business Platform

- Cloud API oficial da Meta, número verificado, modelos de mensagem aprovados.
- Cobrança por mensagem de modelo conforme categoria (marketing, utilidade, autenticação) e país; respostas dentro da janela de atendimento têm regras próprias. Consultar a tabela vigente da Meta para o Brasil antes de definir o preço dos planos.
- Opt-in registrado; opt-out com um toque; sem dados clínicos detalhados no corpo da mensagem (ex.: "Sua nova dieta está disponível no app" em vez do conteúdo).

### 7.5 Pagamentos

Candidatos com PIX recorrente/cartão no Brasil: Asaas, Pagar.me, Stripe (Brasil), Mercado Pago. Critérios: assinatura recorrente, PIX automático, emissão de NFS-e, split (para clínicas no futuro), webhooks confiáveis, taxas. Recomendação inicial: **Asaas** (assinaturas + PIX + boleto + NFS-e numa só API) com camada de abstração `billing.providers` para permitir troca.

### 7.6 IA

API da Anthropic, chamada apenas do backend (chave nunca no app). Dados enviados: somente os fatos do relatório, sem nome/CPF (pseudonimização: "Paciente A"). Registrar o tratamento no RIPD (seção 8).

---

## 8. Segurança e LGPD

Dados de saúde são **dados pessoais sensíveis** (LGPD, art. 5º, II, e art. 11).

| Controle | Implementação |
|---|---|
| Base legal | Tutela da saúde por profissionais de saúde (art. 11, II, "f") para o atendimento; **consentimento específico e destacado** para compartilhamento multidisciplinar, IA e marketing |
| Papéis LGPD | Profissional/clínica = controlador dos dados do paciente; RP Performance = operador (e controlador dos dados de conta e cobrança). Contrato de tratamento de dados no aceite do plano |
| Encarregado (DPO) | Nomear e publicar contato |
| RIPD | Relatório de Impacto antes do lançamento comercial |
| Criptografia | TLS 1.2+ em trânsito; disco/banco/backup criptografados; campos especialmente sensíveis (anamnese clínica, observações) com criptografia em nível de aplicação |
| Isolamento | Filtro por organização em toda consulta + RLS (Fase 6) + testes automáticos de isolamento |
| Autenticação | MFA obrigatório para profissionais e admins; sessões curtas no painel; bloqueio por tentativas |
| Permissões | Mínimo necessário, escopos por consentimento, break-glass auditado para suporte |
| Logs de acesso | `AccessLog` imutável (quem, quando, o quê, por qual escopo), retenção definida; nunca registrar segredos ou corpo de respostas de autenticação |
| Arquivos e vídeos | Bucket privado, URLs assinadas de minutos, sem link público, verificação antivírus em uploads |
| Backup | Backup diário + PITR do PostgreSQL, cópia em outra região, teste de restauração trimestral |
| Direitos do titular | Exportação, correção, exclusão/anonimização, revogação de consentimento, pelo app |
| Retenção | Política por tipo de dado; prontuários seguem prazo legal de guarda (Lei 13.787/2018 e normas dos conselhos), após o qual são eliminados |
| Incidentes | Plano de resposta, registro de incidentes, comunicação à ANPD e aos titulares quando aplicável, no prazo regulamentar |
| Transferência internacional | Preferir hospedagem no Brasil (ex.: AWS sa-east-1). Serviços fora (IA, WhatsApp) exigem cláusulas contratuais conforme regulamento da ANPD sobre transferência internacional |
| Normas profissionais | Verificar resoluções vigentes do CFN, COFFITO e CONFEF sobre prontuário eletrônico, teleatendimento e guarda de registros. Prescrição dietética é atividade privativa do nutricionista (Lei 8.234/1991); o sistema só permite prescrição de dieta a perfis com CRN |
| Regulação de software | A IA não diagnostica nem prescreve, o que reduz o risco de enquadramento como software médico (ANVISA, RDC 657/2022). Reavaliar se a Fase 5 ganhar funções de apoio à decisão clínica |

---

## 9. Custos estimados

Valores em dólar convertidos aproximadamente para reais (câmbio de referência R$ 5,50). São ordens de grandeza para planejamento; confirmar com cotações no momento da contratação.

### 9.1 Infraestrutura mensal

| Item | Uso pessoal (Fase 1 a 3) | Até ~50 profissionais / 2.000 pacientes | Até ~500 profissionais / 20.000 pacientes |
|---|---|---|---|
| Servidor de aplicação + workers | US$ 25 a 50 | US$ 120 a 250 | US$ 600 a 1.200 |
| PostgreSQL gerenciado com backup | US$ 15 a 30 | US$ 100 a 200 | US$ 400 a 900 |
| Redis | incluso no servidor | US$ 15 a 30 | US$ 50 a 100 |
| PowerSync | plano gratuito/autohospedado | US$ 50 a 100 | US$ 300 a 600 |
| Armazenamento de fotos e documentos | < US$ 5 | US$ 10 a 30 | US$ 80 a 200 |
| Vídeo (streaming) | US$ 5 a 10 | US$ 50 a 150 | US$ 400 a 1.000 |
| E-mail transacional, monitoramento, logs | US$ 0 a 20 | US$ 50 a 100 | US$ 200 a 400 |
| **Total aproximado** | **US$ 50 a 120 (R$ 275 a 660)** | **US$ 400 a 850 (R$ 2,2 mil a 4,7 mil)** | **US$ 2 mil a 4,4 mil (R$ 11 mil a 24 mil)** |

### 9.2 Custos variáveis

| Item | Estimativa |
|---|---|
| IA: relatório semanal por paciente (~15 mil tokens de entrada, ~1,5 mil de saída, `claude-opus-5-5`) | ~US$ 0,09 por relatório (US$ 0,045 via Batch API). 100 pacientes com 4 relatórios/mês ≈ US$ 18 a 36/mês |
| IA: análise de foto de refeição | Centavos de dólar por foto; limitar por plano |
| WhatsApp | Por mensagem de modelo, segundo a tabela da Meta para o Brasil (frações de dólar por mensagem); limitar por plano ou repassar |
| Gateway de pagamento | Aproximadamente 1 a 5% por transação, conforme meio (PIX mais barato que cartão) |
| Lojas de aplicativos | Apple: US$ 99/ano; Google Play: US$ 25 (taxa única) |

### 9.3 Custos únicos e de conformidade

| Item | Estimativa |
|---|---|
| Assessoria jurídica LGPD (termos, política, contrato de operador, RIPD) | R$ 8 mil a 30 mil |
| Licenças de questionários clínicos protegidos | Variável por instrumento; pedir orçamento ao detentor |
| Licença de bibliotecas de vídeo de terceiros (se houver) | Sob contrato |
| Produção de vídeos próprios | Variável; recomendada para os 100 a 150 exercícios mais usados |
| Teste de invasão antes da comercialização | R$ 15 mil a 40 mil |

### 9.4 Esforço de desenvolvimento

Estimativa em semanas de uma equipe pequena (1 backend, 1 frontend/mobile, design parcial), partindo do wger:

| Fase | Semanas | Observação |
|---|---|---|
| 1. Fundação | 6 a 8 | Rebranding, tenancy, vínculo, consentimento, painéis-base |
| 2. Treino e fisioterapia | 8 a 10 | Motor de treino já existe; fisioterapia e avaliações são novas |
| 3. Nutrição | 10 a 12 | Maior volume: bases de alimentos, substituições, versionamento, diário |
| 4. Integração | 8 a 10 | Meu Dia, calendário, chat, WhatsApp, relatórios |
| 5. Inteligência | 6 a 8 | IA, análise de vídeo e foto |
| 6. Comercialização | 8 a 10 | Assinaturas, white-label, RLS, admin global, testes de segurança |
| **Total** | **46 a 58 semanas** | Aproximadamente 11 a 14 meses; fases podem se sobrepor parcialmente |

Para converter em custo: semanas × pessoas × 40 h × valor/hora da equipe contratada.

---

## 10. Telas

### 10.1 App do paciente

1. Boas-vindas, login, ativação por convite, aceite de termos e consentimentos.
2. **Meu Dia** (adaptativo aos módulos ativos).
3. Treino do dia → execução do treino (cronômetro de descanso, registro de carga/repetições/RIR/RPE, vídeo do exercício, enviar vídeo de execução).
4. Plano alimentar (por refeição, com substituições aprovadas e orientações).
5. Diário alimentar (refeições, totais, restante, busca, código de barras, favoritos, refeições salvas).
6. Hidratação.
7. Fisioterapia: protocolo do dia, vídeo, registro de dor, questionários enviados.
8. Calendário.
9. Evolução (peso, medidas, cargas, dor, adesão).
10. Mensagens (por profissional) e mural.
11. Conquistas e hábitos (se ativos).
12. Perfil: profissionais vinculados, **autorizações de compartilhamento**, notificações, exportar/excluir dados.

### 10.2 Painel profissional

1. Início (indicadores da especialidade, alertas, pendências).
2. Lista de pacientes (filtros por status, adesão, alertas).
3. Ficha do paciente com abas: Resumo · Anamnese · Avaliações · Prescrição (do módulo do profissional) · Execução/Diário · Evolução · Compartilhado comigo · Mensagens · Mural · Relatórios de IA · Histórico de versões.
4. Construtor de dietas (refeições em colunas, busca lateral de alimentos, totais fixos no topo, gráfico de macros, substituições).
5. Construtor de treinos e ciclos.
6. Construtor de protocolos de fisioterapia.
7. Biblioteca (exercícios, alimentos, receitas, modelos de plano, modelos de avaliação).
8. Agenda.
9. Fila de vídeos pendentes.
10. Configurações da organização, equipe, marca, assinatura.

### 10.3 Admin global

Organizações · profissionais (verificação de registro) · assinaturas e faturas · métricas (MRR, churn, ativos) · suporte e acesso break-glass · incidentes · catálogo global (bases de alimentos, instrumentos, exercícios) · auditoria.

### 10.4 Identidade visual

| Token | Cor sugerida | Uso |
|---|---|---|
| `navy-900` | `#0B1F3A` | Barra lateral, cabeçalhos, botões primários |
| `navy-700` | `#16365F` | Estados hover, cartões escuros |
| `white` | `#FFFFFF` | Fundo |
| `neon-500` | `#39FF88` | Destaques, metas atingidas, chamadas de ação secundárias (sobre fundo escuro; em fundo branco usar `neon-700` para contraste) |
| `neon-700` | `#12B85C` | Texto/ícones de destaque sobre branco |
| `gray-500` | `#6B7280` | Texto secundário |
| `gray-100` | `#F3F4F6` | Divisórias e fundos de seção |

Cores dos macronutrientes nos gráficos definidas uma vez e usadas em todo o produto. Contraste mínimo WCAG AA.

---

## 11. Planejamento por fases (com entregas verificáveis)

### Fase 1: Fundação (semanas 1 a 8)
- Rebranding RP Performance no backend, painel e app (mantendo o aviso de licença AGPL e o link para o código).
- Apps `tenancy`, `care`, `audit` (básico); serviço de política de acesso; MFA para profissionais.
- Cadastro de profissional, organização `solo`, cadastro/convite de paciente, consentimentos.
- Painel profissional com lista de pacientes e ficha; app do paciente com módulos derivados dos vínculos.
- CI com testes de isolamento entre organizações e entre especialidades.
- **Entrega**: você cadastra seus pacientes e cada um vê só o módulo correspondente (Testes 1 e 2 em estado inicial).

### Fase 2: Treino e fisioterapia (semanas 9 a 18)
- RPE, cadência, isometria, amplitude, periodização, versionamento de rotinas.
- Exercícios privados e vídeos próprios; vídeos de execução do aluno.
- Motor de avaliações, app `physio`, dor, primeiros instrumentos com licença verificada.
- **Entrega**: Testes 1, 3, 7 e 9 (treino/fisio) automatizados.

### Fase 3: Nutrição (semanas 19 a 30)
- Importação TACO (+ TBCA se autorizada), nutrientes extras, alimentos da organização, receitas.
- Construtor de dietas com totais em tempo real, metas, cálculo transparente, variações por tipo de dia.
- Substituições, versionamento, diário com adesão, hidratação, evolução.
- **Entrega**: Testes 2, 6 e 9 (nutrição) automatizados.

### Fase 4: Integração (semanas 31 a 40)
- Meu Dia, calendário integrado, autorizações por escopo, mural multidisciplinar, chat com mídia, push, WhatsApp, relatórios PDF.
- **Entrega**: Testes 4, 5 e 8 automatizados.

### Fase 5: Inteligência (semanas 41 a 48)
- RP Intelligence (relatórios por especialidade e multidisciplinar), análise assistida de vídeo, estimativa por foto.
- Avaliação de qualidade dos relatórios com casos reais anonimizados antes de liberar.

### Fase 6: Comercialização (semanas 49 a 58)
- Assinaturas, limites por plano, clínicas, white-label, admin global, RLS, teste de invasão, documentação pública, política de privacidade e termos finais.

---

## 12. Critérios de aceitação → testes automatizados

| Teste | Cenário automatizado |
|---|---|
| 1 | Paciente com vínculo só `training`: endpoint de módulos retorna `["training"]`; endpoints de nutrição/fisio retornam vazio para planos prescritos; app não renderiza abas vazias |
| 2 | Paciente só `nutrition`: módulos = `["nutrition"]`; dieta, diário, calorias e macros acessíveis; nenhuma rotina atribuída |
| 3 | Paciente `physio`: protocolo, vídeos, registros de dor e gráfico de evolução acessíveis |
| 4 | Paciente `training` + `nutrition`: endpoint "Meu Dia" retorna as duas seções para a data, no fuso do paciente |
| 5 | Três vínculos + escopos concedidos: cada profissional vê exatamente os cartões autorizados |
| 6 | Nutricionista tenta `PATCH` em rotina do paciente → 403; altera a dieta → rotina inalterada |
| 7 | Personal tenta `PATCH` em plano alimentar → 403; altera o treino → dieta inalterada |
| 8 | Profissional sem escopo → 403/404 nos dados do outro módulo; revogação tem efeito imediato; acesso fica no `AccessLog` |
| 9 | Publicar v2 mantém v1 legível, diário antigo aponta para v1, novo para v2; snapshot com hash confere |
| 10 | Suíte completa em PostgreSQL (não só SQLite), testes de isolamento entre organizações, testes de API com dados realistas (fixtures anonimizadas), migrações testadas em cópia de banco |

---

## 13. Decisões que dependem de você

1. **Licença**: aceitar a AGPL (produto comercial com código-fonte aberto aos usuários), ou começar uma base própria fechada (aproximadamente o dobro do prazo das fases 2 e 3)? Recomendação: aceitar a AGPL; o valor comercial está no serviço, nos dados, nos vídeos, na marca e no suporte. Confirmar com advogado.
2. **Sua especialidade** para o primeiro uso real: personal, fisioterapeuta, nutricionista ou mais de uma? Define a ordem das Fases 2 e 3.
3. **Hospedagem**: Brasil (AWS sa-east-1, custo um pouco maior) ou fora (Hetzner/DigitalOcean, mais barato, exige cláusulas de transferência internacional)?
4. **Gateway de pagamento**: Asaas (recomendado) ou outro?
5. **Repositórios dos clientes**: o app Flutter e o front React do wger não estão nesta sessão. Para alterá-los é preciso ter forks deles na sua conta do GitHub (ex.: `raynay01/flutter`, `raynay01/react`) e adicioná-los.
6. **TBCA e questionários clínicos**: autoriza que eu prepare os pedidos de licença/permissão para você enviar?

---

## 14. Próximo passo proposto

Com as decisões 1, 2 e 5 respondidas, começo a **Fase 1** neste repositório, em entregas pequenas e testadas:
1. App `tenancy` (organização, membro, perfil profissional) + migrações + testes.
2. App `care` (vínculo, autorização por escopo, consentimento) + serviço de política + testes de isolamento.
3. Endpoint "módulos ativos do paciente" (base dos Testes 1 a 4).
4. Campos de autoria/versão/status em `NutritionPlan` e `Routine` + regra de escrita por especialidade (base dos Testes 6, 7 e 9).

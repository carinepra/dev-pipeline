# Dev Pipeline Orchestrator — Guia de Uso

> **Status:** ✅ MVP Implementado (Fase 3)

## Visão Geral

O Dev Pipeline Orchestrator automatiza o ciclo completo de desenvolvimento: História Jira → Task Breakdown → Planning → Implementation → Review → PR → Address Reviews → Docs.

**Arquitetura híbrida:**
- 🤖 **Scripts Python** (automáticos): git, linters, GitHub API, Jira API
- 🧠 **Skills Cursor** (manual): análise de histórias, planejamento, review de código, interpretação de comentários
- ✋ **Validação humana** em 7 pontos críticos (aprovação de tasks, plano, arquivos a commitar, etc)

**Múltiplos projetos Jira e repositórios:** O orquestrador lê `.pipeline-config.json` na raiz do repositório para saber quais projetos Jira e quais repositórios locais usar. Os exemplos abaixo usam `<PROJECT>-1234` como placeholder genérico e `PROJ-542` como ilustração concreta; qualquer chave de projeto Jira válida funciona.

## Quick Start

### 1. Pré-requisitos

```bash
# Instalar dependências
make install-dev

# Configurar .env
JIRA_EMAIL=seu-email@exemplo.com
JIRA_API_TOKEN=seu-token-jira
GITHUB_TOKEN=ghp_seu-token-github

# (Opcional) Multi-repo setup para linters cross-repo
WHITE_LOCAL_API=../white-api
WHITE_LOCAL_BACKOFFICE=../white-app
WHITE_LOCAL_DOCS=../white-docs-tech
```

**Multi-repo setup (opcional mas recomendado):**

Se você mantém todos os repositórios do projeto em uma pasta compartilhada:

```bash
# Estrutura:
repos/
├── dev-pipeline/              # Orquestrador + estado + artefatos em pipelines/
├── white-api/       # Código da API
├── white-app/   # Código do backoffice
└── white-docs-tech/                 # Documentação técnica
```

*Os nomes de pastas acima são um exemplo de layout; confira `.pipeline-config.json` para os repositórios e caminhos usados no seu ambiente.*

Configure as variáveis `WHITE_LOCAL_*` no `.env` para que o pipeline rode linters no repo correto (nomes típicos; **os paths reais vêm de `.pipeline-config.json`**):
- Frontend tasks → linters rodam no repositório de backoffice configurado
- Backend tasks → linters rodam no repositório de API configurado

**Vantagem:** Estado centralizado no repo do orquestrador, mas review automático funciona no código real.

### 2. Pre-flight checks

O pipeline valida automaticamente:
- ✅ Env vars (JIRA_EMAIL, JIRA_API_TOKEN, GITHUB_TOKEN)
- ✅ Git config (user.name, user.email)
- ✅ GitHub CLI auth (`gh auth status`)
- ✅ Python 3.12+

### 3. Iniciar pipeline

```bash
# Produção
make dev-pipeline STORY=<PROJECT>-1234

# Dry-run (não cria issues/PRs de verdade)
make dev-pipeline STORY=<PROJECT>-1234 DRY_RUN=true
```

### 4. Workflow interativo

O pipeline guia você através de 9 fases:

1. **STORY_ANALYSIS**: 
   - Carrega história do Jira
   - Confirma escopo (backend/frontend/ambos)
   - **NOVO v1.4:** Executa `pipeline-story-analyzer` (análise Figma + docs + codebase)
   - Gera `.story-plan.md` validado

2. **TASK_BREAKDOWN**: 
   - Skill lê `.story-plan.md` (contexto consolidado)
   - Propõe tasks baseado em design, regras e decisões
   - Você aprova → cria no Jira

3. **TASK_PLANNING**: Para cada task: skill cria plano → skill melhora (3 rounds) → você aprova

4. **IMPLEMENTATION**: Você implementa código seguindo o plano

5. **REVIEW_CHANGES**: Script roda linters (no repo correto via `WHITE_LOCAL_*`) → skill analisa erros → você aprova ou corrige

6. **GIT_PUBLISH**: Mostra arquivos a commitar → você confirma → branch + commit + push + PR criada

7. **PR_REVIEW_CYCLE**: Aguarda reviews externos (manual no MVP)

8. **DOCUMENTATION**: Skill gera docs técnicos → você aprova → commit

9. **COMPLETED**: Pipeline finalizado ✅

### 5. Pausar e retomar

```bash
# Pipeline pausa automaticamente após cada fase
# Retomar:
make dev-pipeline-resume STORY=<PROJECT>-1234

# Ver status de todos pipelines ativos
make dev-pipeline-status
```

## Visualizando Trabalho Ativo

### Comando Unificado: `dev-pipeline-list`

Ver histórias + tasks numa única tela:

```bash
# Panorama completo
make dev-pipeline-list

# Filtrar por história (exemplo concreto PROJ-542; qualquer chave de projeto funciona)
make dev-pipeline-list STORY=PROJ-542

# Filtrar tasks por estado
make dev-pipeline-list STATE=IMPLEMENTING
```

**Output:** Duas tabelas consolidadas:
- **Histórias:** Key + Título + Estado + Progress
- **Tasks:** Story + Task + Título + Estado (com `◄` na atual) + PR

**Ícones:**
- 🔄 Pipeline ativo
- ⏳ Task em andamento (atual)
- ✅ Concluído/Merged
- ⏸️ Aguardando próxima fase
- 📝 Não planejado
- 🔧 Necessita correções

**Casos de uso:**
- Daily standup: `make dev-pipeline-list`
- Code review: `make dev-pipeline-list STATE=PR_OPENED`
- Planning: `make dev-pipeline-list STATE=PENDING`

**Comandos alternativos (legacy):**
- `make dev-pipeline-list-stories` (apenas histórias)
- `make dev-pipeline-list-tasks` (apenas tasks)

---

## Comandos Disponíveis

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `dev-pipeline` | Iniciar novo pipeline | `make dev-pipeline STORY=<PROJECT>-1234` |
| `dev-pipeline-resume` | Retomar pipeline pausado (restaura estado sem reexecutar handlers) | `make dev-pipeline-resume STORY=<PROJECT>-1234` |
| `dev-pipeline-status` | Status de todos pipelines ativos (ou detalhado de 1) | `make dev-pipeline-status [STORY=<PROJECT>-1234]` |
| `dev-pipeline-list` | 📚📋 **Listar histórias + tasks** (visão unificada) | `make dev-pipeline-list [STORY=<PROJECT>-1234] [STATE=IMPLEMENTING]` |
| `dev-pipeline-list-stories` | 📚 Listar todas as histórias em andamento com títulos | `make dev-pipeline-list-stories` |
| `dev-pipeline-list-tasks` | 📋 Listar todas as tasks de todas histórias (ou filtradas) | `make dev-pipeline-list-tasks [STORY=<PROJECT>-1234] [STATE=PLANNED]` |
| `dev-pipeline-next` | ✅ **Avançar automaticamente** para próxima fase | `make dev-pipeline-next STORY=<PROJECT>-1234` |
| `dev-pipeline-goto` | ✅ Pular para fase específica (**recovery only**) | `make dev-pipeline-goto STORY=<PROJECT>-1234 STAGE=REVIEW_CHANGES` |
| `dev-pipeline-cancel` | ✅ Cancelar pipeline (marca como CANCELLED) | `make dev-pipeline-cancel STORY=<PROJECT>-1234` |
| `dev-pipeline-unlock` | Forçar unlock | `make dev-pipeline-unlock STORY=<PROJECT>-1234` |
| `dev-pipeline-validate` | Validar estado JSON | `make dev-pipeline-validate STORY=<PROJECT>-1234` |

### ✅ Melhorias Implementadas (v1.2.0)

**Fase A - Fundação de estado e CLI:**
- ✅ **A.1**: Estado padronizado (sempre `PipelineStateEnum.IDLE.value` etc no JSON)
- ✅ **A.2**: `restore_from_state` implementado (restaura sem reexecutar handlers)
- ✅ **A.3**: Comandos `next`, `cancel`, `goto` totalmente funcionais

**Fase B - Fluxo de trabalho:**
- ✅ **B.2**: PR review cycle completo (fetch comments → skill analisa → implementa correções)

**Fase C - Review técnico:**
- ✅ **C.1**: Escopo vs repo detection (suporte `both`, `docs`, `infra` com fallback)
- ✅ **C.2**: Linters focados nos arquivos modificados
- ✅ **C.3**: Diff completo (staged + unstaged) em `.review-data.json`
- ✅ **C.4**: Ruff adicionado aos linters backend (se disponível)

**Fase D - Integrações e UX:**
- ✅ **D.1**: Jira story fetch real via `core/jira` (substituiu mock)
- ✅ **D.2**: Edição de task breakdown (permite reeditar JSON manualmente)
- ✅ **D.3**: Abrir arquivos cross-platform (macOS/Windows/Linux)

## Arquitetura

### State Machine (9 estados)

```
IDLE → STORY_ANALYSIS → TASK_BREAKDOWN → TASK_PLANNING (loop) → 
IMPLEMENTATION → REVIEW_CHANGES → GIT_PUBLISH → PR_REVIEW_CYCLE → 
DOCUMENTATION → COMPLETED
```

Qualquer estado pode pausar → **PAUSED** (e retomar para o estado original).

### Persistência

Estado salvo em `.pipeline-state/{STORY}-pipeline.json`:
- Schema versionado (Pydantic validation)
- Lock file com PID (previne concorrência)
- Backup automático antes de cada save
- Schema migration (v0.0 → v1.0)

### Skills Integrados (modo instrucional)

O pipeline **mostra comando para executar no Cursor** e aguarda você:

| Skill | O que faz | Quando |
|-------|-----------|--------|
| `pipeline-task-breaker` | Quebrar história em tasks | TASK_BREAKDOWN |
| `pipeline-task-planner` | Criar plano de implementação (invoca `pipeline-plan-validator`) | TASK_PLANNING |
| `pipeline-review-backend` | Analisar erros de linter (backend) | REVIEW_CHANGES |
| `pipeline-review-frontend` | Analisar erros de linter (frontend) | REVIEW_CHANGES |
| `pipeline-pr-responder` | Interpretar comentários de PR | PR_REVIEW_CYCLE / opcional |
| `skill-create-technical-docs` | Gerar documentação técnica | DOCUMENTATION |

**Custo de IA:** $0 (skills usam Cursor AI, já incluído no seu plano)

### Scripts Automáticos (Python puro, $0)

| Script | O que faz | Custo |
|--------|-----------|-------|
| `review_runner.py` | Roda black/mypy/eslint, coleta erros | $0 |
| `git_ops.py` | git status, add, commit, push, branch ops | $0 |
| `github_ops.py` | gh pr create, fetch comments | $0 |
| `jira_ops.py` | CRUD de issues (após skill propor) | $0 |

## Validações (Touch Points)

O pipeline **nunca** faz commit/push sem sua aprovação explícita:

| Etapa | Validação | Pode pular? |
|-------|-----------|-------------|
| Story Analysis | Confirmar escopo (back/front/ambos) | Não |
| Task Breakdown | Aprovar lista de tasks antes de criar no Jira | Não |
| Task Planning | Aprovar cada plano após improvement | Não |
| Implementation | Confirmar implementação concluída | Não |
| Review Changes | Aprovar review ou voltar para fixes | Não |
| Git Publish | **Confirmar arquivos a commitar** | Não |
| PR Review | Aprovar correções propostas | Não |
| Documentation | Aprovar docs antes de commitar | Sim (opcional) |

## Troubleshooting

### Pipeline travou (lock file)

```bash
# Forçar unlock
make dev-pipeline-unlock STORY=<PROJECT>-1234
```

### Estado JSON corrompido

```bash
# Validar integridade
make dev-pipeline-validate STORY=<PROJECT>-1234

# Se corrompido, restaurar do backup
cd .pipeline-state
cp <PROJECT>-1234-pipeline.backup.json <PROJECT>-1234-pipeline.json
```

### Pular para etapa específica (recovery)

Use `goto` apenas para recovery (ex: após corrigir erro manualmente):

```bash
# Estados válidos: IDLE, STORY_ANALYSIS, TASK_BREAKDOWN, TASK_PLANNING,
# IMPLEMENTATION, REVIEW_CHANGES, GIT_PUBLISH, PR_REVIEW_CYCLE,
# DOCUMENTATION, COMPLETED, PAUSED, CANCELLED

make dev-pipeline-goto STORY=<PROJECT>-1234 STAGE=REVIEW_CHANGES
```

**Nota:** O comando valida se a transição é válida segundo `VALID_TRANSITIONS`, mas permite pular em modo recovery.

### Erro ao criar PR (GitHub token)

Verifique permissões do token:
- ✅ Actions: Read
- ✅ Contents: Read
- ✅ Pull requests: Read

Se organização usa SSO: autorize o token em `Settings > Developer settings > Personal access tokens > Configure SSO`.

### Erro ao criar issue (Jira)

Verifique `.env`:
```bash
JIRA_EMAIL=seu-email@exemplo.com  # não pode ser @whitecompany.com alias
JIRA_API_TOKEN=ATATT...           # gerar em: id.atlassian.com/manage-profile/security/api-tokens
```

## Dry-Run Mode

Testar pipeline sem side effects:

```bash
make dev-pipeline STORY=<PROJECT>-1234 DRY_RUN=true
```

**O que acontece:**
- ✅ Pre-flight checks rodados normalmente
- ✅ Skills executados normalmente (você executa no Cursor)
- ✅ Estado JSON salvo normalmente
- ❌ Issues **não** criadas no Jira (keys fictícios: DRY-1, DRY-2)
- ❌ PRs **não** criadas no GitHub (URL fake)
- ✅ Logs gerados normalmente

**Uso:** Validar implementação do orquestrador antes de afetar Jira/GitHub.

## Logs

Logs salvos em `logs/pipeline-{STORY}.log`:
- Timestamp, nível, estado, ação
- Console: INFO+ (Rich colorido)
- Arquivo: DEBUG+ (completo)

```bash
# Ver log
tail -f logs/pipeline-<PROJECT>-1234.log
```

## Limitações e Roadmap

### Implementado ✅ (v1.2.0)
- ✅ State machine com 9 estados + persistência + lock + backup + schema validation
- ✅ Comandos CLI completos (start, resume, status, next, cancel, goto, unlock, validate)
- ✅ PR review cycle (fetch comments → skill address → corrigir)
- ✅ Review com linters focados nos arquivos modificados (staged + unstaged)
- ✅ Restore de estado sem reexecutar handlers
- ✅ Transições automáticas via `next` command
- ✅ **Escopo multi-repo** (`both`, `docs`, `infra`) com fallback inteligente
- ✅ **Ruff** adicionado aos linters backend (auto-detecta se disponível)
- ✅ **Jira fetch real** via `core/jira` (substituiu mock)
- ✅ **Task breakdown editável** (permite reeditar JSON manualmente)
- ✅ **Cross-platform file opening** (macOS/Windows/Linux)

### Limitações conhecidas
- Skills são executados **manualmente** (você executa no Cursor quando o pipeline pede)
  - **Motivo**: Skills usam Cursor AI (já pago), não OpenAI API adicional
  - **Workaround**: Modo instrucional (pipeline mostra comando, você executa)
- Múltiplos repos no **mesmo pipeline** não suportado totalmente
  - **Workaround**: Configure `WHITE_LOCAL_*` para linters cross-repo, ou rodar 1 pipeline por repo
- CI check automático **não implementado**
  - **Workaround**: Reviewer vê no GitHub, ou rodar `make ci-report` manualmente
- Tasks executadas **sequencialmente** (não em paralelo)
  - **Motivo**: Simplifica estado e evita conflitos de merge
  - **Futuro**: Paralelização para tasks independentes (se demanda surgir)

### Pós-MVP (futuro)
- [ ] Automação completa de skills via subprocess/API Cursor
- [ ] PR polling automático (atualmente manual: avança após reviews)
- [ ] Multi-repo simultâneo (criar PRs em backend + frontend no mesmo pipeline)
- [ ] CI check integration (integrar Fase 2: rodar após push)
- [ ] Notifications (Slack/Email quando pipeline pausar)
- [ ] Dashboard web (visualizar progresso de múltiplos pipelines)
- [ ] Métricas agregadas (tempo médio por fase, taxa de sucesso)

## Referências

- **Plano completo:** [`PLAN-FASE-3.md`](../PLAN-FASE-3.md)
- **Arquitetura híbrida:** [`PLAN-FASE-3-HYBRID-ARCHITECTURE.md`](../PLAN-FASE-3-HYBRID-ARCHITECTURE.md)
- **Skills Cursor:** `~/.cursor/skills/skill-*/SKILL.md`
- **Padrões do projeto:** `.cursor/rules/*.mdc` (frontend), `~/.cursor/skills/skill-back-review-changes/refs/` (backend, referência; no pipeline: `pipeline-review-backend`)

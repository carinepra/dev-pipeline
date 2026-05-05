# Pipeline Skills para Dev Pipeline Orchestrator

Este diretório contém as **12 skills adaptadas** especificamente para o Dev Pipeline Orchestrator.

## Skills Disponíveis

| # | Skill | Função | Features v1.5 | Linhas |
|---|-------|--------|---------------|--------|
| 1 | `pipeline-story-analyzer` | Análise completa + planejamento estratégico | 🎨 Figma<br>📚 Docs<br>💻 Codebase<br>🔍 Sanity checks<br>✅ Validação<br>🎯 Modo Plan<br>❓ AskQuestion | ~650 |
| 2 | `pipeline-story-planner` | Planejamento estratégico (orquestrador) | 🎨 Figma<br>📚 Docs<br>💻 Codebase<br>🎯 Modo Plan<br>❓ AskQuestion | ~930 |
| 3 | `pipeline-task-breaker` | Quebra de tasks (simplificado) | ✅ Lê .story-plan.md<br>📝 Propõe tasks<br>🎯 Modo Plan<br>❓ AskQuestion | ~270 |
| 4 | `pipeline-task-planner` | Planeja implementação de task | 🎯 Modo Plan<br>❓ AskQuestion<br>✅ Validação decisões | ~620 |
| 5 | `pipeline-plan-validator` | Melhora plano com 3 rounds | 🎯 Modo Plan<br>🔍 3 rounds análise | ~180 |
| 6 | `pipeline-task-definer` | Refina task nova (TASK=NEW) | ✅ Perguntas técnicas<br>📝 Define título/ACs/priority<br>🎯 Modo Plan<br>❓ AskQuestion | ~400 |
| 7 | `pipeline-review-backend` | Review backend | | ~396 |
| 8 | `pipeline-review-frontend` | Review frontend | | ~349 |
| 9 | `pipeline-review-documentation` | Review de documentação técnica | | — |
| 10 | `pipeline-pr-responder` | Processa reviews de PR | ✅ Lê .pr-comments.json<br>📝 Gera .pr-response-plan.md | ~369 |
| 11 | `pipeline-pr-updater` | Commit, push e atualiza PR | ✅ Filtros inteligentes<br>📝 Template estruturado | ~260 |
| 12 | `pipeline-create-technical-docs` | Gera documentação técnica consolidada | 📚 Docs<br>✅ Consolidação | — |

**Total:** ~4400+ linhas de documentação

**v1.5 Updates:**
- 🎯 Todas as skills de planejamento agora entram em **Modo Plan** automaticamente
- ❓ Skills de planejamento usam **AskQuestion** para coleta estruturada de decisões
- 🇧🇷 Reforço de comunicação em português mantido em todas as skills

---

## Instalação

### Para Novos Desenvolvedores

Execute o script de sincronização após clonar o repo:

```bash
./scripts/sync-skills.sh
```

Isso irá:
1. ✅ Copiar todas as skills `pipeline-*` para `~/.cursor/skills/`
2. ✅ Detectar mudanças (se skill já existe, atualiza apenas se diferente)
3. ✅ Mostrar resumo da sincronização

**Modo dry-run** (ver mudanças sem aplicar):

```bash
./scripts/sync-skills.sh --dry-run
```

### Script Antigo (Deprecated)

```bash
./scripts/install-pipeline-skills.sh  # Use sync-skills.sh ao invés
```

### Manualmente

Se preferir instalar manualmente:

```bash
cp -r skills/pipeline-* ~/.cursor/skills/
```

### Verificar Instalação

```bash
ls -la ~/.cursor/skills/pipeline-*
```

Você deve ver 12 diretórios `pipeline-*`:
- `pipeline-story-analyzer/`
- `pipeline-story-planner/`
- `pipeline-task-breaker/`
- `pipeline-task-planner/`
- `pipeline-plan-validator/`
- `pipeline-task-definer/`
- `pipeline-review-backend/`
- `pipeline-review-frontend/`
- `pipeline-review-documentation/`
- `pipeline-pr-responder/`
- `pipeline-pr-updater/`
- `pipeline-create-technical-docs/`

---

## Diferenças das Skills Originais

Estas skills são **versões adaptadas** das skills originais do Cursor (`skill-*`).

### Principais Diferenças

| Aspecto | Skill Original | Pipeline Skill |
|---------|---------------|----------------|
| **Output** | Opcional/flexível | **SEMPRE gera arquivo** |
| **Path** | Definido pelo usuário | **Fixo por convenção** |
| **Linters** | Roda linters | **Lê resultado** (orquestrador já rodou) |
| **Jira** | Cria issues | **Apenas propõe** (orquestrador cria) |
| **Escopo** | Pergunta sempre | **Lê do estado** (evita duplicação) |
| **Análise** | Integrada | **Separada** (pipeline-story-analyzer) |
| **Integração** | Standalone | **Otimizado para pipeline** |

### v1.4.0 — Arquitetura de Duas Fases

**Antes (v1.3):**
```
pipeline-task-breaker (antigo) → análise + proposta de tasks (tudo junto)
```

**Agora (v1.4):**
```
pipeline-story-analyzer → análise completa + validação + decisões
   ↓
pipeline-task-breaker → lê plano + propõe tasks (simplificado)
```

### Por Que Skills Separadas?

As skills originais (`skill-*`) foram projetadas para uso standalone no Cursor. O pipeline precisa de garantias específicas:

1. **Arquivos sempre criados** nos paths esperados
2. **Sem duplicação** de trabalho (linters, fetch do Jira, escopo)
3. **Paths padronizados** para integração automática
4. **Outputs estruturados** (JSON, Markdown)
5. **Compartilhamento de estado** (lê `.pipeline-state/*.json`)
6. **Contexto técnico automático** (busca em docs do projeto via `.pipeline-config.json`)

---

## Estrutura de Cada Skill

Cada skill contém:

```
pipeline-*/
└── SKILL.md      # Documentação completa (300-600 linhas)
    ├── Descrição
    ├── Input esperado (do orquestrador)
    ├── Workflow (passo a passo)
    ├── Output obrigatório (path fixo)
    ├── Diferenças da skill original
    ├── Validações
    ├── Troubleshooting
    └── Exemplos
```

---

## Como Usar

### Durante o Pipeline

O orquestrador mostra instruções claras:

```
Execute no Cursor:
  @pipeline-task-breaker quebrar <PROJECT>-XXX
  
O arquivo será criado em:
  pipelines/stories/<PROJECT>-XXX/.tasks-proposed.json
```

### Importante

❌ **NÃO use as skills originais** (`@skill-*`) durante o pipeline  
✅ **Use SEMPRE as skills pipeline** (`@pipeline-*`)

---

## Atualização

Quando as skills forem atualizadas no repo:

```bash
git pull
./scripts/sync-skills.sh
```

O script atualiza apenas skills que difiram do repo.

---

## Paths de Output

Todas as skills seguem a convenção:

```
pipelines/
├── stories/{story_key}/
│   ├── .story-plan.md                # pipeline-story-analyzer
│   └── .tasks-proposed.json          # pipeline-task-breaker
└── tasks/{task_key}/
    ├── .plan.md                      # pipeline-task-planner
    ├── .review-report.md             # pipeline-review-backend / pipeline-review-frontend
    └── .pr-response-plan.md          # pipeline-pr-responder
```

---

## Troubleshooting

### "Skill não encontrada no Cursor"

**Erro ao executar** `@pipeline-task-breaker`:
```
Skill 'pipeline-task-breaker' not found
```

**Solução:**
```bash
# Verificar se skill está instalada
ls ~/.cursor/skills/pipeline-task-breaker

# Se não existe, instalar
./scripts/sync-skills.sh
```

### "Arquivo não criado"

**Erro no pipeline:**
```
FileNotFoundError: pipelines/stories/<KEY>/.tasks-proposed.json
```

**Causa:** Skill não completou corretamente ou não usou `Write` tool.

**Solução:**
1. Verificar no chat do Cursor se skill mostrou "✅ Arquivo criado:"
2. Se não, reexecutar skill
3. Se persistir, verificar se está usando skill correta (`@pipeline-*`, não `@skill-*`)

### "Path incorreto"

**Erro:**
```
Expected: pipelines/tasks/<KEY>/.plan.md
Got: <KEY>.plan.md
```

**Causa:** Usou skill original (`@skill-*`) ao invés de pipeline (`@pipeline-*`).

**Solução:** Sempre usar `@pipeline-*`.

---

## Documentação Completa

- **Guia do pipeline:** [`docs/dev-pipeline-guide.md`](../docs/dev-pipeline-guide.md)
- **Integração:** [`docs/pipeline-skills-integration.md`](../docs/pipeline-skills-integration.md)
- **Resumo:** [`PIPELINE-SKILLS-SUMMARY.md`](../PIPELINE-SKILLS-SUMMARY.md)

---

## Manutenção

### Adicionar Nova Skill Pipeline

1. Criar em `skills/pipeline-{name}/SKILL.md`
2. Garantir geração de arquivo:
   ```python
   Write(path=expected_output, contents=result)
   print(f"✅ Arquivo criado: {expected_output}")
   ```
3. Adicionar método em `utils/skills_runner.py`
4. Integrar no fluxo do `dev_pipeline.py`
5. Testar localmente
6. Commit e outros devs fazem `./scripts/sync-skills.sh`

### Atualizar Skill Existente

1. Editar `skills/pipeline-{name}/SKILL.md`
2. Commit alterações
3. Outros devs fazem:
   ```bash
   git pull
   ./scripts/sync-skills.sh
   ```

---

## Contato

Dúvidas ou problemas com as skills pipeline? Ver documentação completa em `docs/` ou consultar o time.

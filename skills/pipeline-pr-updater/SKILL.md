---
name: pipeline-pr-updater
description: Create branch, commit, push, and open/update GitHub PR for Dev Pipeline tasks. Filters code changes, confirms with user, creates branch if needed, commits, pushes, and creates/updates PR with structured Portuguese description. Use when user wants to "commitar correções", "atualizar PR", "push changes", "publicar correções do PR", "criar PR", "publicar branch".
---

# Pipeline PR Updater

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**
**🌐 IMPORTANTE: A descrição do PR DEVE ser escrita em PORTUGUÊS (PT-BR).**

## 📁 Estrutura de Repositórios (IMPORTANTE)

**📋 Config:** Leia `.pipeline-config.json` na raiz do repo `dev-pipeline` para descobrir repos, paths de docs e projeto atual.

**Contextos de uso:**

### Quando chamada pelo ORQUESTRADOR (Pipeline):
- **Working directory:** o workspace root do Cursor (diretório raiz com todos os repos)
- **Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo dev-pipeline (contem .pipeline-config.json)
- **Repositórios disponíveis como subdiretórios:**
  - Consulte `repositories` em `.pipeline-config.json` para paths dos repos
  - Cada repo tem `local_path`, `type` e `tech_stack`

**⚠️ Ao fazer commit/push:** Certifique-se de estar no repositório correto (onde o PR foi criado). Consulte `local_path` de cada repo no `.pipeline-config.json`.

### Quando usada PONTUALMENTE (standalone):
- **Working directory:** Dentro de um repo específico (onde você vai fazer commit/push)
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

**Diferenças da skill original:**
- ✅ Integrado com pipeline state (lê task_key, story_key)
- ✅ Usa convenções de commit do projeto
- ✅ Cria branch seguindo padrão `<type>/<TASK-KEY>/<user>` (ex: `feat/PROJ-655/{user}`)
- ✅ Cria PR ou atualiza PR existente
- ✅ Descrição do PR sempre em PORTUGUÊS (PT-BR)
- ✅ Output estruturado para o orquestrador

---

## Convenção de Branch (OBRIGATÓRIO)

**Formato:** `<type>/<TASK-KEY>/<user>`

- `<type>`: tipo da mudança (`feat`, `fix`, `refactor`, `chore`, `perf`, `test`)
- `<TASK-KEY>`: código da task Jira (ex: `PROJ-655`)
- `<user>`: iniciais/username do desenvolvedor (ex: iniciais do nome)

**Exemplos:**
- `feat/PROJ-655/{user}` -- nova feature
- `fix/PROJ-650/{user}` -- bug fix
- `refactor/PROJ-660/{user}` -- refatoração

**Como determinar o type:**
- Analise o diff e o contexto da task
- Na dúvida, use `feat` para features/melhorias e `fix` para correções

**Como determinar o user:**
- Use `git config user.name` ou extraia das iniciais do email com `git config user.email`
- Fallback: perguntar ao usuário

---

## Input Esperado

Usuário fornece:
- **TASK** key (ex: `PROJ-645`)
- Ou contexto atual (branch já está no PR)

O agente deve inferir:
- Branch atual (`git rev-parse --abbrev-ref HEAD`)
- PR number (via `gh pr view`), se existir
- Story key (se aplicável)

---

## Workflow

```
Step 1: Validate → Step 2: Create Branch (se necessário) → Step 3: Filter & Confirm → Step 4: Commit → Step 5: Push → Step 6: Create/Update PR
```

---

## Step 1: Validate Context

Run in parallel:

```bash
git status --short
git rev-parse --abbrev-ref HEAD
git log --oneline -3
gh auth status
gh pr view --json number,url,title,body 2>/dev/null || echo "NO_PR"
git config user.name
```

**Verificar:**
- Há mudanças para commitar
- GitHub CLI autenticado
- Se branch atual é `main`/`master` -> precisa criar branch nova (Step 2)
- Se branch atual já tem PR -> pular Step 2, ir para Step 3

---

## Step 2: Create Branch (se necessário)

**Criar branch quando:**
- Branch atual é `main` ou `master`
- Ou branch atual não segue o padrão `<type>/<TASK-KEY>/<user>`

**Determinar nome da branch:**

1. Identificar `<type>` analisando o diff (`git diff --stat`):
   - Novos arquivos / features -> `feat`
   - Correções de bugs -> `fix`
   - Reestruturação sem mudança de comportamento -> `refactor`
   - Config, deps, cleanup -> `chore`

2. Identificar `<user>`:
   ```bash
   git config user.name | tr '[:upper:]' '[:lower:]' | tr ' ' '-'
   ```
   Ou usar iniciais do nome (ex: "Nome Sobrenome" -> "nsobrenome")

3. Criar branch:
   ```bash
   git checkout -b <type>/<TASK-KEY>/<user>
   ```

**Exemplo:**
```bash
git checkout -b feat/PROJ-655/{user}
```

---

## Step 3: Filter & Confirm Files

### Filtering Rules

**EXCLUIR por padrão:**
- Documentation: `*.md`, `docs/`, `README*`
- Pipeline internal: `.pipeline-state/`, `pipelines/tasks/`, `pipelines/stories/`, `logs/`
- Configuration: `.env*`, `.cursor/rules/`, `*.mdc`, `.gitignore`
- Credentials: Auth files, secrets
- Scripts: Utility scripts (`scripts/`, standalone analysis)
- Generated: Build artifacts, `dist/`, `.next/`, `node_modules/`

**INCLUIR por padrão:**
- Source code: `.py`, `.ts`, `.tsx`, `.js`, `.jsx`
- Tests: `test_*.py`, `*.test.ts`, `*.spec.ts`
- Config que afeta behavior: `pyproject.toml`, `package.json`, `tsconfig.json`
- Type definitions: `.pyi`, `.d.ts`
- Styles: `.css`, `.scss`

### User Confirmation

**Mostrar ao usuário:**

```markdown
📝 Arquivos para commit (após filtros):

✅ Serão commitados:
  M  app/service/order/order.py
  M  app/handlers/orders.py
  A  app/constants/order.py
  M  tests/unit/test_order.py

⏭️ Excluídos (não serão commitados):
  ?? docs/notas.md
  ?? .cursor/rules/custom.mdc
  ?? logs/pipeline-PROJ-645.log

Deseja modificar essa lista? (s/N)
```

**Se usuário responder SIM:**
- Permitir adicionar ou remover arquivos
- Re-confirmar antes de prosseguir

**Se usuário responder NÃO ou dar Enter:**
- Stage files automaticamente
- Prosseguir para Step 3

---

## Step 4: Commit Changes

### Analyze Diff

```bash
git diff --staged
```

**Identificar:**
- Natureza das mudanças (fix, feat, refactor, chore)
- Escopo (module/component principal afetado)
- Issue key (PROJ-XXX) se não tiver no contexto

### Draft Commit Message

**Formato padrão de commit:**

```
<type>(<scope>): <description> (<ISSUE-KEY>)

- Detail 1
- Detail 2
```

**Types:**
- `fix`: Correções de bugs
- `feat`: Novas funcionalidades
- `refactor`: Refatoração sem mudança de comportamento
- `chore`: Config, dependências, cleanup
- `perf`: Melhorias de performance
- `test`: Adicionar/atualizar testes

**Exemplo:**

```
fix(order): corrigir validação de inventário (PROJ-645)

- Adicionar tratamento de erro DynamoDB no handler de pedidos
- Extrair constante MAX_DATA_SIZE para order constants
- Corrigir ordem de imports em orders.py
- Atualizar testes para novos cenários de erro
```

### Commit

```bash
git commit -m "$(cat <<'EOF'
fix(order): corrigir validação de inventário (PROJ-645)

- Adicionar tratamento de erro DynamoDB no handler de pedidos
- Extrair constante MAX_DATA_SIZE para order constants
- Corrigir ordem de imports em orders.py

EOF
)"
```

### Handle Commit Failures

**Pre-commit hook falha:**
- Corrigir issues (linter, formatação)
- Criar NOVO commit (nunca `--amend` a menos que explicitamente solicitado)

**Nenhuma mudança staged:**
- Confirmar com usuário: "Nenhum arquivo staged. Deseja adicionar arquivos?"

---

## Step 5: Push Changes

```bash
git push -u origin HEAD
```

**Requires:** `required_permissions: ["all"]` or `["git_write"]`

### Handle Push Failures

| Erro | Solução |
|------|---------|
| Behind remote | `git pull --rebase origin $(git branch --show-current)` e tentar novamente |
| Rejected (force needed) | Perguntar: "Push foi rejeitado. Fazer force push? (não recomendado)" |
| No upstream | `git push -u origin HEAD` |

---

## Step 6: Create or Update PR

### Verificar se PR já existe

```bash
gh pr view --json number,url,title,body 2>/dev/null
```

### Se NÃO existe PR -> Criar

**Título do PR:** `<type>(<scope>): <descrição curta> (<TASK-KEY>)`

**Descrição do PR (SEMPRE em PORTUGUÊS):**

```bash
gh pr create --title "<type>(<scope>): <descrição> (<TASK-KEY>)" --body "$(cat <<'EOF'
## Resumo
- (Mudança 1)
- (Mudança 2)
- (Mudança 3)

## Detalhes técnicos
- (Explicação técnica das mudanças mais relevantes)
- (Trade-offs ou decisões de design)

## Plano de testes
- [ ] (Passo de verificação 1)
- [ ] (Passo de verificação 2)

---
**Relacionado:** <TASK-KEY>
EOF
)"
```

**Confirmar com o usuário antes de criar:**

```
📝 Criar PR

Título: feat(order): Adicionar validação de inventário (PROJ-655)

Descrição:
## Resumo
- Adicionar validação de estoque antes de criar pedido
- Implementar handler de erro para DynamoDB

Deseja criar o PR? (S/n)
```

### Se JÁ existe PR -> Atualizar

```bash
gh pr view --json number,url,title,body
```

**Template de atualização (SEMPRE em PORTUGUÊS):**

```bash
gh pr edit <pr-number> --body "$(cat <<'EOF'
## Resumo
- (Mudança 1 original)
- (Mudança 2 original)

## Alterações nesta atualização
- (O que foi corrigido/adicionado no último commit)
- (Comentário de review endereçado de @reviewer)

## Plano de testes
- [ ] (Passo de verificação 1)
- [ ] (Passo de verificação 2)

---
**Relacionado:** <TASK-KEY>
EOF
)"
```

**Mostrar ao usuário antes de atualizar:**

```
📝 Atualizar descrição do PR

Título atual: "feat(order): Adicionar validação (PROJ-655)"
Corpo atual: (mostrar existente)

Atualização sugerida: (mostrar novo corpo)

Deseja atualizar a descrição do PR? (S/n)
```

### Resultado

```
✅ PR criado/atualizado com sucesso!
🔗 https://github.com/org/repo/pull/123
```

---

## Integração com o Pipeline

Essa skill é usada na etapa **GIT_PUBLISH** do pipeline:

```
1. Pipeline detecta mudanças para publicar
2. @pipeline-pr-updater PROJ-645  →  cria branch + commit + push + PR
3. Pipeline avança para AGUARDANDO_MERGE
```

Também é o **passo natural após** executar `pipeline-pr-responder`:

```
1. @pipeline-pr-responder PROJ-645  →  gera plano de correções
2. (Usuário implementa ou pede implementação)
3. (Review das mudanças com pipeline-review-backend / pipeline-review-frontend)
4. @pipeline-pr-updater PROJ-645  →  commit + push + atualiza PR
```

---

## Error Handling

| Erro | Ação |
|------|------|
| Branch em main/master | Criar branch nova seguindo padrão `<type>/<TASK-KEY>/<user>` |
| Nenhuma mudança para commit | Perguntar: "Nenhuma mudança detectada. Verificar git status?" |
| Push rejeitado | Pull com rebase, tentar novamente |
| Pre-commit hook falha | Corrigir issues, commitar novamente (NOVO commit) |
| GH CLI não autenticado | Orientar: `gh auth login` |

---

## Success Criteria

- [ ] Branch criada seguindo padrão `<type>/<TASK-KEY>/<user>` (se necessário)
- [ ] Arquivos filtrados e confirmados com usuário
- [ ] Commit criado com mensagem estruturada
- [ ] Push realizado com sucesso
- [ ] PR criado/atualizado com descrição em PORTUGUÊS
- [ ] Usuário informado da URL do PR

---

## Troubleshooting

### "Muitos arquivos filtrados"

**Causa:** Filtros muito agressivos excluíram código válido.

**Solução:**
- Mostrar lista completa ao usuário
- Perguntar: "Algum desses arquivos deveria ser commitado?"
- Ajustar filtros manualmente

### "Commit message não segue padrão"

**Causa:** Repo tem convenção específica (Conventional Commits).

**Solução:**
- Ler últimos 3 commits: `git log --oneline -3`
- Seguir padrão detectado
- Validar formato antes de commitar

### "PR description muito longa"

**Causa:** Muitas mudanças no update.

**Solução:**
- Agrupar mudanças relacionadas
- Focar em high-level summary
- Detalhe técnico fica no código/comments

---

## Checklist Final

- [x] Branch atual tem PR aberto
- [x] Mudanças filtradas e confirmadas
- [x] Commit criado com mensagem estruturada
- [x] Push realizado com sucesso
- [x] PR description atualizada
- [x] Usuário informado do resultado

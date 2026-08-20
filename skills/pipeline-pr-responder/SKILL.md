---
name: pipeline-pr-responder
description: Processa comentários de PR para o Dev Pipeline Orchestrator. Lê `.pr-comments.json`, avalia relevância, cria plano de correções, e SEMPRE gera `.pr-response-plan.md`. Use APENAS quando chamado pelo orquestrador em PR_REVIEW_CYCLE.
---

# Pipeline PR Responder

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

## 📁 Estrutura de Repositórios (IMPORTANTE)

**📋 Config:** Leia `.pipeline-config.json` na raiz do repo `dev-pipeline` para descobrir repos, paths de docs e projeto atual.

**Contextos de uso:**

### Quando chamada pelo ORQUESTRADOR (Pipeline):
- **Working directory:** o workspace root do Cursor (diretório raiz com todos os repos)
- **Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo dev-pipeline (contem .pipeline-config.json)
- **Repositórios disponíveis como subdiretórios:**
  - Consulte `repositories` em `.pipeline-config.json` para paths dos repos
  - Cada repo tem `local_path`, `type` e `tech_stack`

**⚠️ Ao explorar código:** Use paths relativos. Consulte `local_path` de cada repo no `.pipeline-config.json`.

### Quando usada PONTUALMENTE (standalone):
- **Working directory:** Dentro de um repo específico
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-pr-responder pipelines/tasks/{task_key}/.pr-comments.json
```

**O caminho relativo deve ser interpretado como:**
```
{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.pr-comments.json
```

**REGRA:** O path relativo `pipelines/tasks/...` é relativo ao repo `dev-pipeline/`, partindo do workspace root.

**SEMPRE use o caminho COMPLETO ao chamar a ferramenta Read:**
```python
Read(path="{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.pr-comments.json")
```

---

**Diferenças da skill original:**
- ✅ Lê `.pr-comments.json` (comentários já fetched)
- ✅ **SEMPRE gera** `.pr-response-plan.md` no caminho esperado
- ✅ Não fetcha PR nem comentários (orquestrador já fez)
- ✅ Output estruturado em markdown
- ✅ **Invoca pipeline-plan-validator automaticamente** (Step 5)

---

## Input Esperado

O orquestrador já forneceu:
- **PR comments file**: `.pr-comments.json` com:
  ```json
  {
    "pr_number": 123,
    "pr_url": "https://github.com/...",
    "comments": [
      {
        "id": 456,
        "body": "...",
        "path": "app/handlers/orders.py",
        "line": 45,
        "reviewer": "reviewer-name"
      }
    ]
  }
  ```

**Não** rodar `gh pr view` ou `gh api` novamente.

---

## Workflow (adaptado)

```
Step 1: Ler .pr-comments.json → Step 1.5: Entender escopo do PR → Step 2: Avaliar relevância →
Step 3: Criar plano → Step 4: GERAR MARKDOWN → Step 5: Melhorar Plano Automaticamente (pipeline-plan-validator)
```

---

## Step 1: Ler Comentários do PR

```python
import json

with open(pr_comments_file) as f:
    data = json.load(f)

pr_number = data["pr_number"]
pr_url = data["pr_url"]
comments = data["comments"]
```

**Mostrar resumo:**
```
📝 PR Review Comments
PR: #123 (https://github.com/...)
Total comments: 8
```

---

## Step 1.5: Entender Escopo do PR

**Obrigatório antes de avaliar comentários.**

Buscar contexto do PR para validar se comentários são compatíveis:

### A. Ler PR description

```bash
# Orquestrador já salvou em .pr-comments.json (adicionar campo "pr_body")
pr_description = data.get("pr_body", "")
```

**Extrair:**
- Objetivo principal (title/summary)
- Requisitos explícitos
- Test plan
- Decisões de design mencionadas

### B. Procurar docs relacionadas

Buscar em `docs/` ou `pipelines/` (stories e tasks) por arquivos relacionados:
- RFC, spec, plan
- Grep por issue/ticket number (ex: `PROJ-123`)

**Usar esse contexto no Step 2** para identificar comentários que:
- ❌ Contradizem requisitos explícitos
- ❌ Sugerem mudanças fora do escopo
- ❌ Revertem decisões de design documentadas

---

## Step 2: Avaliar Relevância

**PRIMEIRO:** Usar contexto do **Step 1.5** (requisitos do PR, descrição, test plan) para identificar comentários fora de escopo.

Para cada comentário, classificar como:

| Classification | Criteria | Action |
|----------------|----------|--------|
| **✅ VALID** | Technical issue, bug, security, maintainability | Include in plan |
| **✅ VALID-OPTIONAL** | Code quality, non-critical refactor | Include with lower priority |
| **⏭️ SKIP** | Already fixed, not applicable | Document and skip |
| **⏭️ SKIP-OUT-OF-SCOPE** | Contradicts PR requirements (Step 1.5), suggests reverting intentional changes, or proposes unrelated refactoring | Document with PR requirement reference |
| **⏭️ OVERENGINEERING** | Adds complexity for rare edge case with minimal impact | Reject with reasoning |
| **❓ UNCLEAR** | Ambiguous, needs clarification | Ask user |

### Overengineering Detection

Rejeitar comentários que sugerem mudanças onde **cost > benefit:**

**Cost > Benefit:**
- Adds conditional logic / new state for extremely rare scenario
- Scenario has minimal user impact when it happens
- Fix is more expensive to maintain than the problem it solves

**Exemplos para REJEITAR:**
- "Preserve selection when all requests fail" → Rare + user would investigate errors anyway
- "Add loading state for 50ms operation" → No perceivable UX benefit
- "Handle theoretical race in UI that can't happen due to API constraints"

**Exemplos para ACEITAR:**
- "Prevent selecting wrong order due to non-unique ID" → Critical data integrity
- "Block double-submit" → Common user behavior, causes real problems
- "Add loading state for 2s+ operation" → Perceivable UX improvement

### Out-of-Scope Validation

**PRIMEIRO:** Usar contexto do **Step 1.5** (requisitos do PR, descrição, test plan) para identificar comentários fora de escopo.

**Exemplos de comentários OUT-OF-SCOPE:**
- **Exemplo 1:** PR says "Removida opção 'Todos os grupos'" → Comment asks to restore it → **SKIP-OUT-OF-SCOPE** (contradicts requirement)
- **Exemplo 2:** PR implements mandatory filter → Comment suggests making it optional → **SKIP-OUT-OF-SCOPE** (reverses core requirement)
- **Exemplo 3:** PR focuses on orders page → Comment suggests refactoring unrelated auth module → **SKIP-OUT-OF-SCOPE** (not in scope)
- Comentário: "Restore bulk delete" → PR description: "Remove bulk delete as per product decision"
- Comentário: "Use Redux instead of Context" → PR: "Migrating from Redux to Context"
- Comentário: "Refactor X service" → PR: "Add field Y to orders" (unrelated)

**Marcar:** `SKIP-OUT-OF-SCOPE` com referência ao requisito do PR.

### Already-Fixed Comments

**Verificar se o comentário já foi corrigido:**
- Ler arquivo atual na linha comentada (usando Read tool)
- Comparar com a descrição do comentário
- Se o fix já está presente no branch atual, classificar como **⏭️ SKIP**
- Documentar: "Already fixed in current branch"

---

## Step 3: Criar Plano de Correções

Para comentários **VALID** e **VALID-OPTIONAL**, agrupar por arquivo/área e criar plano.

**Estrutura:**

```markdown
# PR Response Plan

## PR Context
- **PR:** #123 — Add hr_modify_employee flow
- **URL:** https://github.com/...
- **Total comments:** 8
- **Requires changes:** 5 VALID, 2 OPTIONAL
- **Skipped:** 1 (out-of-scope)

## Comments Evaluation

### ✅ VALID (5 comments)

#### 1. Comment #456 (reviewer-name)
**File:** `app/handlers/orders.py:45`
**Issue:** Missing error handling for DynamoDB failure
```python
# Current:
table.put_item(Item=item)

# Should:
try:
    table.put_item(Item=item)
except ClientError as e:
    logger.error(f"DynamoDB error: {e}")
    raise HTTPException(status_code=500, detail="Failed to create order")
```
**Action:** Add try/except block with logging + HTTPException

#### 2. Comment #457 (reviewer-name)
**File:** `app/service/order.py:78`
**Issue:** Hardcoded constant should be extracted
```python
# Current:
if len(data) > 100:  # Magic number

# Should:
MAX_DATA_SIZE = 100  # In constants.py
if len(data) > MAX_DATA_SIZE:
```
**Action:** Extract constant to `app/constants/order.py`

### ✅ VALID-OPTIONAL (2 comments)

#### 3. Comment #458 (reviewer-name)
**File:** `app/handlers/orders.py:12`
**Issue:** Import order (minor style)
**Action:** Reorder imports (stdlib → third-party → app)

### ⏭️ SKIPPED (1 comment)

#### 4. Comment #459 (reviewer-name — SKIP-OUT-OF-SCOPE)
**File:** `src/components/OrdersTable.tsx`
**Issue:** "Add bulk actions back"
**Reason:** PR description explicitly states: "Removing bulk actions as per product decision PROJ-400"
**Action:** Reply: "This was intentionally removed per PROJ-400. Bulk actions will be redesigned in Q2."

## Implementation Plan

### Phase 1: Critical Fixes (VALID)
1. **app/handlers/orders.py**
   - Line 45: Add DynamoDB error handling (try/except + logging)
   - Line 12: Fix import order

2. **app/service/order.py**
   - Line 78: Extract `MAX_DATA_SIZE = 100` to constants

3. **app/constants/order.py**
   - Add new constant `MAX_DATA_SIZE`

### Phase 2: Optional Improvements (VALID-OPTIONAL)
4. **src/types/order.ts**
   - Replace `any` with specific type

### Phase 3: Reply to Skipped Comments
5. Post reply to comment #459 explaining scope decision

## Files Affected
- `app/handlers/orders.py` (modify)
- `app/service/order.py` (modify)
- `app/constants/order.py` (modify)
- `src/types/order.ts` (modify — optional)

## Estimated Effort
- Phase 1 (VALID): ~20 minutes
- Phase 2 (OPTIONAL): ~10 minutes
- Total: ~30 minutes

## Success Criteria
- [ ] All VALID comments addressed
- [ ] Tests still passing
- [ ] Linters clean
- [ ] Reviewer approved changes
```

---

## Step 4: GERAR MARKDOWN (OBRIGATÓRIO)

### 4.1 Determinar caminho

```python
story_key = "PROJ-436"
task_key = "PROJ-437"
output_file = f"pipelines/tasks/{task_key}/.pr-response-plan.md"
```

### 4.2 Criar arquivo

```python
Write(
    path=output_file,
    contents=plan_markdown
)
```

### 4.3 Confirmar criação

```
✅ Arquivo criado: pipelines/tasks/PROJ-437/.pr-response-plan.md

📝 Resumo:
- 5 VALID (must fix)
- 2 VALID-OPTIONAL
- 1 SKIP-OUT-OF-SCOPE

Arquivos afetados: 4
Tempo estimado: ~30 min

Pressione qualquer tecla...
```

---

## Diferenças da Skill Original

| Aspecto | Skill Original | Pipeline Version |
|---------|---------------|------------------|
| **Input** | Fetcha PR via `gh` | Lê `.pr-comments.json` |
| **Fetch comments** | `gh api ...` | **NÃO fetcha** (orquestrador já fez) |
| **Output** | Cria plano com CreatePlan | **SEMPRE gera arquivo markdown** |
| **Path** | Flexível (Plan mode) | **Fixo**: `pipelines/tasks/{task_key}/.pr-response-plan.md` |
| **pipeline-plan-validator** | Roda após CreatePlan | **Roda automaticamente** (Step 5) |

---

## Validações Finais

- [ ] `.pr-comments.json` foi lido corretamente
- [ ] PR context foi entendido (description + docs)
- [ ] Comentários foram avaliados (VALID/SKIP/OVERENGINEERING)
- [ ] Plano de correções foi criado
- [ ] **Arquivo `.pr-response-plan.md` foi CRIADO**
- [ ] Path correto: `pipelines/tasks/{task_key}/.pr-response-plan.md`
- [ ] Arquivos afetados listados
- [ ] Tempo estimado fornecido

---

## Troubleshooting

### "Nenhum comentário para processar"

**Causa:** `.pr-comments.json` com array vazio.

**Solução:**
```
⚠️ Nenhum comentário encontrado no PR.
Criando plano vazio...
```

Gerar arquivo markdown mesmo assim:
```markdown
# PR Response Plan

**PR:** #123  
**Status:** ✅ No comments to address

All feedback was positive or already addressed.
```

### "Comentário ambíguo"

**Causa:** Comentário não tem clareza suficiente.

**Solução:**
- Classificar como `❓ UNCLEAR`
- Adicionar ao plano com nota: "Needs clarification from reviewer"
- Sugerir reply: "Could you clarify what you mean by...?"

---

## Next Steps (após gerar o plano)

Workflow completo de correção de PR reviews:

```
1. @pipeline-pr-responder PROJ-645
   → Gera .pr-response-plan.md com avaliação e plano

2. Implementar correções (manualmente ou com AI)
   → Aplicar mudanças conforme o plano

3. Review das correções:
   - Backend: @pipeline-review-backend
   - Frontend: @pipeline-review-frontend
   → Valida contra padrões do projeto

4. @pipeline-pr-updater PROJ-645
   → Commit + push + atualiza descrição do PR
```

**Automação completa:**
- Avaliação inteligente (out-of-scope, overengineering, already-fixed)
- Plano estruturado em markdown
- Review de qualidade (pipeline-review-backend / pipeline-review-frontend)
- Commit e atualização de PR automatizados (pipeline-pr-updater)

---

## Step 5: Melhorar Plano Automaticamente (pipeline-plan-validator)

**⚡ AUTOMATIZAÇÃO:** Após criar o plano (Step 4), chamar automaticamente a skill de melhoria.

### 5.1. Informar usuário

```python
from pathlib import Path
import json

# ============================================================
# CONFIG CENTRALIZADO - Lê paths de .pipeline-config.json
# ============================================================
def get_pipeline_paths():
    """Lê paths do config centralizado."""
    config_path = Path(".pipeline-config.json")
    if not config_path.exists():
        # Fallback v1 se config não existir
        return {
            "stories_dir": "pipelines/stories",
            "tasks_dir": "pipelines/tasks"
        }
    config = json.loads(config_path.read_text())
    return config["paths"]

paths_config = get_pipeline_paths()
STORIES_DIR = paths_config["stories_dir"]
TASKS_DIR = paths_config["tasks_dir"]
# ============================================================

plan_file = Path(f"{TASKS_DIR}/{task_key}/.pr-response-plan.md")

print("\n" + "="*60)
print("✅ PLANO DE RESPOSTA CRIADO")
print("="*60)
print(f"📄 Arquivo: {plan_file}")
print(f"📊 Tamanho: {plan_file.stat().st_size} bytes")
print("\n🔄 Executando pipeline-plan-validator automaticamente...")
print("   (3 rounds de análise crítica)")
print("="*60 + "\n")
```

### 5.2. Invocar skill automaticamente

Executar automaticamente (sem precisar do usuário):

```
@pipeline-plan-validator melhorar pipelines/tasks/{task_key}/.pr-response-plan.md
```

**O que essa skill fará:**
- Round 1: Perspectiva do implementador (gaps, arquivos, dependências)
- Round 2: Perspectiva do tech lead (arquitetura, riscos, manutenção)
- Round 3: Perspectiva do advogado do diabo (edge cases, falhas)
- Aplicará melhorias in-place no arquivo

### 5.3. Confirmar sucesso

Após a skill `pipeline-plan-validator` concluir:

```python
print("\n" + "="*60)
print("✅ PLANO MELHORADO (3 rounds concluídos)")
print("="*60)
print(f"📄 Arquivo final: {plan_file}")
print("\n📌 Próximos passos:")
print("   → Revisar o plano (pipeline-plan-validator já rodou)")
print("   → Implementar correções conforme o plano")
print("   → Review das correções (pipeline-review-backend/frontend)")
print("="*60)
```

**Resultado final:** Plano robusto e revisado; **implementação segue após confirmação explícita** de que pode prosseguir.

---

## Checklist Final

- [x] Comentários foram lidos (`.pr-comments.json`)
- [x] PR context foi entendido
- [x] Comentários foram classificados (VALID/SKIP/etc)
- [x] Plano de correções foi criado
- [x] **Arquivo `.pr-response-plan.md` CRIADO**
- [x] **pipeline-plan-validator foi invocado automaticamente** (Step 5)
- [x] Plano foi melhorado (3 rounds de análise)
- [x] Usuário informado do resumo

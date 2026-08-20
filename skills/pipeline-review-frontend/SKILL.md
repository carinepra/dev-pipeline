---
name: pipeline-review-frontend
description: Review de código frontend para o Dev Pipeline Orchestrator. Lê `.review-data.json` gerado pelo orquestrador, aplica checklists do projeto, e SEMPRE gera `.review-report.md`. Use APENAS quando chamado pelo orquestrador em REVIEW_CHANGES.
---

# Pipeline Review Frontend

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

## 📁 Estrutura de Repositórios (IMPORTANTE)

**Contextos de uso:**

### Quando chamada pelo ORQUESTRADOR (Pipeline):
- **Working directory:** o workspace root do Cursor (diretório raiz)
- **Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo dev-pipeline (contem .pipeline-config.json)
- **Código frontend:** Consulte `local_path` do repo frontend em `.pipeline-config.json`
- **Explore o src/ do repo** conforme path do config

### Quando usada PONTUALMENTE (standalone):
- **Working directory:** Dentro do repo frontend (ver `local_path` no `.pipeline-config.json`)
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-review-frontend pipelines/tasks/{task_key}/.review-data.json
```

**O caminho relativo deve ser interpretado como:**
```
{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.review-data.json
```

**REGRA:** O path relativo `pipelines/tasks/...` é relativo ao repo `dev-pipeline/`, partindo do workspace root.

**SEMPRE use o caminho COMPLETO ao chamar a ferramenta Read:**
```python
Read(path="{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.review-data.json")
```

---

**Diferenças da skill original:**
- ✅ Lê `.review-data.json` (linters + diff já coletados)
- ✅ **SEMPRE gera** `.review-report.md` no caminho esperado
- ✅ Não roda linters (orquestrador já rodou)
- ✅ Aplica regras do projeto (`.cursor/rules/*.mdc`)

---

## Input Esperado

O orquestrador já forneceu:
- **Review data file**: `.review-data.json` com:
  - `repo`: "frontend"
  - `linters`: {errors: [...], warnings: [...], summary: {...}}
  - `diff`: {files_changed: [...], diff_staged: "...", diff_unstaged: "...", stats: {...}}

**Se o arquivo não existir:** gerá-lo automaticamente via Shell com `git diff` e linters — **NÃO perguntar ao usuário**.

```bash
# Coletar diff (rodar no repo frontend: white-app)
git -C {WORKSPACE_ROOT}/white-app diff
git -C {WORKSPACE_ROOT}/white-app diff --cached

# Linters
cd {WORKSPACE_ROOT}/white-app && npx eslint --format json src/
cd {WORKSPACE_ROOT}/white-app && npx tsc --noEmit
```

Salvar resultado em `{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.review-data.json` e prosseguir.

---

## Workflow (adaptado)

```
Step 0: Ler regras do projeto → Step 1: Ler (ou gerar) .review-data.json → Step 2: Agrupar arquivos →
Step 3: Review por grupo → Step 4: GERAR RELATÓRIO
```

---

## Step 0: Ler Regras do Projeto

Ler checklists de `.cursor/rules/*.mdc`:

- `.cursor/rules/geral.mdc` — Regras gerais
- `.cursor/rules/components.mdc` — Components React
- `.cursor/rules/hooks.mdc` — Custom hooks
- `.cursor/rules/services.mdc` — API services
- `.cursor/rules/tables.mdc` — TanStack Table

Usar essas regras nos checks de cada layer.

---

## Step 1: Ler Dados do Review

```python
import json

with open(review_data_file) as f:
    data = json.load(f)

linters = data["linters"]
diff_data = data["diff"]
```

**Mostrar resumo:**
```
📊 Review Frontend
Arquivos modificados: 8
Linter errors: 3
Linter warnings: 12
Diff: +280 -45 linhas
```

---

## Step 2: Agrupar Arquivos por Domínio

Agrupar por feature/domínio:

```
Exemplos:
  orders-page: [OrdersPage.tsx, OrdersFilters.tsx, useOrders.ts]
  order-detail: [OrderDetail.tsx, OrderActions.tsx]
  order-table: [OrdersTable.tsx, OrdersColumns.tsx]
  shared: [Button.tsx, Modal.tsx, types.ts]
```

Classificar cada arquivo por **layer**:

| Layer | Path pattern |
|-------|-------------|
| page | `src/app/**/*Page.tsx` |
| component | `src/components/**/*.tsx` |
| hook | `src/hooks/**/*.ts` |
| service | `src/services/**/*.ts` |
| type | `src/types/**/*.ts` |
| util | `src/utils/**/*.ts` |
| constant | `src/constants/**/*.ts` |
| context | `src/contexts/**/*.tsx` |
| test | `*.test.tsx`, `*.test.ts` |

---

## Step 3: Review Por Grupo

Para cada grupo:

### 3a. Ler Contexto

1. **Ler git diff** (`diff_data["diff_staged"]` + `diff_data["diff_unstaged"]`)
2. **Ler arquivos completos** quando necessário
3. Para arquivos novos, ler inteiro

### 3b. Aplicar Checks

**Ordem:**
1. **Universal checks** (todos arquivos)
2. **Layer-specific checklist** (regras do `.cursor/rules/`)
3. **Pattern verification** (componentes/hooks novos)
4. **Cross-file consistency** (por grupo)
5. **React-specific checks** (hooks, lifecycle, state)
6. **Accessibility checks** (a11y)
7. **Performance checks** (re-renders, memoization)

### Universal Checks (Frontend)

- [ ] Import order: React → libs → types → components → utils → constants
- [ ] No commented-out code
- [ ] No `console.log()` (use logger ou remover)
- [ ] No hardcoded URLs/tokens
- [ ] Naming: components=PascalCase, hooks=use*, utils=camelCase, UPPER_SNAKE_CASE
- [ ] No unnecessary comments
- [ ] TypeScript strict mode (no `any` desnecessário)

### Layer-Specific Checks

**Components (`.cursor/rules/components.mdc`):**
- [ ] Props definidas com interface (não type inline)
- [ ] PropTypes ou TypeScript interface
- [ ] Estado local mínimo (delegar ao hook)
- [ ] Event handlers prefixados com `handle*`
- [ ] Renderização condicional clara (não ternários aninhados)
- [ ] Acessibilidade (aria-*, role, alt, labels)

**Hooks (`.cursor/rules/hooks.mdc`):**
- [ ] Nome começa com `use`
- [ ] Retorno consistente (array ou object, não misto)
- [ ] Dependencies de `useEffect` completas
- [ ] Cleanup em `useEffect` quando necessário
- [ ] Não chama outros hooks condicionalmente

**Services (`.cursor/rules/services.mdc`):**
- [ ] Usa TanStack Query (`useQuery`, `useMutation`)
- [ ] Error handling com try/catch
- [ ] Typing completo (request + response)
- [ ] Base URL vem de env var
- [ ] Não mistura lógica de negócio (delegar ao hook)

**Tables (`.cursor/rules/tables.mdc`):**
- [ ] Usa TanStack Table
- [ ] Columns definidas fora do component (memoizadas)
- [ ] Sorting/filtering/pagination configurados
- [ ] Loading e empty states
- [ ] Tipos para row data

### Pattern Verification (componentes/hooks novos)

Para cada componente/hook novo:
1. **Encontrar referência:** componente/hook similar
2. **Comparar:**
   - Imports (ordem? aliases?)
   - Props interface (naming? required vs optional?)
   - Estado (useState vs useReducer? escopo?)
   - Effects (dependencies? cleanup?)
   - Return (formato consistente?)
3. **Marcar divergências:** WARN ou FAIL

### React-Specific Checks

- [ ] `useEffect` sem dependencies array? (re-run a cada render)
- [ ] State updates em loop? (infinite re-render)
- [ ] Props drilling profundo? (considerar context ou state management)
- [ ] Componente muito grande? (>300 linhas → split)
- [ ] Lógica complexa inline? (extrair para hook)

### Accessibility (A11y)

- [ ] Buttons têm `aria-label` quando sem texto
- [ ] Inputs têm `<label>` associada
- [ ] Imagens têm `alt` descritivo
- [ ] Modals têm `role="dialog"` e `aria-modal`
- [ ] Keyboard navigation funciona (`tabIndex`, `onKeyDown`)

### Performance

- [ ] Lists têm `key` única (não index)
- [ ] Componentes pesados são memoizados (`React.memo`, `useMemo`)
- [ ] Callbacks são memoizados (`useCallback`) quando passados como props
- [ ] Re-renders desnecessários? (props mudam mesmo valor)

### Edge Cases (obrigatório)

- [ ] Loading state (dados ainda carregando)
- [ ] Error state (requisição falhou)
- [ ] Empty state (lista vazia, sem dados)
- [ ] Null/undefined checks (`.?` ou guard)
- [ ] Array vazio vs undefined

### 3c. Registrar Findings

Severity: **FAIL** / **WARN** / **PASS** / **A11Y** / **PERF**

---

## Step 4: GERAR RELATÓRIO (OBRIGATÓRIO)

### 4.1 Estrutura do Relatório (Frontend)

```markdown
# Code Review Report — Frontend

**Task:** PROJ-437  
**Date:** 2026-03-25  
**Reviewer:** Pipeline (Automated)

## Summary

- **Files reviewed:** 8
- **FAIL:** 1
- **A11Y:** 2
- **PERF:** 1
- **WARN:** 7
- **PASS:** 15

## Critical Issues (FAIL)

### 1. [FAIL] src/components/OrderDetail.tsx
**Issue:** `useEffect` sem dependencies array
```tsx
useEffect(() => {
  fetchOrderDetails();  // ← Re-run a cada render (infinite loop)
});
```
**Sugestão:** Adicionar `[]` ou especificar dependencies

## Accessibility Issues (A11Y)

### 1. [A11Y] src/components/OrdersTable.tsx
**Issue:** Button sem label acessível
```tsx
<IconButton onClick={handleDelete}>
  <DeleteIcon />  {/* ← Sem aria-label */}
</IconButton>
```
**Sugestão:** Adicionar `aria-label="Deletar pedido"`

### 2. [A11Y] src/components/OrderModal.tsx
**Issue:** Modal sem role
```tsx
<Dialog open={open}>  {/* ← Sem role="dialog" */}
```
**Sugestão:** MUI Dialog já adiciona, mas verificar se não está overriding

## Performance Issues (PERF)

### 1. [PERF] src/hooks/useOrders.ts
**Issue:** Re-renderização desnecessária
```tsx
const filters = { status, type };  // ← Novo objeto a cada render
useEffect(() => { ... }, [filters]);  // ← Effect re-run sempre
```
**Sugestão:** Memoizar: `const filters = useMemo(() => ({ status, type }), [status, type])`

## Warnings (WARN)

### 1. [WARN] src/types/order.ts
**Issue:** Type `any` desnecessário
```tsx
export interface Order {
  data: any;  // ← Muito genérico
}
```
**Sugestão:** Definir type específico para `data`

## Review by Group

### Group: orders-page
- `src/app/orders/OrdersPage.tsx` — **1 WARN**
- `src/app/orders/OrdersFilters.tsx` — **PASS**
- `src/hooks/useOrders.ts` — **1 PERF, 1 WARN**

### Group: order-detail
- `src/components/OrderDetail.tsx` — **1 FAIL**
- `src/components/OrderActions.tsx` — **1 A11Y**

### Group: order-table
- `src/components/OrdersTable.tsx` — **1 A11Y, 2 WARN**

## Action Items

### Must Fix (FAIL)
1. Corrigir `useEffect` sem dependencies em `OrderDetail.tsx`

### Should Fix (A11Y + PERF)
2. Adicionar `aria-label` em buttons sem texto
3. Memoizar `filters` object em `useOrders.ts`

### Optional (WARN)
4. Substituir `any` por types específicos
5. Extrair component grande (`OrdersPage` 350 linhas)

## Conclusion

**Status:** ❌ **Review failed** — 1 FAIL item must be fixed before merge.

**Estimated effort:** ~10 min para corrigir FAIL, +20 min para A11Y/PERF.
```

### 4.2 Criar arquivo

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

Write(
    path=f"{TASKS_DIR}/{task_key}/.review-report.md",
    contents=report_markdown
)
```

---

## Diferenças da Skill Original

| Aspecto | Skill Original | Pipeline Version |
|---------|---------------|------------------|
| **Input** | `git status` + roda linters | Lê `.review-data.json` |
| **Linters** | Roda eslint/tsc | **NÃO roda** (orquestrador já rodou) |
| **Output** | Resumo no chat | **Relatório markdown completo** |
| **Rules** | Lê `.cursor/rules/` | **Idêntico** (lê `.cursor/rules/`) |

---

## Checklist Final

- [x] Regras do projeto lidas (`.cursor/rules/`)
- [x] Dados do review lidos (`.review-data.json`)
- [x] Arquivos agrupados por domínio
- [x] Checks aplicados (universal, layer, pattern, react, a11y, perf)
- [x] Findings registrados
- [x] **Relatório `.review-report.md` CRIADO**
- [x] Usuário informado do resultado

---
name: pipeline-review-backend
description: Review de código backend para o Dev Pipeline Orchestrator. Lê `.review-data.json` gerado pelo orquestrador, aplica checklists do projeto, e SEMPRE gera `.review-report.md`. Use APENAS quando chamado pelo orquestrador em REVIEW_CHANGES.
---

# Pipeline Review Backend

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

## 📁 Estrutura de Repositórios (IMPORTANTE)

**Contextos de uso:**

### Quando chamada pelo ORQUESTRADOR (Pipeline):
- **Working directory:** o workspace root do Cursor (diretório raiz)
- **Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo dev-pipeline (contem .pipeline-config.json)
- **Código backend:** Consulte `local_path` do repo backend em `.pipeline-config.json`
- **Explore o src/ do repo** conforme path do config

### Quando usada PONTUALMENTE (standalone):
- **Working directory:** Dentro do repo backend (ver `local_path` no `.pipeline-config.json`)
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-review-backend pipelines/tasks/{task_key}/.review-data.json
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
- ✅ Output estruturado em markdown (para orquestrador e PR)

---

## Input Esperado

O orquestrador já forneceu:
- **Review data file**: `.review-data.json` com:
  - `repo`: "backend"
  - `linters`: {errors: [...], warnings: [...], summary: {...}}
  - `diff`: {files_changed: [...], diff_staged: "...", diff_unstaged: "...", stats: {...}}

**Se o arquivo não existir:** gerá-lo automaticamente via Shell com `git diff` e linters — **NÃO perguntar ao usuário**.

```bash
# Coletar diff (rodar no repo backend: white-api)
git -C {WORKSPACE_ROOT}/white-api diff
git -C {WORKSPACE_ROOT}/white-api diff --cached

# Linters
cd {WORKSPACE_ROOT}/white-api && black --check . && mypy . && ruff check .
```

Salvar resultado em `{PIPELINE_ROOT}/pipelines/tasks/{task_key}/.review-data.json` e prosseguir.

---

## Workflow (adaptado)

```
Step 1: Ler (ou gerar) .review-data.json → Step 2: Agrupar arquivos → Step 3: Review por grupo → 
Step 4: GERAR RELATÓRIO
```

---

## Step 1: Ler Dados do Review

Ler o arquivo `.review-data.json`:

```python
import json

with open(review_data_file) as f:
    data = json.load(f)

linters = data["linters"]  # {errors: [...], warnings: [...], summary: {...}}
diff_data = data["diff"]   # {files_changed: [...], diff_staged: "...", ...}
```

**Mostrar resumo:**
```
📊 Review Backend
Arquivos modificados: 5
Linter errors: 2
Linter warnings: 8
Diff: +150 -30 linhas
```

---

## Step 2: Agrupar Arquivos por Domínio

Agrupar arquivos relacionados para checar consistência cross-file:

```
Exemplos:
  order-serialization: [serializers.py, serializers_test.py]
  order-service: [order.py, order_strategy.py, orders_config.py]
  order-handler: [orders.py (handler), orders_test.py]
  infrastructure: [dynamodb.py, batch.py]
```

Classificar cada arquivo por **layer**:

| Layer | Path pattern |
|-------|-------------|
| handler | `app/handlers/*.py` (not viewmodel/) |
| viewmodel | `app/handlers/viewmodel/**/*.py` |
| serializer | `**/serializers.py` |
| service | `app/service/**/*.py` |
| config | `app/config/*.py` |
| constants | `app/constants/*.py` |
| entity | `app/entities/**/*.py` |
| test | `*_test.py`, `test_*.py`, `app/tests/**` |
| yaml-config | `**/*.yaml` in service dirs |

---

## Step 3: Review Por Grupo

Para cada grupo:

### 3a. Ler Contexto

1. **Ler git diff** para cada arquivo (`diff_data["diff_staged"]` + `diff_data["diff_unstaged"]`)
2. **Ler arquivos completos** quando diff precisa de contexto
3. Para arquivos novos (untracked), ler o arquivo inteiro

### 3b. Aplicar Checks

**Ordem:**
1. **Universal checks** (todos arquivos)
2. **Layer-specific checklist** (da skill original `~/.cursor/skills/skill-back-review-changes/refs/checklists.md`)
3. **Pattern verification** (obrigatório para arquivos novos)
4. **Cross-file consistency** (por grupo)
5. **Edge case analysis** (obrigatório)
6. **Tech lead quick review** (8 checks)
7. **Design critique** (obrigatório)

### Universal Checks

- [ ] Import order: stdlib → third-party → `app.*`
- [ ] No commented-out code
- [ ] No `print()` (use `logging`)
- [ ] No hardcoded env values
- [ ] Naming: functions=snake_case, classes=PascalCase, UPPER_SNAKE_CASE
- [ ] No unnecessary comments narrating code
- [ ] No reinvented utils (grep `app/utils/` antes)
- [ ] DB entities em inglês

### Overengineering Detection

Flag changes onde **cost > benefit:**

- [ ] Rare edge case (<1% com baixo impacto)
- [ ] Premature optimization (sem load testing)
- [ ] Defensive coding para estados impossíveis
- [ ] Over-abstraction (services usados em 1 lugar só)

**Marcar como:** `WARN-OVERENGINEERING`

### Pattern Verification (arquivos novos/refatorados)

Para cada arquivo novo:
1. **Encontrar referência:** handler/service/entity similar
2. **Comparar:**
   - Imports (relativo vs absoluto?)
   - Constructor (type hints, atributos `_table`, `_dynamodb`, `_logger`)
   - Chamadas a infra (positional vs kwargs?)
   - Response format (campos, nomes, nesting)
   - Utilitários (reinventando `csv_to_list`, `encode_cursor`, etc?)
3. **Marcar divergências:** WARN (menor) ou FAIL (quebra consistência)

### Edge Case Analysis (obrigatório)

Para cada método/função modificado ou criado:

**1. Inputs ausentes:**
- `order_item['group']` vs `order_item.get('group', {})`?
- Lista vazia vs `None` vs ausente?
- String vazia (`''`) vs `None`?

**2. Falha em dependências externas:**
- Se S3/Redis/API falhar, fluxo principal é afetado?
- Operação principal ANTES ou DEPOIS da que pode falhar?
- Try/except? Exceção logada ou engolida?

**3. Retrocompatibilidade:**
- Registros antigos no DynamoDB têm todos os campos?
- Defaults defensivos (`.get('field', default)')?
- Campo retorna `None` vs `[]` vs `{}`?

**4. Cobertura de testes:**
- Para cada guard/condicional, existe teste?
- Cenários: dependência `None`, exceção, campo ausente, lista vazia

**5. Templates e strings:**
- Variáveis de template podem ser vazias? Resultado OK?
- URLs com f-string: componente `None` ou vazio?

**Marcar:** `EDGE` (não coberto, risco prod) ou `WARN` (gap de teste sem risco imediato)

### Tech Lead Quick Review (8 checks)

1. **DRY** — código duplicado 3+ vezes?
2. **Magic strings** — string hardcoded 2+ vezes?
3. **Magic numbers** — números sem contexto?
4. **Type hints** — `list[dict[str, Any]]` genérico? TypedDict
5. **Hardcoded columns** — validações com `column="B"`? Mapeamento dinâmico
6. **Input validation** — parâmetros vazios validados?
7. **Exception handling** — `except Exception` genérico?
8. **Unnecessary constants** — limites arbitrários não validados?

### Design Critique (obrigatório)

Avaliar decisões arquiteturais — incluindo mudanças pedidas por reviewers.

Para cada mudança significativa:
1. **A remoção faz sentido?** O que o código removido fazia? Tinha razão arquitetural?
2. **A simplificação introduz problema novo?** Troca um problema por outro pior?
3. **Reviewer entendeu contexto completo?** Sugestão externa certa no diagnóstico mas errada na solução?
4. **Efeito colateral não mapeado?** Outros callers afetados?
5. **Edge cases ignorados?** Se remove guard, o que acontece?

**Marcar:** `DESIGN` (mais crítico que FAIL)

### 3c. Registrar Findings

Cada finding com severity: **FAIL** / **WARN** / **PASS** / **EDGE** / **DESIGN** / **WARN-OVERENGINEERING**

---

## Step 4: GERAR RELATÓRIO (OBRIGATÓRIO)

**Este passo é CRÍTICO** — o pipeline espera este arquivo.

### 4.1 Determinar caminho

```python
story_key = "PROJ-436"
task_key = "PROJ-437"
output_file = f"pipelines/tasks/{task_key}/.review-report.md"
```

### 4.2 Estrutura do Relatório

```markdown
# Code Review Report — Backend

**Task:** PROJ-437  
**Date:** 2026-03-25  
**Reviewer:** Pipeline (Automated)

## Summary

- **Files reviewed:** 5
- **FAIL:** 2
- **DESIGN:** 0
- **EDGE:** 3
- **WARN:** 5
- **WARN-OVERENGINEERING:** 0
- **PASS:** 12

## Critical Issues (FAIL)

### 1. [FAIL] app/handlers/orders.py
**Issue:** Import relativo inconsistente
```python
# Encontrado:
from app.dependencies import get_dynamodb_table

# Esperado (padrão do projeto):
from ..dependencies import get_dynamodb_table
```
**Sugestão:** Usar import relativo (padrão de todos os handlers)

### 2. [FAIL] app/service/order.py
**Issue:** Reinventando utilitário existente
**Código:**
```python
def parse_csv(text):
    return [x.strip() for x in text.split(',')]
```
**Sugestão:** Usar `csv_to_list()` de `app/utils/utils.py` (já testado)

## Edge Cases (EDGE)

### 1. [EDGE] app/handlers/orders.py:45
**Issue:** Acesso a campo sem validação
```python
employee_id = order_item['employee_id']  # ← KeyError se ausente
```
**Sugestão:** Usar `.get('employee_id')` com default ou validar antes

### 2. [EDGE] app/service/order.py:78
**Issue:** Falha em S3 não logada
```python
try:
    s3_client.put_object(...)
except Exception:
    pass  # ← Engole exceção silenciosamente
```
**Sugestão:** Log da exceção + re-raise ou fallback

## Warnings (WARN)

### 1. [WARN] app/constants/order_types.py
**Issue:** Magic string repetida
```python
# 3 ocorrências de "hr_modify_employee"
```
**Sugestão:** Constante: `HR_MODIFY_EMPLOYEE = "hr_modify_employee"`

## Design Concerns (DESIGN)

(Nenhum encontrado)

## Overengineering (WARN-OVERENGINEERING)

(Nenhum encontrado)

## Review by Group

### Group: order-handler
- `app/handlers/orders.py` — **2 FAIL, 1 EDGE**
- `tests/handlers/test_orders.py` — **1 WARN**

### Group: order-service
- `app/service/order.py` — **1 FAIL, 1 EDGE, 2 WARN**

### Group: infrastructure
- `app/constants/order_types.py` — **1 WARN**

## Action Items

### Must Fix (FAIL)
1. Corrigir imports relativos em `app/handlers/orders.py`
2. Substituir `parse_csv()` custom por `csv_to_list()` em `app/service/order.py`

### Should Fix (EDGE + WARN)
3. Adicionar `.get()` defensivo em `app/handlers/orders.py:45`
4. Log exceção S3 em `app/service/order.py:78`
5. Extrair constante `HR_MODIFY_EMPLOYEE`

## Conclusion

**Status:** ❌ **Review failed** — 2 FAIL items must be fixed before merge.

**Estimated effort:** ~15 min para corrigir todos os problemas.
```

### 4.3 Criar arquivo com Write tool

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

output_dir = Path(f"{TASKS_DIR}/{task_key}")
output_dir.mkdir(parents=True, exist_ok=True)

Write(
    path=str(output_dir / ".review-report.md"),  # v2.1: sempre .review-report.md
    contents=report_markdown
)
```

### 4.4 Confirmar criação

```
✅ Arquivo criado: pipelines/tasks/PROJ-437/.review-report.md

📊 Resultado:
- 2 FAIL (must fix)
- 3 EDGE (should fix)
- 5 WARN (optional)

Status: ❌ Review failed

Pressione qualquer tecla...
```

---

## Validações Finais

- [ ] `.review-data.json` foi lido corretamente
- [ ] Arquivos foram agrupados por domínio
- [ ] Todos os checks foram aplicados
- [ ] Findings têm severidade correta
- [ ] Action items estão claros
- [ ] **Relatório `.review-report.md` foi CRIADO**
- [ ] Path correto: `pipelines/tasks/{task_key}/.review-report.md`

---

## Diferenças da Skill Original

| Aspecto | Skill Original | Pipeline Version |
|---------|---------------|------------------|
| **Input** | `git status` + roda linters | Lê `.review-data.json` (já tem tudo) |
| **Linters** | Roda black/mypy/ruff | **NÃO roda** (orquestrador já rodou) |
| **Output** | Resumo no chat | **Relatório markdown completo** |
| **Path** | Flexível | **Fixo**: `pipelines/tasks/{task_key}/.review-report.md` |
| **Grouping** | Manual | Usa `diff_data["files_changed"]` |

---

## Referências (usar da skill original)

- `~/.cursor/skills/skill-back-review-changes/refs/checklists.md` — Checklists por layer
- `~/.cursor/skills/skill-back-review-changes/refs/review.md` — Tech lead review estendido
- `~/.cursor/skills/skill-back-review-changes/refs/implementation.md` — Padrões FastAPI/DynamoDB/pytest

---

## Checklist Final

- [x] Dados do review foram lidos (`.review-data.json`)
- [x] Arquivos foram agrupados
- [x] Todos os checks aplicados (universal, layer, pattern, edge, tech lead, design)
- [x] Findings registrados com severity
- [x] **Relatório `.review-report.md` CRIADO**
- [x] Path correto confirmado
- [x] Usuário informado do resultado

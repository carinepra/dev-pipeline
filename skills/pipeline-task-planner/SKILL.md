---
name: pipeline-task-planner
description: Planeja implementação de uma task Jira para o Dev Pipeline Orchestrator. SEMPRE gera arquivo `.plan.md` no caminho esperado. Use APENAS quando chamado pelo orquestrador em TASK_PLANNING.
---

# Pipeline Task Planner

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

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

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

---

## Fluxo de governança (ordem obrigatória)

1. **Criar o plano** — gerar o `.plan.md` com escopo fiel à task, após análise (Jira, Figma, codebase).
2. **Incentivar discussão técnica** — usar modo Plan, AskQuestion e espaço para dúvidas até **todos os pontos estarem alinhados** (abordagem, arquivos, riscos, dependências). Não tratar o plano como “fechado” só porque o arquivo foi escrito.
3. **Rodar a skill de revisão de plano** — em seguida, **obrigatoriamente** invocar `pipeline-plan-validator` (Step 7) sobre o mesmo `.plan.md`, para endurecer o plano em 3 rounds.
4. **Só depois** da revisão: o pipeline/orquestrador pode perguntar se pode **executar** (avançar para implementação). **Sempre confirmar explicitamente** com o usuário que pode **executar o plano** (implementar) — **nunca** assumir consentimento silencioso.

A ideia é: **plano → alinhamento em discussão → revisão automatizada do plano → confirmação explícita antes de executar.**

---

## ⚠️ DISCLAIMER CRÍTICO: Escopo e Foco

**🎯 REGRA FUNDAMENTAL: ATENHA-SE ESTRITAMENTE AO OBJETIVO DA TASK**

### O Que Fazer

✅ **Foco absoluto no escopo da task:**
- Ler o que a task pede (summary, description, ACs)
- Planejar APENAS o que está descrito
- Identificar arquivos ESTRITAMENTE necessários
- Propor implementação MÍNIMA viável

✅ **Se identificar gaps ou melhorias adicionais:**
- **NÃO adicione ao plano automaticamente**
- **USE MODO ASK** para validar com o usuário:
  ```
  "Identifiquei que poderíamos também [X]. 
   Deseja incluir isso no escopo ou manter apenas o solicitado?"
  ```
- Só adicione se usuário aprovar explicitamente

### O Que NÃO Fazer

❌ **Não expanda o escopo sem aprovação:**
- "Já que vamos mexer em X, podemos refatorar Y também"
- "Seria bom adicionar Z enquanto estamos aqui"
- "Aproveitando, podemos melhorar W"

❌ **Não adicione features não solicitadas:**
- Otimizações não mencionadas
- Refatorações "de brinde"
- Testes além do escopo
- Validações extras não requisitadas

❌ **Não presuma o que o usuário quer:**
- "Isso claramente precisa de [X]" → ASK FIRST
- "Provavelmente querem [Y] também" → ASK FIRST
- "Faz sentido adicionar [Z]" → ASK FIRST

### Por Quê?

**Problema:** Planos com escopo expandido geram:
- ⏱️ Mais tempo de implementação
- 🐛 Mais pontos de falha
- 🔄 Retrabalho na revisão (usuário rejeita extras)
- 💰 Desperdício de recursos

**Solução:** Plano minimalista → aprovação rápida → implementação eficiente

### Checklist de Escopo

Antes de gerar o plano, perguntar a si mesmo:

- [ ] Tudo no plano está EXPLICITAMENTE solicitado na task?
- [ ] Há algo que eu ASSUMI que deveria ser feito?
- [ ] Há melhorias/refatorações "de brinde"?
- [ ] Se SIM em 2 ou 3: **USE MODO ASK** antes de adicionar

**Lema:** "Entregar exatamente o que foi pedido, nada mais, nada menos."

---

**Diferenças da skill original:**
- ✅ **SEMPRE gera** o arquivo `.plan.md` no formato esperado
- ✅ **Caminho fixo** baseado no task key fornecido
- ✅ **Invoca pipeline-plan-validator automaticamente** (Step 7)
- ✅ **Entra em modo Plan** para discussão colaborativa
- ✅ **Usa AskQuestion** para validar decisões técnicas

---

## Input Esperado

O orquestrador já forneceu:
- **Task key**: `PROJ-437` (subtask a planejar)
- **Story key**: `PROJ-436` (parent)
- **Task data**: Summary, description (já fetched ou do breakdown)

**Não** pedir essas informações novamente.

---

## Workflow

```
Step 0: Ativar Modo Plan →
Step 1: Ler task → Step 2: Ler design (Figma) → Step 3: Explorar codebase →
Step 4: Consultar docs → Step 5: Validar Decisões (AskQuestion) → Step 6: GERAR PLANO
```

---

## Step 0: Ativar Modo Plan

**OBRIGATÓRIO: Logo no início da skill, entre em modo Plan.**

Use `SwitchMode` com:
- target_mode_id: "plan"
- explanation: "Vamos planejar a implementação da task colaborativamente antes de começar"

**Benefícios:**
- Discussão focada sobre abordagem e decisões técnicas
- Usuário pode revisar e ajustar plano antes da implementação
- Identificar riscos e dependências sem começar a codificar

---

## Step 1: Ler a Task no Jira

A task foi criada pelo pipeline no step anterior. Buscar detalhes:

### Opção A: Atlassian MCP (preferencial)

1. Listar tools do servidor MCP Atlassian
2. Buscar: summary, description, acceptance criteria, parent epic, Figma links

### Opção B: Fallback via script

Se MCP falhar:
```bash
# Usar query_issues.py da skill original
source ~/.zshrc && python3 ~/.cursor/skills/skill-jira-task-creator/query_issues.py
```

Com `QUERY = {"type": "issue", "key": "PROJ-437"}`.

**Mostrar resumo:**
```
📋 Task: PROJ-437
Parent: PROJ-436
Summary: [Portal] Adicionar hr_modify_employee ao NewMovementDrawer
Component: Front

Description:
- Adicionar tipo ao availableTypes
- Fluxo: criação → upload → validação → aprovação
- ...
```

---

## Step 2: Ler Design do Figma (se disponível)

- Se a description da task tiver link Figma, usar Figma MCP (listar tools antes)
- Extrair: hierarquia, layout, tokens quando útil para o plano
- Sem link: nota "sem Figma"
- MCP falhou: perguntar se o usuário cola o link

---

## Step 3: Explorar o Codebase

Detectar repo pelo workspace path ou pelo `scope` do `story_data`:

| Repo | Foco |
|------|------|
| Repo frontend (ver config) | `src/app/`, components, hooks, services, types, constants |
| Repo backend (ver config) | handlers, services, entities, config, tests, DynamoDB |

**Estratégia:**
1. Usar subagents `explore` em paralelo para áreas relevantes
2. Identificar **padrão similar** a reutilizar (ex: endpoint similar, componente similar)
3. Listar arquivos afetados

**Frontend:**
- Buscar components similares em `src/components/`
- Buscar hooks relacionados em `src/hooks/`
- Buscar services em `src/services/`
- Buscar types em `src/types/`

**Backend:**
- Buscar handlers similares em `app/handlers/`
- Buscar services em `app/service/`
- Buscar entities em `app/entities/`
- Buscar constants em `app/constants/`

---

## Step 3.5: Contexto do Banco de Dados (OPCIONAL — apenas backend)

**Execute este step SOMENTE SE:**
1. O escopo da task for `backend`
2. A descrição da task mencionar operações de persistência (BD, tabela, entidade, query, schema)
3. O repo afetado tiver `database` configurado no `.pipeline-config.json`

**Se qualquer condição não for atendida, pule para o Step 4.**

### Como descobrir o BD do repo

```python
import json
from pathlib import Path

# Descobrir qual repo é o backend desta task
config = json.loads(Path(".pipeline-config.json").read_text())

# Identificar o repo pelo escopo/componente da task
# (ex: componente "Back" → white-backend; ler component_repo_map do projeto)
project_key = story_key.split("-")[0]  # ex: "PROJ"
project_config = config["jira"]["projects"].get(project_key, {})
component_map = project_config.get("component_repo_map", {})
repo_id = component_map.get(task_component, None)  # task_component = "Back", "Infra", etc.

repo_config = config["repositories"].get(repo_id, {})
db_config = repo_config.get("database")

if not db_config:
    print(f"ℹ️ Repo '{repo_id}' não tem banco de dados configurado — pulando Step 3.5")
    db_context = None
else:
    print(f"🗄️ BD configurado: {db_config['type']} — {db_config.get('description', '')}")
```

### Por tipo de banco

**`type: "dynamodb"`**

```python
if db_config["type"] == "dynamodb":
    from shared.db.dynamodb import DynamoDBClient

    db = DynamoDBClient.try_connect()

    if db is None:
        print("ℹ️ DynamoDB indisponível (credenciais ausentes ou tabela inacessível) — pulando")
        db_context = None
    else:
        # Inferir a entity relevante para esta task a partir da descrição
        # Ex.: task fala de "pedidos" → "ORDER"; "funcionários" → "EMPLOYEE"
        target_entity = "<inferir da descrição da task>"

        sample_items = db.query_by_gsi(
            gsi_name="HIERARCHY",
            pk_attr="entity",
            pk_value=target_entity,
            limit=3
        )

        if sample_items:
            db_context = {
                "type": "dynamodb",
                "table": db.table_name,
                "entity": target_entity,
                "real_attributes": list(sample_items[0].keys()),
                "available_gsis": ["HIERARCHY", "STATUS", "TIMESTAMP", "GSI1", "GSI2"],
            }
            print(f"✅ Schema real: {db_context['real_attributes']}")
        else:
            db_context = {"type": "dynamodb", "table": db.table_name, "note": "sem itens de exemplo"}
```

**`type: "unknown"` ou tipo não suportado**

```python
else:
    # BD configurado mas sem client implementado ainda
    print(f"⚠️ Tipo de BD '{db_config['type']}' reconhecido no config mas sem client implementado")
    print(f"   {db_config.get('notes', 'Consulte o config para detalhes')}")
    db_context = {"type": db_config["type"], "note": db_config.get("notes", "")}
```

**Use `db_context` no plano final** para documentar:
- Schema real dos atributos (evita discrepâncias entre plano e dados reais)
- Índices/GSIs disponíveis para as queries previstas
- Alertas se o tipo de BD não tiver suporte implementado

---

## Step 4: Consultar Docs de Libs (Context7 MCP)

Com base nos passos anteriores, escolher libs relevantes:

**Front:** Next.js, MUI, TanStack Table/Query, Zod, React Hook Form
**Back:** FastAPI, boto3/DynamoDB, pytest, Pydantic

Invocar Context7 MCP (listar tools primeiro). Se desabilitado ou falhar: `WebSearch` ou omitir.

---

## Step 5: Validar Decisões (AskQuestion)

**USE `AskQuestion` para confirmar decisões técnicas antes de gerar o plano.**

```python
print("\n" + "="*60)
print("🔍 VALIDAÇÃO DE DECISÕES TÉCNICAS")
print("="*60 + "\n")
```

**Preparar perguntas baseadas na análise:**

```json
{
  "title": "Validação do Plano de Implementação",
  "questions": [
    {
      "id": "implementation_approach",
      "prompt": "Qual abordagem de implementação usar?",
      "options": [
        {"id": "reuse", "label": "Reutilizar código existente de [arquivo similar]"},
        {"id": "extend", "label": "Estender componente/handler existente"},
        {"id": "new", "label": "Criar novo do zero"}
      ],
      "allow_multiple": false
    },
    {
      "id": "scope_validation",
      "prompt": "O plano está aderente ao escopo da task?",
      "options": [
        {"id": "yes", "label": "Sim, cobre exatamente o que foi pedido"},
        {"id": "missing", "label": "Falta algo importante"},
        {"id": "extra", "label": "Tem algo além do escopo"}
      ],
      "allow_multiple": false
    },
    {
      "id": "ready_to_implement",
      "prompt": "O plano está claro o suficiente para implementar?",
      "options": [
        {"id": "yes", "label": "Sim, posso começar a implementar"},
        {"id": "needs_detail", "label": "Precisa de mais detalhes técnicos"},
        {"id": "needs_context", "label": "Precisa de mais contexto do codebase"}
      ],
      "allow_multiple": false
    }
  ]
}
```

**Processar respostas:**

```python
# Se há problemas, coletar feedback
if answers["scope_validation"] != "yes" or answers["ready_to_implement"] != "yes":
    print("\n💡 Vamos ajustar o plano antes de gerar:")
    print("   Descreva o que precisa ser ajustado/adicionado:")
    # Usuário responde via mensagem
    # Ajustar plano conforme feedback
    # Re-validar se necessário

# Se tudo OK, prosseguir para Step 6
else:
    print("✅ Validação concluída. Gerando plano final...")
```

---

## Step 6: GERAR PLANO (OBRIGATÓRIO)

**Este passo é CRÍTICO** — o pipeline espera este arquivo para continuar.

### 6.1 Determinar caminho do arquivo

```python
story_key = "PROJ-436"  # Parent story
task_key = "PROJ-437"   # Subtask atual
output_dir = f"pipelines/tasks/{task_key}"
output_file = f"{output_dir}/.plan.md"
```

**No repo `dev-pipeline`**, criar:
```
pipelines/tasks/PROJ-437/.plan.md
```

### 6.2 Estrutura do Plano

**Frontend (template):**

```markdown
# [Nome da feature/task]

## Contexto
- **Task Jira:** PROJ-437 — [Portal] Adicionar hr_modify_employee ao NewMovementDrawer
- **Parent Story:** PROJ-436 — Implementar fluxo completo de hr_modify
- **Design Figma:** [link ou N/A]
- **Component:** Front
- **Priority:** Highest

### DOD (Definition of Done)
- [ ] hr_modify_employee disponível no select do NewMovementDrawer
- [ ] POST /orders/hr_modify_employee cria pedido e redireciona
- [ ] Upload, validação, aprovação e cancelamento funcionam
- [ ] Testes E2E passando

## Escopo

### Criar
- Novo tipo `hr_modify_employee` em `useMovementForm.ts`
- Handler no `NewMovementDrawer.tsx` para o novo tipo
- Validações específicas para hr_modify (se houver)

### Modificar
- `src/hooks/useMovementForm.ts` — adicionar tipo ao `availableTypes`
- `src/components/NewMovementDrawer.tsx` — integrar tipo no fluxo
- `src/types/movement.ts` — estender interfaces

### Referência no codebase
- **Padrão similar:** `hr_new_employee` já implementado
- **Arquivos de referência:**
  - `src/hooks/useMovementForm.ts` (lógica de tipos)
  - `src/components/NewMovementDrawer.tsx` (UI)

## Abordagem

### 1. Adicionar tipo ao useMovementForm
- Adicionar `hr_modify_employee` ao array `availableTypes`
- Configurar labels e validações específicas
- Seguir padrão idêntico ao `hr_new_employee`

### 2. Integrar ao NewMovementDrawer
- Tornar tipo selecionável no dropdown
- Configurar fluxo de submissão (POST para backend)
- Redirecionar após criação

### 3. Validações
- Campos obrigatórios: employee_id, reason, new_data
- Validar formato de new_data (JSON válido)
- Mensagens de erro claras

### 4. Testes
- Unit tests: useMovementForm com novo tipo
- Integration tests: NewMovementDrawer submissão
- E2E: fluxo completo de criação

## Decisões Arquiteturais

### Reutilização de código
- ✅ Reusar `useMovementForm` existente (adicionar tipo ao array)
- ✅ Reusar `NewMovementDrawer` existente (não criar componente novo)
- ❌ Não criar service separado (usar service existente de movements)

### Validações
- Validar no frontend (Zod schema)
- Validar no backend (Pydantic model)
- Não duplicar validações

### API Integration
- Endpoint: `POST /orders/hr_modify_employee` (backend já implementa)
- Payload: `{employee_id, reason, new_data, attachments}`
- Response: `{order_id, status, redirect_url}`

## Implementação Passo a Passo

### Passo 1: Atualizar useMovementForm.ts
```typescript
// src/hooks/useMovementForm.ts

const availableTypes = [
  'hr_new_employee',
  'hr_modify_employee',  // ← NOVO
  'hr_resigned',
  // ...
];

const typeLabels = {
  hr_new_employee: 'Nova Contratação',
  hr_modify_employee: 'Modificação de Funcionário',  // ← NOVO
  hr_resigned: 'Desligamento',
  // ...
};
```

### Passo 2: Atualizar NewMovementDrawer.tsx
```typescript
// src/components/NewMovementDrawer.tsx

// No handleSubmit, adicionar case para hr_modify_employee
case 'hr_modify_employee':
  await createOrder({
    type: 'hr_modify_employee',
    data: formData,
    attachments: files,
  });
  router.push(`/orders/${orderId}`);
  break;
```

### Passo 3: Estender types
```typescript
// src/types/movement.ts

export type MovementType = 
  | 'hr_new_employee'
  | 'hr_modify_employee'  // ← NOVO
  | 'hr_resigned'
  | ...;

export interface HrModifyEmployeeData {
  employee_id: string;
  reason: string;
  new_data: Record<string, any>;
  attachments?: File[];
}
```

### Passo 4: Validações Zod
```typescript
// src/schemas/movement.ts

const hrModifySchema = z.object({
  employee_id: z.string().min(1, 'ID obrigatório'),
  reason: z.string().min(10, 'Justificativa obrigatória'),
  new_data: z.record(z.any()),
});
```

### Passo 5: Testes
```typescript
// src/hooks/__tests__/useMovementForm.test.ts

test('hr_modify_employee está disponível', () => {
  const { result } = renderHook(() => useMovementForm());
  expect(result.current.availableTypes).toContain('hr_modify_employee');
});

// src/components/__tests__/NewMovementDrawer.test.tsx

test('submete hr_modify_employee corretamente', async () => {
  // ...
});
```

## Arquivos Afetados

### Criar
- `src/schemas/movement.ts` (novo — se não existir)

### Modificar
- `src/hooks/useMovementForm.ts`
- `src/components/NewMovementDrawer.tsx`
- `src/types/movement.ts`
- `src/hooks/__tests__/useMovementForm.test.ts`
- `src/components/__tests__/NewMovementDrawer.test.tsx`

## Dependências

### Blocking
- **PROJ-435** (Backend endpoint) — precisa estar implementado antes

### External
- API endpoint `/orders/hr_modify_employee` funcional
- Permissões no backend configuradas

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Backend não está pronto | Implementar com mock/stub, trocar por API real depois |
| Validações diferentes front/back | Alinhar schemas Zod (front) e Pydantic (back) |
| UX confusa para usuário | Adicionar tooltips e mensagens claras |

## Critérios de Sucesso

- [ ] Tipo `hr_modify_employee` disponível no dropdown
- [ ] Formulário válido submete corretamente
- [ ] Redirecionamento após criação funciona
- [ ] Mensagens de erro são claras
- [ ] Testes unitários passando (coverage > 80%)
- [ ] Testes E2E passando
- [ ] Code review aprovado
- [ ] Sem linter errors

## Notas Adicionais

- Seguir `.cursor/rules/` do projeto (components, hooks, services)
- Usar MUI components existentes (não criar custom)
- Manter consistência visual com outros tipos de movement
- Documentar decisões no código (comentários em pontos não-óbvios)

## Referências

- [Padrão similar: hr_new_employee](src/hooks/useMovementForm.ts#L45)
- [API docs: POST /orders](../<repo-backend>/docs/api.md) — use o path do repo backend em `repositories` (`.pipeline-config.json`)
- [Regras do projeto](.cursor/rules/components.mdc)
```

**Backend (template — alinhar com `refs/planning-backend.md`):**

```markdown
# [Nome da feature/task]

## Objective
[Descrição do que a task resolve]

## Scope

### In Scope
- Criar endpoint `POST /orders/hr_modify_employee`
- Persistir no DynamoDB (`Order_Item` table)
- Validar payload com Pydantic
- Logging de operações

### Out of Scope
- Notificações (task separada)
- Sync com sistemas externos (task separada)
- UI (frontend task separada)

### Files Affected

**Create:**
- `app/handlers/hr_modify_employee.py` (handler)
- `tests/handlers/test_hr_modify_employee.py` (tests)

**Modify:**
- `app/main.py` (adicionar route)
- `app/entities/order_item.py` (estender se necessário)

## DynamoDB Operations

### Table: `Order_Item`

**Primary Key:** `PK = ORDER#{order_id}`, `SK = ITEM#{item_id}`

**GSI1:** `GSI1PK = EMPLOYEE#{employee_id}`, `GSI1SK = ORDER#{timestamp}`

**Attributes (new/modified):**
- `order_type` → `hr_modify_employee`
- `modification_data` → `{"reason": "...", "new_data": {...}}`

**Operations:**
- `put_item` — criar order
- `query` (GSI1) — buscar orders por employee

## Implementation Steps

### 1. Create Handler
```python
# app/handlers/hr_modify_employee.py

from fastapi import APIRouter, Depends
from app.dependencies import get_dynamodb_table
from app.entities.order_item import OrderItem

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/hr_modify_employee")
async def create_hr_modify_order(
    payload: HrModifyPayload,
    table = Depends(get_dynamodb_table),
):
    # 1. Validate
    # 2. Create OrderItem
    # 3. Persist to DynamoDB
    # 4. Return
    pass
```

### 2. Add Route to main.py
```python
# app/main.py

from app.handlers import hr_modify_employee

app.include_router(hr_modify_employee.router)
```

### 3. Extend Entity
```python
# app/entities/order_item.py

class OrderItem:
    # Adicionar suporte para order_type = "hr_modify_employee"
    pass
```

### 4. Tests (pytest + moto)
```python
# tests/handlers/test_hr_modify_employee.py

@pytest.mark.parametrize("scenario", ["valid", "invalid_payload", "dynamodb_error"])
def test_create_hr_modify_order(scenario, dynamodb_table_mock):
    # ...
    pass
```

## Testing Strategy

### Unit Tests
- Payload validation (valid, invalid)
- DynamoDB operations (success, error)
- Error handling (4xx, 5xx)

### Integration Tests
- End-to-end flow (POST → persist → query)

### Coverage Target
> 90% (handlers, entities)

## Success Criteria

- [ ] Endpoint `POST /orders/hr_modify_employee` funcional
- [ ] Payload validado com Pydantic
- [ ] Persistido no DynamoDB corretamente
- [ ] Testes passando (coverage > 90%)
- [ ] Logging implementado
- [ ] Code review aprovado
- [ ] Sem linter errors (black, mypy, ruff)

## Dependencies

### Blocking
- Nenhuma

### External
- DynamoDB table `Order_Item` configurada
- Permissões IAM para DynamoDB

## Risks

| Risk | Mitigation |
|------|------------|
| Schema incompatível com dados existentes | Usar `.get()` defensivo, defaults |
| DynamoDB throttling | Implementar retry com backoff |

## References

- [Similar endpoint: hr_new_employee](app/handlers/hr_new_employee.py)
- [DynamoDB patterns](docs/dynamodb-patterns.md)
- [Testing guide](tests/README.md)
```

### 6.3 Criar o arquivo usando Write tool

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

# Garantir que o diretório existe
output_dir = Path(f"{TASKS_DIR}/{task_key}")
output_dir.mkdir(parents=True, exist_ok=True)

# USAR O TOOL Write DO CURSOR
Write(
    path=str(output_dir / ".plan.md"),  # v2.1: sempre .plan.md (não task_key.plan.md)
    contents=plan_markdown  # String do plano completo
)
```

### 6.4 Confirmar criação

Após criar o arquivo, **SEMPRE** informar ao usuário:

```
✅ Arquivo criado: pipelines/tasks/PROJ-437/.plan.md

📋 Plano:
- Escopo: 5 arquivos afetados
- Abordagem: Reusar padrão hr_new_employee
- Dependências: PROJ-435 (backend endpoint)

Pressione qualquer tecla para o pipeline continuar...
```

---

## Validações Finais

Antes de gerar o plano, validar:

- [ ] Task key está correto
- [ ] Contexto completo (Jira + Figma + codebase)
- [ ] Arquivos afetados listados
- [ ] Padrão similar identificado
- [ ] Passos de implementação claros
- [ ] Dependências mapeadas
- [ ] Critérios de sucesso definidos

---

## Diferenças da Skill Original

| Aspecto | Skill Original | Pipeline Version |
|---------|---------------|------------------|
| **Input** | Pede task key | Recebe do orquestrador |
| **Output** | Plano em markdown (flexível) | **SEMPRE gera arquivo .plan.md** |
| **Path** | Flexível | **Fixo**: `pipelines/tasks/{task_key}/.plan.md` |
| **Modo Plan** | Não usa | **Ativa automaticamente** (Step 0) |
| **AskQuestion** | Não usa | **Usa para validação** (Step 5) |
| **pipeline-plan-validator** | Roda no final | **Roda automaticamente** (Step 7) |
| **Approval** | Apresenta e espera | Pipeline pede após criar arquivo |

---

## Troubleshooting

### "Pipeline não encontrou o arquivo"

**Causa:** Plano não foi criado ou caminho está errado.

**Solução:**
1. Verificar se `Write` tool foi executado
2. Confirmar path: `pipelines/tasks/{task_key}/.plan.md`
3. Testar: `ls -la pipelines/tasks/PROJ-436/`

### "Plano muito genérico"

**Causa:** Exploração de codebase insuficiente.

**Solução:**
1. Usar subagents `explore` em áreas relevantes
2. Identificar padrão similar concreto (não assumir)
3. Listar arquivos específicos (não "handlers gerais")

### "Dependências faltando"

**Causa:** Não mapeou blocking tasks.

**Solução:**
1. Checar `blocking_links` do `.tasks-proposed.json`
2. Adicionar seção "Dependencies" com tasks bloqueadoras

---

## Step 7: Melhorar Plano Automaticamente (pipeline-plan-validator)

**⚡ AUTOMATIZAÇÃO:** Após criar o plano (Step 6), chamar automaticamente a skill de melhoria.

### 7.1. Informar usuário

```python
from pathlib import Path

plan_file = Path(f"{TASKS_DIR}/{task_key}/.plan.md")

print("\n" + "="*60)
print("✅ PLANO CRIADO")
print("="*60)
print(f"📄 Arquivo: {plan_file}")
print(f"📊 Tamanho: {plan_file.stat().st_size} bytes")
print("\n🔄 Executando pipeline-plan-validator automaticamente...")
print("   (3 rounds de análise crítica para robustez)")
print("="*60 + "\n")
```

### 7.2. Invocar skill automaticamente

**IMPORTANTE:** Usar o caminho **EXATO** do arquivo que acabou de criar.

```python
# Invocar automaticamente (sem precisar do usuário)
# O Cursor vai executar a skill e retornar aqui quando concluir
```

**Executar:**

```
@pipeline-plan-validator melhorar pipelines/tasks/{task_key}/.plan.md
```

### 7.3. Confirmar sucesso

Após a skill `pipeline-plan-validator` concluir:

```python
print("\n" + "="*60)
print("✅ PLANO MELHORADO (3 rounds concluídos)")
print("="*60)
print(f"📄 Arquivo final: {plan_file}")
print("\n📋 Próximos passos:")
print("   → Revisar o plano (pipeline-plan-validator já rodou)")
print("   → Alinhar qualquer ponto em dúvida em discussão técnica")
print("   → Só com confirmação explícita: aprovar execução / avançar para implementação")
print("   → Nunca executar o plano sem o usuário confirmar que pode executar")
print("="*60)
```

**Resultado final:** Plano robusto e revisado; **implementação só após confirmação explícita** de que pode executar.

---

## Checklist Final

Antes de terminar, confirmar:

- [x] **Modo Plan foi ativado** (Step 0)
- [x] Task foi lida (Jira + Figma)
- [x] Codebase foi explorado
- [x] Padrão similar foi identificado
- [x] **Decisões validadas com AskQuestion** (Step 5)
- [x] Plano foi criado (markdown completo)
- [x] **Arquivo `.plan.md` foi CRIADO** usando `Write` tool
- [x] Path está correto: `pipelines/tasks/{task_key}/.plan.md`
- [x] Plano tem todas as seções (Contexto, Escopo, Abordagem, Implementação, Critérios)
- [x] **pipeline-plan-validator foi invocado automaticamente** (Step 7)
- [x] Plano foi melhorado (3 rounds de análise)

---
name: pipeline-task-breaker
description: Task breakdown para o Dev Pipeline Orchestrator. Lê contexto de .story-plan.md, propõe quebra de tasks, e SEMPRE gera o arquivo .tasks-proposed.json no caminho esperado pelo pipeline.
---

# Pipeline Task Breaker

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

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

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**Diferenças da skill original:**
- ✅ **Lê contexto** de `.story-plan.md` (gerado pelo pipeline-story-analyzer)
- ✅ **SEMPRE gera** o arquivo `.tasks-proposed.json` no formato esperado
- ✅ **Não cria** issues no Jira (orquestrador faz isso após validação)
- ✅ **Caminho fixo** baseado no story key fornecido
- ✅ **Simplificado** - foca apenas em quebra de tasks
- ✅ **Entra em modo Plan** automaticamente
- ✅ **Usa AskQuestion** para validação da quebra

---

## Input Esperado

O orquestrador já forneceu:
- **Story key**: `<PROJECT>-XXX`
- **Story data**: Summary, description, acceptance criteria (já fetched)
- **Story plan**: `.story-plan.md` (já validado e gerado pelo pipeline-story-analyzer)

**Não** pedir essas informações novamente.

---

## Workflow

```
Step 0: Ativar Modo Plan →
Step 1: Ler Contexto (.story-plan.md) →
Step 2: Propor Quebra de Tasks →
Step 3: Validar com Usuário (AskQuestion) →
Step 4: GERAR JSON
```

---

## Step 0: Ativar Modo Plan

**OBRIGATÓRIO: Logo no início da skill, entre em modo Plan.**

Use `SwitchMode` com:
- target_mode_id: "plan"
- explanation: "Vamos planejar a quebra de tasks estrategicamente antes de criar no Jira"

**Benefícios:**
- Discussão colaborativa sobre estrutura e dependências das tasks
- Usuário pode revisar proposta antes de criar issues
- Ajustes rápidos sem necessidade de editar Jira depois

---

## Step 1: Ler Contexto do Story Plan

```python
import yaml
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

story_plan_path = Path(f"{STORIES_DIR}/{story_key}/.story-plan.md")

if story_plan_path.exists():
    print(f"📖 Lendo plano: {story_plan_path}\n")
    
    content = story_plan_path.read_text(encoding='utf-8')
    
    # Parsear YAML frontmatter
    if content.startswith('---'):
        _, frontmatter, markdown = content.split('---', 2)
        plan_data = yaml.safe_load(frontmatter)
        
        # Extrair contexto consolidado
        figma_summary = plan_data["context"]["figma"]["summary_one_line"]
        docs_summary = plan_data["context"]["docs"]["summary_one_line"]
        codebase_summary = plan_data["context"]["codebase"]["summary_one_line"]
        decisions = plan_data["decisions"]
        scope = plan_data["scope"]
        
        print("="*60)
        print("📋 CONTEXTO (do Story Planner)")
        print("="*60)
        print(f"\n🎨 Design: {figma_summary}")
        print(f"📚 Regras: {docs_summary}")
        print(f"💻 Código: {codebase_summary}")
        print(f"\n🤔 Decisões:")
        print(f"   - Reutilizar: {'Sim - ' + decisions.get('reuse_file', 'N/A') if decisions.get('reuse') else 'Não'}")
        print(f"   - Escopo: {decisions.get('scope_definition', 'N/A')[:50]}...")
        print(f"   - Approach: {decisions.get('approach', 'Padrão')}")
        print("="*60 + "\n")
        
    else:
        raise ValueError("Plano sem frontmatter YAML")
        
else:
    print("⚠️ Plano não encontrado. Usando análise básica (standalone)...\n")
    
    # Fallback: modo standalone (análise mínima)
    from questionary import select
    
    scope = select(
        "Qual o escopo desta história?",
        choices=["backend", "frontend", "both", "docs", "infra"]
    ).ask()
    
    # Exploração básica do codebase
    print("💻 Explorando codebase (modo básico)...")
    
    # [Busca simples por arquivos similares]
    # NÃO buscar Figma/docs (uso standalone sem planner)
    
    figma_summary = "N/A"
    docs_summary = "N/A"
    codebase_summary = "Análise básica"
    decisions = {}
```

---

## Step 2: Propor Quebra de Tasks

**Usar TODO o contexto carregado no Step 1.**

```python
print("="*60)
print("📝 PROPOSTA DE TASKS")
print("="*60 + "\n")

# Apresentar resumo do contexto novamente
print("### Contexto Consolidado (referência)")
print(f"- Design: {figma_summary}")
print(f"- Regras: {docs_summary}")
print(f"- Código: {codebase_summary}")

if decisions:
    print(f"- Reutilizar: {'Sim' if decisions.get('reuse') else 'Não'}")
    print(f"- Escopo: {decisions.get('scope_definition', 'Não especificado')[:50]}...")
    print(f"- Approach: {decisions.get('approach', 'Padrão')}")

print("\n---\n")
```

### 2.1 Criar Proposta de Subtasks

Seguir padrões do projeto:

**Backend tasks:** `B1`, `B2`, `B3`...
**Frontend tasks:** `F1`, `F2`, `F3`...
**Docs tasks:** `D1`, `D2`...
**Infra tasks:** `I1`, `I2`...

Para cada task proposta, incluir:

| Campo | Descrição |
|-------|-----------|
| **id** | Identificador único (B1, F1, etc) |
| **summary** | Título da task (com prefix `[Portal]` ou `[API]`) |
| **description** | O que fazer (bullet points) |
| **component** | `Back`, `Front`, `Design`, `Produto` |
| **priority** | `Highest` (default), `High`, `Medium`, `Low`, `Lowest` |
| **files** | Lista de arquivos afetados |
| **dependencies** | IDs de tasks que bloqueiam esta (ex: `["B1"]`) |
| **estimate** | Story points (opcional) |

**Padrões de descrição:**
- Sempre referenciar arquivos chave: `app/service/`, `app/handlers/`, `src/app/`, etc.
- Tasks que estendem padrão existente: "Padrão idêntico ao X já implementado"
- Tasks de teste: listar cenários específicos a cobrir

**Usar contexto do planner:**
- Se Figma presente: mencionar frames, textos, componentes nas tasks de frontend
- Exemplo: "Implementar modal conforme Figma (frame: Modal Confirmação, 480x240px)"

**Usar decisões do Step 5 do planner:**
- Se decisão de reutilização: "Reutilizar [arquivo] ajustando props X, Y"
- Se decisão de approach: "Implementar usando approach [X]"
- Se escopo definido: Incluir apenas o que está no escopo definido

### 2.2 Exemplo de Tasks Propostas

```markdown
## Tasks Propostas

**F1: [Portal] Criar componente ConfirmDeleteModal**

Descrição:
- Criar `src/components/ConfirmDeleteModal/index.tsx`
- Frame Figma: "Modal Confirmação" (480x240px)
- Props: isOpen, onConfirm, onCancel, beneficiaryName, isLoading
- Estados: normal, loading (spinner no botão confirmar)
- Textos exatos do Figma:
  * Título: "Confirmar Exclusão"
  * Mensagem: "Tem certeza que deseja excluir [Nome]? Esta ação não pode ser desfeita."
  * Botões: "Confirmar Exclusão", "Cancelar"
- Estilo: padding 24px, shadow elevation-24, cores #D32F2F, #FFFFFF
- Reutilizar padrão: ConfirmModal existente

Component: Front
Priority: Highest
Files: ['src/components/ConfirmDeleteModal/index.tsx', 'src/components/ConfirmDeleteModal/styles.ts']
Dependencies: []

**F2: [Portal] Implementar lógica de exclusão**

Descrição:
- Criar handler onConfirm: chamar API DELETE /beneficiaries/{id}
- Loading state durante request
- Feedback: toast success após exclusão
- Error handling: toast error se falhar
- Integrar com hook useBeneficiaries

Component: Front
Priority: Highest
Files: ['src/hooks/useBeneficiaries.ts']
Dependencies: ['F1']

**F3: [Portal] Testes Cypress**

Descrição:
- Cenário 1: abrir modal, clicar cancelar (fecha sem deletar)
- Cenário 2: abrir modal, clicar confirmar (loading → delete → toast)
- Cenário 3: API falha (mostrar toast de erro)
- Arquivo: cypress/e2e/beneficiaries/delete.cy.ts

Component: Front
Priority: High
Files: ['cypress/e2e/beneficiaries/delete.cy.ts']
Dependencies: ['F2']
```

---

## Step 3: Validar com Usuário (AskQuestion)

**USE `AskQuestion` para validar a proposta de quebra.**

```python
print("\n🔍 Revisão da Proposta\n")
```

**Estrutura da validação:**

```json
{
  "title": "Validação da Quebra de Tasks",
  "questions": [
    {
      "id": "proposal_quality",
      "prompt": "A quebra de tasks proposta está adequada?",
      "options": [
        {"id": "approved", "label": "Aprovada - pode criar no Jira"},
        {"id": "minor_adjusts", "label": "Precisa de ajustes menores"},
        {"id": "major_adjusts", "label": "Precisa de ajustes significativos"}
      ],
      "allow_multiple": false
    },
    {
      "id": "concerns",
      "prompt": "Há alguma preocupação específica com a proposta?",
      "options": [
        {"id": "none", "label": "Nenhuma preocupação"},
        {"id": "dependencies", "label": "Dependências entre tasks não estão claras"},
        {"id": "scope", "label": "Escopo de alguma task está errado"},
        {"id": "missing", "label": "Falta alguma task importante"},
        {"id": "redundant", "label": "Alguma task parece redundante"}
      ],
      "allow_multiple": true
    }
  ]
}
```

**Processar respostas:**

```python
# Se aprovado, prosseguir para Step 4
if answers["proposal_quality"] == "approved":
    print("✅ Proposta aprovada. Gerando JSON...")
    
# Se precisa ajustes, coletar feedback via mensagem
elif answers["proposal_quality"] in ["minor_adjusts", "major_adjusts"]:
    print(f"\n💡 Ajustes necessários. Preocupações: {', '.join(answers['concerns'])}")
    print("   Descreva os ajustes que gostaria de fazer:")
    print("   (Use a caixa de texto para detalhar)")
    
    # Usuário responde via mensagem
    # Aplicar ajustes conforme feedback
    # Re-apresentar proposta ajustada
    # Repetir validação até aprovação
```

**Iterar até aprovação final.**

---

## Step 4: GERAR JSON (OBRIGATÓRIO)

**Este passo é CRÍTICO** — o pipeline espera este arquivo para continuar.

### 4.1 Determinar caminho do arquivo

```python
story_key = "PROJ-542"  # Fornecido pelo orquestrador
output_path = Path(f"{STORIES_DIR}/{story_key}/.tasks-proposed.json")

print(f"\n📝 Output esperado: {output_path}")
```

### 4.2 Montar estrutura JSON

```python
import json
from datetime import datetime

tasks_data = {
    "story_key": story_key,
    "generated_at": datetime.now().isoformat(),
    "tasks": [
        {
            "id": "F1",
            "summary": "[Portal] Criar componente ConfirmDeleteModal",
            "description": "- Criar src/components/ConfirmDeleteModal/index.tsx\n- Frame Figma...",
            "component": "Front",
            "priority": "Highest",
            "files": ["src/components/ConfirmDeleteModal/index.tsx"],
            "dependencies": [],
            "estimate": 3
        },
        # ... outras tasks
    ]
}
```

### 4.3 Salvar arquivo JSON

```python
# Criar diretório se não existe
output_path.parent.mkdir(parents=True, exist_ok=True)

# Salvar JSON
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(tasks_data, f, indent=2, ensure_ascii=False)

print(f"\n✅ JSON gerado: {output_path}")
print(f"   Tasks: {len(tasks_data['tasks'])}")
print(f"   Backend: {sum(1 for t in tasks_data['tasks'] if t['id'].startswith('B'))}")
print(f"   Frontend: {sum(1 for t in tasks_data['tasks'] if t['id'].startswith('F'))}")
```

**Estrutura esperada pelo pipeline:**

```json
{
  "story_key": "PROJ-542",
  "generated_at": "2026-03-25T15:30:00",
  "tasks": [
    {
      "id": "F1",
      "summary": "[Portal] Criar componente X",
      "description": "- Bullet point 1\n- Bullet point 2",
      "component": "Front",
      "priority": "Highest",
      "files": ["src/..."],
      "dependencies": [],
      "estimate": 3
    }
  ]
}
```

---

## Validação Final

```python
# Verificar JSON válido
with open(output_path) as f:
    data = json.load(f)

assert "tasks" in data, "JSON deve conter 'tasks'"
assert len(data["tasks"]) > 0, "Deve ter pelo menos 1 task"

for task in data["tasks"]:
    assert "id" in task, f"Task sem 'id': {task}"
    assert "summary" in task, f"Task {task['id']} sem 'summary'"
    assert "component" in task, f"Task {task['id']} sem 'component'"

print("✅ Validação: JSON válido e completo")
```

---

## Fim do Workflow

Após Step 4, a skill termina e retorna controle ao pipeline.

**Garantias:**
- ✅ `.tasks-proposed.json` criado em `data/stories/{story_key}/`
- ✅ JSON válido e parseável
- ✅ Schema correto (fields obrigatórios)
- ✅ Tasks baseadas no contexto do pipeline-story-analyzer

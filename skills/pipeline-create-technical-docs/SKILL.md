---
name: pipeline-create-technical-docs
description: Gera documentação técnica para o Dev Pipeline Orchestrator. Lê `.doc-gen-data.json` com alterações REAIS coletadas, prioriza diffs sobre descrição Jira, e SEMPRE gera documentação completa da história. Use APENAS quando chamado pelo orquestrador em DOCUMENTATION.
---

# Pipeline Create Technical Docs

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

**Diferenças da skill original (skill-create-technical-docs):**
- ✅ Lê `.doc-gen-data.json` (alterações REAIS já coletadas)
- ✅ **PRIORIZA** diffs e PRs sobre descrição Jira
- ✅ Documenta o que FOI IMPLEMENTADO (não o que foi planejado)
- ✅ Gera documentação COMPLETA da história (não task individual)
- ✅ Output em `docs/{story_key}-technical-documentation.md`

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-create-technical-docs pipelines/tasks/{story_key}/.doc-gen-data.json
```

**O caminho relativo deve ser interpretado como:**
```
{PIPELINE_ROOT}/pipelines/tasks/{story_key}/.doc-gen-data.json
```

**REGRA:** O path relativo `pipelines/tasks/...` é relativo ao repo `onze-dev-pipeline/`, partindo do workspace root.

**Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo onze-dev-pipeline (contem .pipeline-config.json)

**SEMPRE use o caminho COMPLETO ao chamar a ferramenta Read:**
```python
Read(path="{PIPELINE_ROOT}/pipelines/tasks/{story_key}/.doc-gen-data.json")
```

---

## Input Esperado

O orquestrador já forneceu `.doc-gen-data.json`:

```json
{
  "story_key": "HUB-542",
  "files_changed": [
    "src/api/forms/router.py",
    "migrations/2024_03_add_deleted_at.sql",
    "src/components/FormPage.tsx",
    // ... 15 arquivos totais
  ],
  "critical_diffs": {
    "migrations/2024_03_add_deleted_at.sql": "ALTER TABLE forms ADD COLUMN deleted_at...",
    "src/api/forms/router.py": "- @router.post('/validate')\n+ # deprecated",
    "src/components/FormPage.tsx": "- <FormWrapper>\n..."
  },
  "db_changes": [
    {
      "type": "migration",
      "file": "migrations/2024_03_add_deleted_at.sql",
      "description": "Adicionou coluna deleted_at para soft delete"
    },
    {
      "type": "schema",
      "file": "src/models/form.py",
      "description": "+ Campo deleted_at (DateTime)"
    }
  ],
  "pr_descriptions": [
    {
      "task_key": "HUB-645",
      "pr_url": "https://github.com/org/repo/pull/789",
      "title": "Remove form validation endpoint",
      "body": "Removes POST /validate endpoint and adds soft delete logic...",
      "files_count": 5
    }
  ],
  "story_data": {
    "summary": "[Portal] Remover formulário de ajuda",
    "description": "...",
    "url": "<JIRA_URL>/browse/<PROJECT>-542"
  },
  "tasks": [
    {
      "jira_key": "HUB-645",
      "summary": "Backend: remover endpoint",
      "pr_url": "..."
    }
  ]
}
```

---

## Workflow

```
Step 1: Ler .doc-gen-data.json → 
Step 2: Analisar alterações REAIS → 
Step 3: Explorar código relevante (opcional) → 
Step 4: Gerar documentação → 
Step 5: Salvar no docs repo
```

---

## Step 1: Ler Dados Coletados

```python
import json
from pathlib import Path

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

# O usuário passa o path como argumento ou está em pipelines/tasks/{task}/
doc_gen_file = Path(f"{TASKS_DIR}/HUB-542/.doc-gen-data.json")  # path exemplo

with open(doc_gen_file) as f:
    data = json.load(f)

story_key = data["story_key"]
files_changed = data["files_changed"]
critical_diffs = data["critical_diffs"]
db_changes = data["db_changes"]
pr_descriptions = data["pr_descriptions"]
story_data = data["story_data"]
tasks = data["tasks"]
```

**Mostrar resumo:**
```
📚 Documentando História Completa: HUB-542

📊 Dados coletados:
   • Arquivos modificados: 15
   • Diffs críticos: 8
   • Alterações BD: 2 (migrations + schema)
   • PRs mergeadas: 3
   • Tasks: 3

🎯 Prioridade: Documentar alterações REAIS (não descrição Jira)
```

---

## Step 2: Analisar Alterações REAIS

### Ordem de Prioridade

1. **Diffs de arquivos** (o que FOI implementado)
2. **Descrições de PRs** (como foi implementado)
3. **Alterações de BD** (schemas, migrations)
4. **Story/Tasks Jira** (contexto e motivação - SECUNDÁRIO)

### Análise por Categoria

**Backend APIs:**
```python
backend_files = [f for f in files_changed if any(x in f for x in ["router", "handler", "service", "controller"])]

# Para cada arquivo backend, verificar:
# - Se tem diff crítico, analisar mudanças
# - Identificar endpoints adicionados/removidos/modificados
# - Extrair lógica de negócio dos diffs
```

**Database:**
```python
# db_changes já vem parseado do orquestrador
for change in db_changes:
    # change["type"] = "migration" ou "schema"
    # change["description"] = "Adicionou coluna X", "Removeu tabela Y", etc
    # Documentar impacto, queries necessárias
```

**Frontend UI:**
```python
ui_files = [f for f in files_changed if f.endswith((".tsx", ".vue", ".jsx"))]

# Para arquivos críticos (page.tsx, layout.tsx):
# - Analisar diff para entender mudança UI
# - Documentar componentes adicionados/removidos/modificados
```

**Tests:**
```python
test_files = [f for f in files_changed if "test" in f.lower()]
# Mencionar cobertura mas não detalhar
```

---

## Step 3: Explorar Código (Opcional)

**IMPORTANTE:** Alterações REAIS (diffs) têm prioridade sobre exploração.

Use exploração apenas para:
- Entender contexto de código que mudou
- Verificar como componentes se relacionam
- Buscar exemplos de uso

**Não use para:**
- ❌ Substituir informação dos diffs
- ❌ Documentar código que não mudou
- ❌ Adicionar features não implementadas

---

## Step 4: Gerar Documentação

### Estrutura Proposta

```markdown
# {story_key}: {story_title}

## 📋 Contexto

[Breve descrição da motivação - de story_data]

**Story:** [{story_key}]({story_url})
**Tasks:** {lista de tasks com links}

---

## 🔄 Alterações Implementadas

### Backend APIs ({count} arquivos)

[Listar baseado em files_changed + critical_diffs]

- `path/to/file.py`: 
  - Endpoint X removido (DEPRECATED)
  - Serviço Y adicionou lógica Z
  - [Extrair dos diffs, não inventar]

### Database ({count} alterações)

[Listar de db_changes]

**Migration:** `{migration_file}`
```sql
{extrair query do diff se disponível}
```
**Impacto:** {descrição do db_change}

**Schema:** `{schema_file}`
```python
{extrair mudanças do diff}
```

### Frontend UI ({count} componentes)

[Listar baseado em files_changed filtrados por .tsx/.vue]

- `Component.tsx`: {analisar diff para entender mudança}

### Tests ({count} arquivos)

[Mencionar cobertura]

- `test_x.py`: Atualizado para refletir mudanças
- `test_y.py`: Novos testes adicionados

---

## 📡 APIs Modificadas

[SE houver mudanças de API]

### ~~`POST /api/endpoint`~~ (DEPRECATED)
**Status:** Removido na PR #{number}
**Motivo:** {extrair de pr_descriptions}
**Migration Path:** {sugerir alternativa se aplicável}

### `GET /api/resource` (MODIFICADO)
**Antes:** {extrair do diff}
**Depois:** {extrair do diff}
**Breaking Change:** {Sim/Não - analisar}

---

## 💾 Schema Changes

[SE houver db_changes]

### Tabela `{table_name}`

- **Adicionada:** {colunas do db_change}
- **Removida:** {colunas do db_change}
- **Modificada:** {colunas do db_change}
- **Impacto:** {como queries devem ser adaptadas}

---

## 🔗 Referências

- Story: [{story_key}]({story_url})
- Tasks: {links para todas tasks}
- PRs: {links para todas PRs de pr_descriptions}
- Arquivos modificados: {count} arquivo(s)

---

**Gerado automaticamente pelo Dev Pipeline Orchestrator v1.6.0**
**Baseado em alterações reais de {len(pr_descriptions)} PR(s) mergeada(s)**
```

### Guidelines de Conteúdo

**✅ FAZER:**
- Documentar O QUE mudou (dos diffs)
- Documentar COMO mudou (dos diffs)
- Mencionar TODOS arquivos modificados
- Listar TODAS alterações de BD
- Linkar TODAS PRs e tasks
- Extrair queries SQL dos diffs de migrations
- Identificar breaking changes
- Sugerir migration paths para deprecations

**❌ NÃO FAZER:**
- Documentar código que não mudou
- Inventar informações não presentes nos diffs
- Copiar descrição Jira como única fonte
- Adicionar features não implementadas
- Documentar planos futuros
- Ignorar arquivos listados em files_changed

### Detectar Patterns Importantes

**Soft Delete:**
```python
if "deleted_at" in str(critical_diffs.values()) or any("deleted_at" in str(c) for c in db_changes):
    # Documentar padrão de soft delete
    # Mencionar impacto em queries (precisam filtrar deleted_at IS NULL)
```

**Deprecation:**
```python
if "deprecated" in str(critical_diffs.values()).lower():
    # Seção "APIs Modificadas" com migration path
```

**Refactoring:**
```python
if "refactor" in " ".join(pr["title"].lower() for pr in pr_descriptions):
    # Mencionar refactoring e motivação
```

---

## Step 5: Salvar Documentação

**Path de output:**
```python
# Docs repo (consultar local_path do repo type=docs em .pipeline-config.json)
docs_repo = Path("../onze-docs-tech")  # ver config para path correto
output_path = docs_repo / "docs" / f"{story_key}-technical-documentation.md"

# OU fallback local
output_path = Path(f"docs/{story_key}-technical-documentation.md")
```

**Validação antes de salvar:**
```python
# 1. Documento não vazio
if len(doc_content) < 500:
    raise ValueError("Documentação muito curta - provavelmente incompleta")

# 2. Menciona story key
if story_key not in doc_content:
    raise ValueError("Documentação não menciona story key")

# 3. Lista arquivos
if len([f for f in files_changed if f in doc_content]) < len(files_changed) * 0.5:
    print("⚠️  Menos de 50% dos arquivos mencionados na doc")

# 4. Documenta BD se houver mudanças
if db_changes and not any(word in doc_content.lower() for word in ["migration", "schema", "database"]):
    raise ValueError("Alterações de BD não documentadas")
```

---

## Mensagem Final

Após gerar documentação:

```
✅ Documentação técnica gerada!

📄 Arquivo: {output_path}
📏 Tamanho: {len(doc_content)} caracteres
📊 Conteúdo:
   • Arquivos documentados: {files_documented}/{len(files_changed)}
   • Alterações BD: {len(db_changes)}
   • APIs modificadas: {apis_count}
   • Componentes UI: {ui_count}
   • Blocos de código: {code_blocks}
   • Seções: {sections}

🎯 Próximo passo: Review automático (@pipeline-review-documentation)
```

---

## Exemplo de Documentação Gerada

```markdown
# HUB-542: Remover Formulário de Cadastro

## 📋 Contexto

Remoção do formulário de cadastro do portal. Durante implementação, foi decidido usar soft delete ao invés de deleção física para manter histórico auditável.

**Story:** [HUB-542](<JIRA_URL>/browse/<PROJECT>-542)
**Tasks:** [HUB-645](link), [HUB-646](link), [HUB-647](link)

---

## 🔄 Alterações Implementadas

### Backend APIs (5 arquivos)

- `forms/router.py`: 
  - ~~`POST /api/forms/validate`~~ removido (DEPRECATED)
  - Endpoint de deleção modificado para soft delete
  
- `forms/service.py`: 
  - Adicionada lógica de soft delete
  - Método `delete_form()` agora seta `deleted_at = NOW()`

- `forms/schemas.py`: 
  - Campo `deleted_at` adicionado ao FormSchema
  - Validação atualizada para aceitar nullable

### Database (2 alterações)

**Migration:** `migrations/2024_03_26_add_deleted_at.sql`

```sql
ALTER TABLE forms ADD COLUMN deleted_at TIMESTAMP NULL;
CREATE INDEX idx_forms_deleted_at ON forms(deleted_at);
```

**Impacto:** Forms não são mais deletados fisicamente. Todas queries devem filtrar `deleted_at IS NULL` para obter forms ativos.

**Schema:** `models/form.py`

```python
class Form(Base):
    # ... campos existentes
    deleted_at: datetime | None = None  # NOVO
```

### Frontend UI (4 componentes)

- `FormPage.tsx`: Removido formulário de cadastro
- `FormWrapper.tsx`: Refatorado para reutilização (oportunidade durante dev)
- `FormList.tsx`: Filtra forms com `deleted_at != null`
- `FormActions.tsx`: Botão "Delete" agora faz soft delete

### Tests (3 arquivos)

- `test_forms_api.py`: Atualizado para soft delete
- `test_form_service.py`: Novos testes de soft delete
- `FormPage.spec.tsx`: Removido (componente deletado)

---

## 📡 APIs Modificadas

### ~~`POST /api/forms/validate`~~ (DEPRECATED)

**Status:** Removido na PR #789 (HUB-645)
**Motivo:** Validação movida para backend service
**Migration Path:** Use `FormService.validate()` diretamente

### `DELETE /api/forms/{id}` (MODIFICADO)

**Antes:**
```python
# Deleção física
db.delete(form)
```

**Depois:**
```python
# Soft delete
form.deleted_at = datetime.now()
db.commit()
```

**Breaking Change:** Não. Response continua 204 No Content.

**Impacto:** Forms deletados ainda aparecem no BD. Filtrar `deleted_at IS NULL` em queries.

---

## 💾 Schema Changes

### Tabela `forms`

| Alteração | Descrição |
|-----------|-----------|
| **Adicionada** | Coluna `deleted_at TIMESTAMP NULL` |
| **Adicionado** | Índice `idx_forms_deleted_at` |
| **Impacto** | Queries devem filtrar `deleted_at IS NULL` para forms ativos |

**Exemplo de query:**
```sql
-- ANTES
SELECT * FROM forms WHERE user_id = ?;

-- DEPOIS
SELECT * FROM forms WHERE user_id = ? AND deleted_at IS NULL;
```

---

## 🔗 Referências

- Story: [HUB-542](<JIRA_URL>/browse/<PROJECT>-542)
- Tasks: [HUB-645](link), [HUB-646](link), [HUB-647](link)
- PRs: [#789](link), [#790](link), [#791](link)
- Arquivos modificados: 15 arquivo(s)

---

**Gerado automaticamente pelo Dev Pipeline Orchestrator v1.6.0**
**Baseado em alterações reais de 3 PR(s) mergeada(s)**
```

---

## Notas Importantes

1. **PRIORIZAR alterações REAIS** - diffs, PRs, BD têm prioridade sobre Jira
2. **Analisar diffs críticos** - extrair o QUE e COMO mudou
3. **Documentar breaking changes** - especialmente APIs e schemas
4. **Migration paths** - sugerir como migrar de código deprecated
5. **Impacto em queries** - se BD mudou, mostrar exemplo before/after
6. **Linkar TUDO** - story, tasks, PRs, arquivos
7. **Marcar deprecated** - usar ~~strikethrough~~ + label DEPRECATED
8. **Não inventar** - só documentar o que está nos dados coletados

---

## Diferenças da Skill Original

| Aspecto | skill-create-technical-docs | pipeline-create-technical-docs |
|---------|----------------------------|-------------------------------|
| **Trigger** | Usuário pede manualmente | Orquestrador chama automaticamente |
| **Input** | Explora codebase do zero | Recebe .doc-gen-data.json |
| **Escopo** | Módulo/sistema completo | História específica (tasks) |
| **Fonte** | Código + docs internos | Alterações REAIS (diffs + PRs) |
| **Output** | content/sistemas/... | docs/{story}-technical-documentation.md |
| **Estrutura** | Múltiplos arquivos (index, modelo, integrações) | 1 arquivo consolidado |
| **Prioridade** | Explorar código igualmente | PRIORIZAR diffs sobre descrição |
| **Validação** | Checkpoints com usuário | Review automático (@pipeline-review-documentation) |

---

## Validação Interna

Antes de finalizar:

```python
# 1. Path correto
expected_path = Path(f"docs/{story_key}-technical-documentation.md")
if not output_path.name.endswith(".md"):
    raise ValueError("Output deve ser .md")

# 2. Conteúdo mínimo
if len(doc_content) < 1000:
    raise ValueError("Doc muito curta - provavelmente incompleta")

# 3. Seções essenciais
required_sections = ["Contexto", "Alterações Implementadas", "Referências"]
for section in required_sections:
    if section not in doc_content:
        print(f"⚠️  Seção '{section}' não encontrada")

# 4. Links
if story_key not in doc_content:
    raise ValueError("Story key não mencionada")

if len([task for task in tasks if task["jira_key"] in doc_content]) < len(tasks):
    print(f"⚠️  Nem todas tasks mencionadas")

print("✅ Validação: Documentação parece completa")
```

---

## Troubleshooting

**Problema:** .doc-gen-data.json não encontrado
```
Solução: Verificar se orquestrador gerou arquivo corretamente
Path esperado: pipelines/{story}/.doc-gen-data.json
```

**Problema:** critical_diffs vazio
```
Solução: Documentação será mais superficial (só lista arquivos)
Sugerir ao usuário explorar arquivos manualmente se precisar mais detalhes
```

**Problema:** db_changes vazio mas há migrations em files_changed
```
Solução: Orquestrador pode não ter detectado
Analisar files_changed manualmente para migrations
```

---

**Versão:** 1.0.0
**Compatível com:** Dev Pipeline Orchestrator v1.6.0+
**Baseada em:** skill-create-technical-docs (standalone)

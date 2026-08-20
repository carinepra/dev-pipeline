---
name: pipeline-review-documentation
description: Review de documentação técnica para o Dev Pipeline Orchestrator. Lê `.doc-review-data.json` gerado pelo orquestrador, aplica checklist de qualidade, e SEMPRE gera `.doc-review-report.md` + `.doc-review-report.json`. Use APENAS quando chamado pelo orquestrador em DOCUMENTATION.
---

# Pipeline Review Documentation

**⚠️ Esta é uma skill ADAPTADA para o Dev Pipeline Orchestrator.**

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

**Diferenças de outras skills:**
- ✅ Lê `.doc-review-data.json` (doc path + contexto já coletado)
- ✅ **SEMPRE gera** `.doc-review-report.md` + `.doc-review-report.json`
- ✅ Review de DOCUMENTAÇÃO (não código)
- ✅ Checklist adaptativo baseado no contexto (BD, APIs, UI)
- ✅ Output estruturado para orquestrador

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-review-documentation pipelines/tasks/{story_key}/.doc-review-data.json
```

**O caminho relativo deve ser interpretado como:**
```
{PIPELINE_ROOT}/pipelines/tasks/{story_key}/.doc-review-data.json
```

**REGRA:** O path relativo `pipelines/tasks/...` é relativo ao repo `dev-pipeline/`, partindo do workspace root.

**Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo dev-pipeline (contem .pipeline-config.json)

**SEMPRE use o caminho COMPLETO ao chamar a ferramenta Read:**
```python
Read(path="{PIPELINE_ROOT}/pipelines/tasks/{story_key}/.doc-review-data.json")
```

---

## Input Esperado

O orquestrador fornece `.doc-review-data.json`:

```json
{
  "doc_path": "docs/PROJ-542-technical-documentation.md",
  "story_key": "PROJ-542",
  "context": {
    "files_count": 15,
    "tasks_count": 3,
    "has_db_changes": true,
    "has_api_changes": true,
    "has_ui_changes": true
  }
}
```

---

## Workflow

```
Step 1: Ler .doc-review-data.json → 
Step 2: Ler documentação gerada → 
Step 3: Aplicar checklist de qualidade → 
Step 4: GERAR RELATÓRIOS (.md + .json)
```

---

## Step 1: Ler Dados do Review

Ler o arquivo `.doc-review-data.json` passado pelo orquestrador:

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

# O usuário passa o path como argumento
# Exemplo: @pipeline-review-documentation analisar pipelines/tasks/PROJ-542/.doc-review-data.json
review_data_file = Path(f"{TASKS_DIR}/PROJ-542/.doc-review-data.json")  # path exemplo

with open(review_data_file) as f:
    data = json.load(f)

doc_path = Path(data["doc_path"])
story_key = data["story_key"]
context = data["context"]
```

**Mostrar resumo:**
```
📊 Review de Documentação
Story: PROJ-542
Documento: docs/PROJ-542-technical-documentation.md
Arquivos: 15
Tasks: 3
DB changes: Sim
API changes: Sim
UI changes: Sim
```

---

## Step 2: Ler Documentação Gerada

Ler o documento completo:

```python
if not doc_path.exists():
    raise FileNotFoundError(f"Documento não encontrado: {doc_path}")

doc_content = doc_path.read_text(encoding="utf-8")
```

---

## Step 3: Aplicar Checklist de Qualidade

### Checklist Base (sempre aplicado)

```python
checklist = [
    {
        "id": "title_overview",
        "description": "Título e overview claros",
        "passed": False,
        "details": ""
    },
    {
        "id": "story_context",
        "description": "Contexto da história (Jira link, motivação)",
        "passed": False,
        "details": ""
    },
    {
        "id": "files_listed",
        "description": f"Arquivos modificados listados ({context['files_count']} arquivos)",
        "passed": False,
        "details": ""
    },
    {
        "id": "pr_links",
        "description": "Links para PRs mergeadas",
        "passed": False,
        "details": ""
    },
    {
        "id": "jira_links",
        "description": "Links para tasks Jira",
        "passed": False,
        "details": ""
    },
    {
        "id": "completeness",
        "description": "Completude (cobre TODAS as alterações?)",
        "passed": False,
        "details": ""
    },
    {
        "id": "accuracy",
        "description": "Precisão (reflete alterações REAIS?)",
        "passed": False,
        "details": ""
    },
]
```

### Checklist Condicional (baseado em contexto)

```python
# Se tem mudanças de BD
if context["has_db_changes"]:
    checklist.append({
        "id": "db_documented",
        "description": "Mudanças de BD documentadas (migrations/schemas)",
        "passed": False,
        "details": ""
    })

# Se tem mudanças de API
if context["has_api_changes"]:
    checklist.append({
        "id": "apis_documented",
        "description": "APIs/endpoints documentados",
        "passed": False,
        "details": ""
    })

# Se tem mudanças de UI
if context["has_ui_changes"]:
    checklist.append({
        "id": "ui_documented",
        "description": "Componentes UI documentados",
        "passed": False,
        "details": ""
    })

# Sempre desejável
checklist.append({
    "id": "code_examples",
    "description": "Exemplos de código dos principais fluxos",
    "passed": False,
    "details": ""
})
```

### Verificar Cada Item

**Item: Título e overview**
```python
# Verificar se documento tem título claro (# PROJ-XXX: ...)
has_title = bool(re.search(r'^# PROJ-\d+:', doc_content, re.MULTILINE))

# Verificar se tem overview/contexto nas primeiras 20 linhas
first_lines = "\n".join(doc_content.split("\n")[:20])
has_overview = "contexto" in first_lines.lower() or "overview" in first_lines.lower() or "descrição" in first_lines.lower()

checklist[0]["passed"] = has_title and has_overview
checklist[0]["details"] = "Título e contexto presentes" if checklist[0]["passed"] else "Faltando título H1 ou overview inicial"
```

**Item: Contexto da história**
```python
# Verificar se menciona story Jira
has_jira_link = story_key in doc_content
has_motivation = any(word in doc_content.lower() for word in ["motivação", "motivation", "contexto", "context", "objetivo"])

checklist[1]["passed"] = has_jira_link and has_motivation
checklist[1]["details"] = "Story key e motivação presentes" if checklist[1]["passed"] else "Faltando link Jira ou motivação"
```

**Item: Arquivos listados**
```python
# Verificar se lista arquivos modificados
has_files_section = bool(re.search(r'(arquivos|files|alterações|changes)', doc_content, re.I))

# Contar menções de paths/arquivos no doc (heurística)
file_mentions = len(re.findall(r'\b\w+/[\w/]+\.(py|tsx|ts|sql|js|jsx)\b', doc_content))

# Se menciona ao menos 50% dos arquivos modificados
threshold = context["files_count"] * 0.5
checklist[2]["passed"] = has_files_section and file_mentions >= threshold
checklist[2]["details"] = f"{file_mentions} arquivos mencionados (threshold: {threshold:.0f})"
```

**Item: PRs linkadas**
```python
# Verificar se tem links para PRs
pr_links = re.findall(r'(github\.com/[^/]+/[^/]+/pull/\d+|\[#\d+\])', doc_content)

has_pr_links = len(pr_links) > 0
checklist[3]["passed"] = has_pr_links
checklist[3]["details"] = f"{len(pr_links)} PR(s) linkada(s)" if has_pr_links else "Nenhuma PR linkada"
```

**Item: Tasks Jira linkadas**
```python
# Verificar se tem links para tasks
jira_links = re.findall(r'PROJ-\d+', doc_content)
unique_jira = len(set(jira_links))

# Deve mencionar ao menos metade das tasks
threshold_tasks = max(1, context["tasks_count"] // 2)
checklist[4]["passed"] = unique_jira >= threshold_tasks
checklist[4]["details"] = f"{unique_jira} task(s) mencionada(s) (esperado: ~{context['tasks_count']})"
```

**Item: Completude**
```python
# Heurística: documento deve ter tamanho proporcional às alterações
min_chars = context["files_count"] * 100  # ~100 chars por arquivo
is_complete = len(doc_content) >= min_chars

# Verificar se tem seções estruturadas
has_sections = len(re.findall(r'^##+ ', doc_content, re.MULTILINE)) >= 3

checklist[5]["passed"] = is_complete and has_sections
checklist[5]["details"] = f"{len(doc_content)} chars, {len(re.findall(r'^##+ ', doc_content, re.MULTILINE))} seções"
```

**Item: Precisão**
```python
# Verificar se menciona "alterações reais" ou "implementado"
mentions_real = any(word in doc_content.lower() for word in ["implementad", "realizado", "mergeado", "alterações"])

# Verificar se não tem muito "futuro" (deve documentar o que FOI feito)
future_count = len(re.findall(r'\b(será|vai|irá|planejado|futuro)\b', doc_content, re.I))

checklist[6]["passed"] = mentions_real and future_count < 5
checklist[6]["details"] = "Documenta alterações implementadas" if checklist[6]["passed"] else f"Muitas menções ao futuro ({future_count})"
```

**Item condicional: BD documentado**
```python
if context["has_db_changes"]:
    # Verificar se tem seção de BD/migration/schema
    has_db_section = bool(re.search(r'(migration|schema|database|banco.*dados|bd)', doc_content, re.I))
    
    # Verificar se menciona SQL/ALTER/CREATE
    has_sql = bool(re.search(r'(CREATE|ALTER|DROP|sql)', doc_content, re.I))
    
    idx = next(i for i, item in enumerate(checklist) if item["id"] == "db_documented")
    checklist[idx]["passed"] = has_db_section and has_sql
    checklist[idx]["details"] = "Seção de BD presente com queries" if checklist[idx]["passed"] else "Faltando detalhes de BD"
```

**Item condicional: APIs documentadas**
```python
if context["has_api_changes"]:
    # Verificar se tem seção de APIs/endpoints
    has_api_section = bool(re.search(r'(api|endpoint|route)', doc_content, re.I))
    
    # Verificar se menciona HTTP methods ou paths
    has_methods = bool(re.search(r'(GET|POST|PUT|DELETE|PATCH|/api/)', doc_content))
    
    idx = next(i for i, item in enumerate(checklist) if item["id"] == "apis_documented")
    checklist[idx]["passed"] = has_api_section and has_methods
    checklist[idx]["details"] = "Endpoints documentados com métodos HTTP" if checklist[idx]["passed"] else "Faltando detalhes de API"
```

**Item condicional: UI documentada**
```python
if context["has_ui_changes"]:
    # Verificar se menciona componentes
    has_components = bool(re.search(r'(component|página|page|interface|ui)', doc_content, re.I))
    
    # Verificar se menciona arquivos .tsx/.vue
    has_ui_files = bool(re.search(r'\.(tsx|vue|jsx)', doc_content))
    
    idx = next(i for i, item in enumerate(checklist) if item["id"] == "ui_documented")
    checklist[idx]["passed"] = has_components and has_ui_files
    checklist[idx]["details"] = "Componentes UI documentados" if checklist[idx]["passed"] else "Faltando detalhes de UI"
```

**Item: Exemplos de código**
```python
# Contar blocos de código
code_blocks = len(re.findall(r'```[\w]*\n', doc_content))

idx = next(i for i, item in enumerate(checklist) if item["id"] == "code_examples")
checklist[idx]["passed"] = code_blocks >= 2
checklist[idx]["details"] = f"{code_blocks} blocos de código" if code_blocks > 0 else "Nenhum exemplo de código"
```

---

## Step 4: Calcular Score e Sugestões

### Calcular Score (0-10)

```python
passed_count = sum(1 for item in checklist if item["passed"])
total_count = len(checklist)

score = round((passed_count / total_count) * 10)
```

### Gerar Sugestões

```python
suggestions = []

# Sugestões baseadas em itens não checados
for item in checklist:
    if not item["passed"]:
        if item["id"] == "code_examples":
            suggestions.append("Adicionar exemplos de código dos principais fluxos (request/response, uso de componentes)")
        elif item["id"] == "db_documented":
            suggestions.append("Documentar migrations e schemas com queries SQL e impacto")
        elif item["id"] == "apis_documented":
            suggestions.append("Documentar endpoints com métodos HTTP, payloads e responses")
        elif item["id"] == "ui_documented":
            suggestions.append("Documentar componentes UI com props e exemplos de uso")

# Sugestões adicionais sempre bem-vindas
if context["has_ui_changes"] and "screenshot" not in doc_content.lower():
    suggestions.append("Adicionar screenshots da UI (se disponível)")

if context["has_api_changes"] and "breaking" not in doc_content.lower():
    suggestions.append("Documentar breaking changes (se houver)")

if "diagrama" not in doc_content.lower() and context["files_count"] > 10:
    suggestions.append("Considerar adicionar diagrama de arquitetura (história complexa)")
```

---

## Step 5: GERAR RELATÓRIOS (OBRIGATÓRIO)

### 5a. Gerar `.doc-review-report.md`

Este arquivo é para humanos lerem:

```markdown
# Review de Documentação: {story_key}

**Score:** {score}/10
**Data:** {datetime.now().strftime("%Y-%m-%d %H:%M")}
**Documento:** {doc_path}

---

## ✅ Checklist de Qualidade

{for each item in checklist:}
- [{x if passed else " "}] {description}
  {if details: "  → " + details}

---

## 💡 Sugestões de Melhoria

{if suggestions:}
{for suggestion in suggestions:}
{idx}. {suggestion}
{else:}
Nenhuma sugestão - documentação está completa!

---

## 📊 Estatísticas

- Arquivos documentados: {context["files_count"]}
- Tasks cobertas: {context["tasks_count"]}
- Alterações BD: {"Sim" if context["has_db_changes"] else "Não"}
- Alterações API: {"Sim" if context["has_api_changes"] else "Não"}
- Alterações UI: {"Sim" if context["has_ui_changes"] else "Não"}
- Tamanho do documento: {len(doc_content)} caracteres
- Blocos de código: {code_blocks}
- Seções: {len(re.findall(r'^##+ ', doc_content, re.MULTILINE))}

---

**Gerado por:** pipeline-review-documentation
**Versão:** 1.0.0
```

**Path obrigatório:** `pipelines/{story_key}/.doc-review-report.md`

### 5b. Gerar `.doc-review-report.json`

Este arquivo é para o orquestrador ler:

```json
{
  "story_key": "PROJ-542",
  "doc_path": "docs/PROJ-542-technical-documentation.md",
  "score": 9,
  "checklist": [
    {
      "id": "title_overview",
      "description": "Título e overview claros",
      "passed": true,
      "details": "Título e contexto presentes"
    },
    // ... todos itens
  ],
  "suggestions": [
    "Adicionar exemplo de soft delete no frontend",
    "Adicionar screenshot do estado deletado"
  ],
  "stats": {
    "passed_count": 10,
    "total_count": 11,
    "doc_size": 3542,
    "code_blocks": 5,
    "sections": 8
  },
  "reviewed_at": "2026-03-30T15:30:00",
  "version": "1.0.0"
}
```

**Path obrigatório:** `pipelines/{story_key}/.doc-review-report.json`

---

## Mensagem Final

Após gerar ambos arquivos, mostrar:

```
✅ Review de documentação concluído!

📊 Score: {score}/10
📋 Checklist: {passed_count}/{total_count} itens aprovados

Arquivos gerados:
  ✅ .doc-review-report.md (relatório humano)
  ✅ .doc-review-report.json (para orquestrador)

{if score >= 8:}
🎉 Documentação de boa qualidade! Pronta para PR.
{elif score >= 6:}
⚠️  Documentação aceitável, mas considere melhorias.
{else:}
❌ Documentação precisa de melhorias significativas.

{if suggestions:}
💡 Sugestões:
{for suggestion in suggestions:}
  • {suggestion}
```

---

## Exemplo de Execução

```bash
# Chamada pelo orquestrador
@pipeline-review-documentation analisar pipelines/tasks/PROJ-542/.doc-review-data.json

📊 Review de Documentação
Story: PROJ-542
Documento: docs/PROJ-542-technical-documentation.md
Arquivos: 15 | Tasks: 3 | BD: Sim | API: Sim | UI: Sim

🔍 Analisando documentação...

✅ Checklist de Qualidade:
  ✅ Título e overview claros
  ✅ Contexto da história presente
  ✅ Arquivos modificados listados (15 arquivos)
  ✅ Mudanças de BD documentadas
  ✅ APIs documentadas
  ✅ Componentes UI documentados
  ⚠️  Exemplos de código (2 blocos - adicionar mais seria melhor)
  ✅ Links para PRs
  ✅ Links para Jira
  ✅ Completude
  ✅ Precisão

📊 Score: 9/10

💡 Sugestões:
  1. Adicionar exemplo de soft delete no frontend
  2. Adicionar screenshot do estado deletado

✅ Relatórios gerados:
  • .doc-review-report.md
  • .doc-review-report.json
```

---

## Validação Interna (CRÍTICA)

Antes de finalizar, verificar:

```python
output_dir = review_data_file.parent

report_md = output_dir / ".doc-review-report.md"
report_json = output_dir / ".doc-review-report.json"

# CRÍTICO: Ambos arquivos DEVEM existir
if not report_md.exists():
    raise FileNotFoundError(f"ERRO: {report_md} não foi gerado!")

if not report_json.exists():
    raise FileNotFoundError(f"ERRO: {report_json} não foi gerado!")

# Validar JSON
with open(report_json) as f:
    data = json.load(f)
    
    # Campos obrigatórios
    required = ["story_key", "score", "checklist", "suggestions"]
    for field in required:
        if field not in data:
            raise ValueError(f"Campo obrigatório faltando no JSON: {field}")

print("✅ Validação: Ambos arquivos gerados corretamente")
```

---

## Notas Importantes

1. **SEMPRE gerar ambos arquivos** (.md + .json) - orquestrador depende do .json
2. **Checklist adaptativo** - varia baseado no contexto (BD, API, UI)
3. **Score justo** - baseado em itens realmente aplicáveis (não penalizar por não ter BD se não modificou BD)
4. **Sugestões acionáveis** - específicas e práticas
5. **Paths fixos** - sempre em `pipelines/stories/{story_key}/`

---

## Troubleshooting

**Problema:** Documento não encontrado
```
Solução: Verificar se doc_path está correto e se arquivo existe
```

**Problema:** JSON de input inválido
```
Solução: Verificar se orquestrador gerou .doc-review-data.json corretamente
```

**Problema:** Score muito baixo (< 4)
```
Solução: Doc provavelmente está muito incompleta - avisar usuário
```

---

**Versão:** 1.0.0
**Compatível com:** Dev Pipeline Orchestrator v1.6.0+

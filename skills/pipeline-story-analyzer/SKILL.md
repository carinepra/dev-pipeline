---
name: pipeline-story-analyzer
description: Análise completa e planejamento estratégico para o Dev Pipeline. Busca Figma + docs + codebase, consolida contexto, executa sanity checks, valida com usuário, e gera .story-plan.md estruturado.
---

# Pipeline Story Analyzer

**🌐 IMPORTANTE: Toda a comunicação com o usuário DEVE ser em PORTUGUÊS (PT-BR).**

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrator.**

## 📁 Estrutura de Repositórios (IMPORTANTE)

**📋 Config:** Leia `.pipeline-config.json` na raiz do repo `onze-dev-pipeline` para descobrir repos, paths de docs e projeto atual.

**Contextos de uso:**

### Quando chamada pelo ORQUESTRADOR (Pipeline):
- **Working directory:** o workspace root do Cursor (diretório raiz com todos os repos)
- **Variáveis de template:** `{WORKSPACE_ROOT}` = pasta pai dos repos | `{PIPELINE_ROOT}` = repo onze-dev-pipeline (contem .pipeline-config.json)
- **Repositórios disponíveis como subdiretórios:**
  - Consulte `repositories` em `.pipeline-config.json` para paths dos repos
  - Cada repo tem `local_path`, `type` e `tech_stack`

**⚠️ Ao explorar código:** Use paths relativos. Consulte `local_path` de cada repo no `.pipeline-config.json`.

### Quando usada PONTUALMENTE (standalone):
- **Working directory:** Dentro de um repo específico
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

**Diferenças da skill original:**
- ✅ **SEMPRE gera** `.story-plan.md` com YAML frontmatter
- ✅ **Análise automática** de 3 fontes em paralelo
- ✅ **Sanity checks práticos** (não "mágicos")
- ✅ **Validação robusta** antes de salvar
- ✅ **Entra em modo Plan** automaticamente
- ✅ **Usa AskQuestion** para validações e decisões
- ✅ **Invoca pipeline-plan-validator automaticamente** (Step 7)

---

## Input Esperado

O orquestrador fornece:
- `story_key`: `<PROJECT>-XXX`
- `story_data`: 
  ```python
  {
    "summary": "...",
    "description": "...",
    "acceptance_criteria": [...],
    "scope": "backend" | "frontend" | "both"  # JÁ DEFINIDO
  }
  ```

**NÃO perguntar escopo** - já foi definido pelo pipeline.

---

## Workflow

```
Step 0: Ativar Modo Plan
   ↓
Step 1: Análise Automática (3 fontes)
   ↓
Step 2: Consolidar Contexto
   ↓
Step 3: Sanity Checks Simples
   ↓
Step 4: Validar com Usuário (AskQuestion)
   ↓
Step 5: Decisões Técnicas (AskQuestion)
   ↓
Step 6: GERAR .story-plan.md
   ↓
Step 7: Melhorar Plano Automaticamente (pipeline-plan-validator)
```

---

## Step 0: Ativar Modo Plan

**OBRIGATÓRIO: Logo no início da skill, entre em modo Plan.**

Use `SwitchMode` com:
- target_mode_id: "plan"
- explanation: "Vamos planejar estrategicamente a história antes de quebrar em tasks"

**Benefícios:**
- Discussão colaborativa sobre decisões arquiteturais
- Usuário pode revisar análise e contexto antes de prosseguir
- Pensamento focado sem risco de implementação prematura

---

## Step 1: Análise Automática (Silenciosa)

**Executar em paralelo (SEM perguntar):**

### 1.1 Figma (se houver link)

```python
import re

# Usar campo direto figma_links (já extraído do Jira customfield_11000)
figma_links = story_data.get('figma_links', [])

if figma_links and len(figma_links) > 0:
    figma_url = figma_links[0]  # Usar primeiro link
    
    # Extrair file_key e node_id
    figma_pattern = r'figma\.com/(file|design)/([a-zA-Z0-9]+)'
    node_pattern = r'node-id=([I\d:;%\d-]+)'
    
    figma_match = re.search(figma_pattern, figma_url)
    
    if figma_match:
        file_key = figma_match.group(2)
        node_match = re.search(node_pattern, figma_url)
        node_id = node_match.group(1) if node_match else None
        
        print("🎨 Analisando design Figma...")
        
        try:
            # Chamar MCP Figma
            figma_data = CallMcpTool(
                server="user-figma",
                toolName="get_figma_data",
                arguments={
                    "fileKey": file_key,
                    "nodeId": node_id
                }
            )
            
            # Extrair APENAS o essencial (MVP)
            figma_context = {
                "file_key": file_key,
                "file_name": figma_data.get("name", "Unknown"),
                "url": figma_url,
                "frames": extract_frame_names(figma_data),  # Top-level frames
                "texts": extract_text_nodes(figma_data)      # Textos principais
            }
            
            print(f"✅ Figma: {figma_context['file_name']}")
            print(f"   Frames: {', '.join(figma_context['frames'][:3])}")
            
        except Exception as e:
            print(f"⚠️ Figma inacessível: {str(e)[:50]}")
            figma_context = None
    else:
        print("⚠️ Link do Figma mal formatado")
        figma_context = None
else:
    print("ℹ️ Nenhum link do Figma detectado na issue")
    figma_context = None
```

**Funções auxiliares:**

```python
def extract_frame_names(figma_data):
    """Extrai nomes de frames top-level"""
    frames = []
    document = figma_data.get("document", {})
    
    for canvas in document.get("children", []):
        if canvas.get("type") == "CANVAS":
            for node in canvas.get("children", []):
                if node.get("type") == "FRAME":
                    frames.append(node.get("name", "Unnamed"))
    
    return frames[:5]  # Top 5

def extract_text_nodes(figma_data):
    """Extrai textos principais (DFS até depth 3)"""
    texts = []
    
    def dfs(node, depth=0):
        if depth > 3:
            return
        
        if node.get("type") == "TEXT":
            chars = node.get("characters", "").strip()
            if chars and len(chars) > 2:  # Ignorar textos muito curtos
                texts.append(chars)
        
        for child in node.get("children", []):
            dfs(child, depth + 1)
    
    document = figma_data.get("document", {})
    dfs(document)
    
    return texts[:10]  # Top 10 textos
```

---

### 1.2 Documentação Técnica (se houver docs configurados)

**Instrução:** Leia `docs_search_paths` do projeto em `.pipeline-config.json` e busque docs nesses paths. Resolva caminhos relativos ao workspace root ou ao `local_path` dos repos em `repositories`.

```python
scope = story_data["scope"]

if scope in ["backend", "frontend", "both"]:
    print("📚 Buscando regras de negócio na documentação do projeto...")
    
    from pathlib import Path
    import json
    import os
    
    workspace_root = Path(os.getcwd()).resolve()
    docs_context = None
    
    config_path = workspace_root / ".pipeline-config.json"
    if not config_path.exists():
        config_path = workspace_root / "onze-dev-pipeline" / ".pipeline-config.json"
    
    search_paths = []
    if config_path.exists():
        config = json.loads(config_path.read_text())
        # Obter docs_search_paths do projeto atual; resolver cada entrada para diretório existente
        # Ex.: paths relativos ao workspace ou combinados com local_path dos repos
        # search_paths = resolve_docs_search_paths(config, workspace_root)
        pass
    
    if not search_paths:
        print("⚠️ docs_search_paths vazio ou paths não encontrados no workspace")
        docs_context = None
    else:
        try:
            query = f"{story_data['summary']} - regras de negócio, validações, estados"
            results = SemanticSearch(
                query=query,
                target_directories=search_paths,
                num_results=3
            )
            if results and len(results) > 0:
                docs_context = {
                    "found": True,
                    "pages": [r.get("path") for r in results],
                    "snippets": [r.get("content")[:200] for r in results]
                }
                print(f"✅ Encontrado: {len(results)} páginas relevantes")
                print(f"   - {docs_context['pages'][0]}")
            else:
                print("ℹ️ Nenhuma doc específica encontrada (pode estar OK)")
                docs_context = None
        except Exception as e:
            print(f"⚠️ Erro ao buscar docs: {str(e)[:50]}")
            docs_context = None
else:
    print("ℹ️ Escopo sem docs configurados, pulando busca em docs")
    docs_context = None
```

---

### 1.3 Codebase (sempre)

```python
print("💻 Explorando codebase...")

# Estratégia baseada no escopo
if scope == "backend":
    explore_strategy = {
        "patterns": ["*Handler.py", "*Service.py", "app/entities/*.py"],
        "keywords": ["handler", "service", "entity"],
        "search_query": f"Como implementar {story_data['summary']} no backend?"
    }
elif scope == "frontend":
    explore_strategy = {
        "patterns": ["*.tsx", "*.ts", "src/components/**", "src/hooks/**"],
        "keywords": ["component", "hook", "page"],
        "search_query": f"Componente similar a {story_data['summary']}"
    }
else:  # both
    explore_strategy = {
        "patterns": ["*Handler.py", "*.tsx"],
        "keywords": ["handler", "component"],
        "search_query": f"Implementação de {story_data['summary']}"
    }

# Buscar padrões similares
similar_files = []

# 1. Glob por padrões
for pattern in explore_strategy["patterns"]:
    files = Glob(pattern)
    similar_files.extend(files[:2])  # Top 2 de cada padrão

# 2. Semantic search (se nada encontrado)
if len(similar_files) == 0:
    results = SemanticSearch(
        query=explore_strategy["search_query"],
        target_directories=[],  # Todo o repo
        num_results=3
    )
    similar_files = [r.get("path") for r in results]

# 3. Extrair código reutilizável (ler arquivos similares)
reusable_code = {
    "services": [],
    "hooks": [],
    "components": [],
    "utils": []
}

for file_path in similar_files[:3]:  # Só primeiros 3
    content = Read(file_path, limit=50)  # Primeiras 50 linhas
    
    # Extrair exports (simples regex)
    if scope == "backend":
        # Python: def function_name, class ClassName
        functions = re.findall(r'def (\w+)\(', content)
        classes = re.findall(r'class (\w+)', content)
        reusable_code["services"].extend(functions + classes)
    else:
        # TypeScript: export const/function
        exports = re.findall(r'export (?:const|function) (\w+)', content)
        if "hook" in file_path:
            reusable_code["hooks"].extend(exports)
        elif "component" in file_path:
            reusable_code["components"].extend(exports)
        else:
            reusable_code["utils"].extend(exports)

codebase_context = {
    "similar_files": similar_files[:5],
    "reusable_code": {k: list(set(v))[:5] for k, v in reusable_code.items()},
    "suggested_dir": get_suggested_directory(scope),
    "naming_pattern": "PascalCase" if scope != "backend" else "snake_case"
}

if similar_files:
    print(f"✅ Encontrado: {len(similar_files)} arquivos similares")
    print(f"   - {similar_files[0]}")
else:
    print("ℹ️ Nenhum padrão similar (implementar do zero)")

print(f"   Sugestão: {codebase_context['suggested_dir']}")
```

**Função auxiliar:**

```python
def get_suggested_directory(scope):
    """Retorna diretório sugerido baseado no escopo"""
    if scope == "backend":
        return "app/handlers/" # ou app/service/
    elif scope == "frontend":
        return "src/components/" # ou src/app/
    else:
        return "backend: app/handlers/, frontend: src/components/"
```

---

## Step 2: Consolidar Contexto

Apresentar resumo estruturado:

```python
print("\n" + "="*60)
print("📋 CONTEXTO COMPLETO COLETADO")
print("="*60 + "\n")

print("## 📖 História (Jira)")
print(f"- Key: {story_key}")
print(f"- Summary: {story_data['summary']}")
print(f"- Tipo: {story_data.get('type', 'Story')}")
print(f"- Escopo: {story_data['scope']}")

# Validar ACs
acs = story_data.get('acceptance_criteria', [])
has_valid_acs = False

if acs and len(acs) > 0:
    # Verificar se são placeholders vazios ou apenas "---"
    valid_acs = [ac for ac in acs if ac.strip() and ac.strip() != '---' and len(ac.strip()) > 3]
    if valid_acs:
        has_valid_acs = True
        print("\nAcceptance Criteria:")
        for i, ac in enumerate(valid_acs, 1):
            print(f"  {i}. {ac}")
    else:
        print("\n⚠️ Acceptance Criteria: Vazios ou placeholders")
        print("   A história não tem ACs definidos no Jira")
else:
    print("\n⚠️ Acceptance Criteria: Não encontrados no Jira")
    print("   Considere adicionar critérios claros antes de quebrar em tasks")

print("\n## 🎨 Design (Figma)")
if figma_context:
    print(f"✅ Arquivo: {figma_context['file_name']}")
    print(f"✅ Link: {figma_context['url']}")
    print(f"\nFrames: {', '.join(figma_context['frames'])}")
    print(f"Textos: {', '.join(figma_context['texts'][:5])}")
else:
    print("ℹ️ Nenhum link do Figma detectado")

print("\n## 📚 Regras de Negócio (docs do projeto)")
if docs_context:
    print(f"✅ Encontrado: {len(docs_context['pages'])} páginas")
    for page in docs_context['pages']:
        print(f"  - {page}")
else:
    print("ℹ️ Nenhuma documentação específica encontrada")

print("\n## 💻 Arquitetura (Codebase)")
print(f"✅ Escopo: {scope}")

if codebase_context['similar_files']:
    print(f"\nPadrões similares:")
    for file in codebase_context['similar_files']:
        print(f"  - {file}")
    
    print(f"\nCódigo reutilizável:")
    for category, items in codebase_context['reusable_code'].items():
        if items:
            print(f"  {category.capitalize()}: {', '.join(items)}")
else:
    print("ℹ️ Nenhum padrão similar encontrado (implementar do zero)")

print(f"\nDiretório sugerido: {codebase_context['suggested_dir']}")
print(f"Padrão de nomeação: {codebase_context['naming_pattern']}")
```

---

## Step 3: Sanity Checks Simples

**Checks práticos (não "mágicos"):**

```python
print("\n" + "="*60)
print("⚠️ SANITY CHECKS")
print("="*60 + "\n")

checks = []

# 0. Validar ACs (se estão definidos)
acs = story_data.get('acceptance_criteria', [])
valid_acs = [ac for ac in acs if ac.strip() and ac.strip() != '---' and len(ac.strip()) > 3]

if not valid_acs or len(valid_acs) == 0:
    checks.append({
        "name": "Acceptance Criteria",
        "passed": False,
        "message": "⚠️ ACs vazios ou não definidos no Jira. Considere adicioná-los antes de continuar."
    })
else:
    checks.append({
        "name": "Acceptance Criteria",
        "passed": True,
        "message": f"✅ {len(valid_acs)} critério(s) de aceitação definido(s)"
    })

# 1. Figma vs ACs (contar elementos)
if figma_context:
    figma_frame_count = len(figma_context['frames'])
    figma_text_count = len(figma_context['texts'])
    ac_count = len(story_data.get('acceptance_criteria', []))
    
    if figma_frame_count > 0:
        checks.append({
            "name": "Figma detectado",
            "passed": True,
            "message": f"✅ {figma_frame_count} frame(s), {figma_text_count} texto(s)"
        })
    
    # Avisar se há muitos frames mas poucos ACs
    if figma_frame_count > ac_count + 2:
        checks.append({
            "name": "Figma vs ACs",
            "passed": False,
            "message": f"⚠️ Figma tem {figma_frame_count} frames mas apenas {ac_count} ACs. Verificar se está completo."
        })

# 2. Docs encontradas
if docs_context:
    checks.append({
        "name": "Documentação",
        "passed": True,
        "message": f"✅ Encontradas {len(docs_context['pages'])} páginas relevantes"
    })
else:
    checks.append({
        "name": "Documentação",
        "passed": True,  # OK não encontrar
        "message": "ℹ️ Nenhuma doc específica (pode estar OK)"
    })

# 3. Padrão similar no codebase
if codebase_context['similar_files']:
    checks.append({
        "name": "Padrão similar",
        "passed": True,
        "message": f"✅ Encontrados {len(codebase_context['similar_files'])} arquivos similares (pode reutilizar)"
    })
else:
    checks.append({
        "name": "Padrão similar",
        "passed": True,  # OK não encontrar
        "message": "ℹ️ Nenhum padrão similar (implementar do zero)"
    })

# Mostrar checks
for check in checks:
    print(check['message'])
```

**NÃO tentar "detectar conflitos" automaticamente** - deixar usuário identificar no Step 4.

---

## Step 4: Validar com Usuário (AskQuestion)

**USE `AskQuestion` para validar o contexto coletado.**

```python
print("\n" + "="*60)
print("🔍 VALIDAÇÃO DO CONTEXTO")
print("="*60 + "\n")

print("Revise o contexto acima antes de prosseguir.\n")
```

**Preparar perguntas baseadas no que foi encontrado:**

```json
{
  "title": "Validação do Contexto Coletado",
  "questions": [
    {
      "id": "context_complete",
      "prompt": "O contexto coletado está correto e completo?",
      "options": [
        {"id": "yes", "label": "Sim, está completo"},
        {"id": "missing", "label": "Falta informação importante"},
        {"id": "incorrect", "label": "Há informação incorreta"}
      ],
      "allow_multiple": false
    },
    {
      "id": "has_conflicts",
      "prompt": "Há algum conflito entre Figma, docs ou ACs? (Ex: Figma mostra X mas docs especificam Y)",
      "options": [
        {"id": "no", "label": "Não, tudo consistente"},
        {"id": "yes_figma_docs", "label": "Sim, conflito entre Figma e docs"},
        {"id": "yes_figma_acs", "label": "Sim, conflito entre Figma e ACs"},
        {"id": "yes_docs_acs", "label": "Sim, conflito entre docs e ACs"},
        {"id": "yes_multiple", "label": "Sim, múltiplos conflitos"}
      ],
      "allow_multiple": false
    }
  ]
}
```

**Processar respostas:**

```python
manual_additions = []
conflict_resolutions = []

# Se contexto incompleto, coletar o que falta via mensagem
if answers["context_complete"] in ["missing", "incorrect"]:
    print("\n💡 Por favor, descreva o que está faltando ou incorreto:")
    print("   (Use a caixa de texto para detalhar)")
    # Usuário responde via mensagem de texto

# Se há conflitos, coletar resolução via mensagem
if answers["has_conflicts"] != "no":
    print(f"\n💡 Conflito identificado: {answers['has_conflicts']}")
    print("   Por favor, descreva o conflito e como resolvê-lo:")
    print("   (Use a caixa de texto para detalhar)")
    # Usuário responde via mensagem de texto
```

---

## Step 5: Decisões Técnicas (AskQuestion)

**USE `AskQuestion` para coletar decisões arquiteturais importantes.**

```python
print("\n" + "="*60)
print("🤔 DECISÕES TÉCNICAS")
print("="*60 + "\n")
```

**Preparar perguntas dinamicamente baseadas no contexto:**

```json
{
  "title": "Decisões Técnicas da História",
  "questions": [
    // Pergunta 1: Reutilização (se houver código similar)
    {
      "id": "reuse_code",
      "prompt": "Padrão similar encontrado: {similar_file}. Reutilizar esse código?",
      "options": [
        {"id": "yes", "label": "Sim, reutilizar e adaptar"},
        {"id": "no", "label": "Não, implementar do zero"},
        {"id": "partial", "label": "Reutilizar apenas estrutura/lógica base"}
      ],
      "allow_multiple": false
    },
    
    // Pergunta 2: Escopo da história (SEMPRE perguntar)
    {
      "id": "scope_phase",
      "prompt": "O que implementar AGORA nesta história vs deixar para próximas?",
      "options": [
        {"id": "minimal", "label": "MVP mínimo - apenas o core funcional"},
        {"id": "complete", "label": "Feature completa - tudo que foi especificado"},
        {"id": "phased", "label": "Faseado - vou descrever o que entra agora"}
      ],
      "allow_multiple": false
    },
    
    // Pergunta 3: Abordagem técnica (se houver múltiplas opções)
    {
      "id": "technical_approach",
      "prompt": "Qual abordagem técnica usar? (escolha baseada no contexto)",
      "options": [
        {"id": "approach_a", "label": "Opção A: [descrição]"},
        {"id": "approach_b", "label": "Opção B: [descrição]"},
        {"id": "approach_c", "label": "Opção C: [descrição]"}
      ],
      "allow_multiple": false
    }
  ]
}
```

**⚠️ IMPORTANTE:** 
- Adapte as perguntas conforme o contexto específico
- Se não houver código similar, pule a pergunta de reutilização
- Se não houver múltiplas abordagens, pule a pergunta técnica
- SEMPRE pergunte sobre o escopo da história

**Processar respostas:**

```python
decisions = {}

# Mapear respostas para decisões
if "reuse_code" in answers:
    decisions["reuse"] = answers["reuse_code"] == "yes"
    if decisions["reuse"]:
        decisions["reuse_file"] = codebase_context['similar_files'][0]
    elif answers["reuse_code"] == "partial":
        decisions["reuse"] = "partial"
        decisions["reuse_file"] = codebase_context['similar_files'][0]
else:
    decisions["reuse"] = False

# Escopo
if answers["scope_phase"] == "phased":
    print("\n💡 Descreva o que entra nesta fase:")
    # Usuário responde via mensagem de texto
    # decisions["scope_definition"] = resposta do usuário
else:
    decisions["scope_definition"] = {
        "minimal": "MVP mínimo - apenas core funcional",
        "complete": "Feature completa conforme especificação"
    }[answers["scope_phase"]]

# Abordagem técnica
if "technical_approach" in answers:
    decisions["approach"] = answers["technical_approach"]

print("\n✅ Decisões registradas")
```

---

## Step 6: GERAR .story-plan.md (YAML + Markdown)

```python
from datetime import datetime
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

output_path = Path(f"{STORIES_DIR}/{story_key}/.story-plan.md")

# Preparar dados YAML
yaml_data = {
    "story_key": story_key,
    "generated_at": datetime.now().isoformat(),
    "validated": True,
    "scope": story_data["scope"],
    
    "context": {
        "figma": {
            "has_figma": bool(figma_context),
            **(figma_context if figma_context else {}),
            "summary_one_line": (
                f"{figma_context['file_name']}: {', '.join(figma_context['frames'][:2])}"
                if figma_context else "N/A"
            )
        },
        "docs": {
            "has_docs": bool(docs_context),
            "pages": docs_context["pages"] if docs_context else [],
            "summary_one_line": (
                f"{len(docs_context['pages'])} páginas relevantes"
                if docs_context else "N/A"
            )
        },
        "codebase": {
            "similar_files": codebase_context["similar_files"],
            "reusable_code": codebase_context["reusable_code"],
            "suggested_dir": codebase_context["suggested_dir"],
            "summary_one_line": (
                f"Reutilizar {codebase_context['similar_files'][0].split('/')[-1]}"
                if codebase_context['similar_files'] else "Implementar do zero"
            )
        }
    },
    
    "sanity_checks": {
        check["name"]: {
            "passed": check["passed"],
            "message": check["message"]
        }
        for check in checks
    },
    
    "manual_additions": manual_additions,
    
    "conflicts": conflict_resolutions,
    
    "decisions": decisions
}

# Gerar conteúdo
content = f"""---
{yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False)}---

# Story Plan: {story_key}

**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Validado:** ✅ Sim

---

## 📋 História

- **Key:** {story_key}
- **Summary:** {story_data['summary']}
- **Escopo:** {story_data['scope']}

**Acceptance Criteria:**
{chr(10).join(f'{i}. {ac}' for i, ac in enumerate(story_data.get('acceptance_criteria', []), 1))}

---

## 🎨 Design (Figma)

{format_figma_section(figma_context)}

---

## 📚 Regras de Negócio (docs do projeto)

{format_docs_section(docs_context)}

---

## 💻 Arquitetura (Codebase)

{format_codebase_section(codebase_context)}

---

## ⚠️ Sanity Checks

{chr(10).join(f"- {c['message']}" for c in checks)}

---

## 🔍 Validações

{format_validations(manual_additions, conflict_resolutions)}

---

## 🤔 Decisões Técnicas

{format_decisions(decisions)}

---

## 📝 Para Task Creator

**Usar este contexto ao propor tasks:**

- **Design:** {yaml_data['context']['figma']['summary_one_line']}
- **Regras:** {yaml_data['context']['docs']['summary_one_line']}
- **Código:** {yaml_data['context']['codebase']['summary_one_line']}
- **Reutilizar:** {'Sim - ' + decisions.get('reuse_file', 'N/A') if decisions.get('reuse') else 'Não'}
- **Escopo:** {decisions.get('scope_definition', 'Não especificado')}
- **Approach:** {decisions.get('approach', 'Padrão')}
"""

# Salvar arquivo
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(content, encoding='utf-8')

print(f"\n✅ Plano salvo: {output_path}")
print(f"   Tamanho: {len(content)} chars")
print(f"   Validado: ✅ Sim")

# TAMBÉM atualizar estado do pipeline
update_pipeline_state(story_key, output_path, yaml_data)
```

**Funções auxiliares de formatação:**

```python
def format_figma_section(figma_context):
    if not figma_context:
        return "ℹ️ Nenhum link do Figma detectado"
    
    return f"""
✅ **Arquivo:** {figma_context['file_name']}  
✅ **Link:** {figma_context['url']}

**Frames:**
{chr(10).join(f'- {f}' for f in figma_context['frames'])}

**Textos principais:**
{chr(10).join(f'- "{t}"' for t in figma_context['texts'][:5])}
"""

def format_docs_section(docs_context):
    if not docs_context:
        return "ℹ️ Nenhuma documentação específica encontrada"
    
    return f"""
✅ **Encontrado:** {len(docs_context['pages'])} páginas

**Páginas:**
{chr(10).join(f'- `{p}`' for p in docs_context['pages'])}
"""

def format_codebase_section(codebase_context):
    sections = []
    
    if codebase_context['similar_files']:
        sections.append("**Padrões similares:**")
        sections.extend(f"- `{f}`" for f in codebase_context['similar_files'])
    
    reusable = codebase_context['reusable_code']
    if any(reusable.values()):
        sections.append("\n**Código reutilizável:**")
        for category, items in reusable.items():
            if items:
                sections.append(f"- {category.capitalize()}: {', '.join(f'`{i}`' for i in items)}")
    
    sections.append(f"\n**Diretório sugerido:** `{codebase_context['suggested_dir']}`")
    sections.append(f"**Padrão de nomeação:** `{codebase_context['naming_pattern']}`")
    
    return chr(10).join(sections)

def format_validations(manual_additions, conflict_resolutions):
    sections = []
    
    if manual_additions:
        sections.append("**Adições manuais:**")
        sections.extend(f"- {a}" for a in manual_additions)
    
    if conflict_resolutions:
        sections.append("\n**Conflitos resolvidos:**")
        for c in conflict_resolutions:
            sections.append(f"- **Conflito:** {c['conflict']}")
            sections.append(f"  **Resolução:** {c['resolution']}")
    
    if not sections:
        sections.append("✅ Contexto validado sem correções")
    
    return chr(10).join(sections)

def format_decisions(decisions):
    sections = []
    
    sections.append(f"**Reutilizar código:** {'✅ Sim' if decisions.get('reuse') else '❌ Não'}")
    
    if decisions.get('reuse'):
        sections.append(f"  - Arquivo: `{decisions.get('reuse_file')}`")
    
    sections.append(f"\n**Escopo da história:**")
    sections.append(f"  {decisions.get('scope_definition', 'Não especificado')}")
    
    if decisions.get('approach'):
        sections.append(f"\n**Abordagem técnica:**")
        sections.append(f"  {decisions['approach']}")
    
    return chr(10).join(sections)

def update_pipeline_state(story_key, plan_path, plan_data):
    """Atualiza .pipeline-state/{story_key}-pipeline.json"""
    import json
    
    state_file = Path(f".pipeline-state/{story_key}-pipeline.json")
    
    if not state_file.exists():
        print(f"⚠️ Estado do pipeline não encontrado: {state_file}")
        return
    
    try:
        with open(state_file, 'r+') as f:
            state = json.load(f)
            
            state["story_plan"] = {
                "generated_at": plan_data["generated_at"],
                "path": str(plan_path),
                "validated": True,
                "has_figma": plan_data["context"]["figma"]["has_figma"],
                "has_docs": plan_data["context"]["docs"]["has_docs"],
                "has_conflicts": len(plan_data["conflicts"]) > 0
            }
            
            f.seek(0)
            f.truncate()
            json.dump(state, f, indent=2)
        
        print(f"✅ Estado do pipeline atualizado: {state_file}")
        
    except Exception as e:
        print(f"⚠️ Erro ao atualizar estado: {e}")
```

---

## Step 7: Melhorar Plano Automaticamente (pipeline-plan-validator)

**⚡ AUTOMATIZAÇÃO:** Após criar o plano (Step 6), chamar automaticamente a skill de melhoria.

### 7.1. Informar usuário

```python
from pathlib import Path

plan_file = Path(f"{STORIES_DIR}/{story_key}/.story-plan.md")

print("\n" + "="*60)
print("✅ PLANO CRIADO")
print("="*60)
print(f"📄 Arquivo: {plan_file}")
print(f"📊 Tamanho: {plan_file.stat().st_size} bytes")
print("\n🔄 Executando pipeline-plan-validator automaticamente...")
print("   (3 rounds de análise crítica)")
print("="*60 + "\n")
```

### 7.2. Invocar skill automaticamente

Executar automaticamente (sem precisar do usuário):

```
@pipeline-plan-validator melhorar pipelines/stories/{story_key}/.story-plan.md
```

**O que essa skill fará:**
- Round 1: Perspectiva do implementador (gaps, arquivos, dependências)
- Round 2: Perspectiva do tech lead (arquitetura, riscos, manutenção)
- Round 3: Perspectiva do advogado do diabo (edge cases, falhas)
- Aplicará melhorias in-place no arquivo

### 7.3. Confirmar sucesso

Após a skill `pipeline-plan-validator` concluir:

```python
print("\n" + "="*60)
print("✅ PLANO MELHORADO (3 rounds concluídos)")
print("="*60)
print(f"📄 Arquivo final: {plan_file}")
print("\n📌 Próximos passos:")
print("   → Revisar o plano (pipeline-plan-validator já rodou)")
print("   → Confirmar se pode avançar para task breakdown")
print("   → Nunca executar sem o usuário confirmar que pode prosseguir")
print("="*60)
```

**Resultado final:** Plano robusto e revisado; **próxima etapa (task breakdown) só após confirmação explícita** de que pode prosseguir.

---

## Fim do Workflow

Após Step 7, a skill termina e retorna controle ao pipeline.

**Garantias:**
- ✅ `.story-plan.md` criado em `data/stories/{story_key}/`
- ✅ YAML frontmatter válido
- ✅ Validado pelo usuário
- ✅ Estado do pipeline atualizado
- ✅ **Plano foi melhorado (3 rounds de análise)**

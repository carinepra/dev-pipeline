---
name: pipeline-task-definer
description: Discussão técnica para refinar uma nova task (TASK=NEW). Lê contexto inicial, usa AskQuestion para coletar detalhes, define título/component/ACs/priority, e atualiza o JSON. Use quando o orquestrador criar uma task que ainda não existe no Jira.
---

# Pipeline Task Definer

**🌐 COMUNICAÇÃO: 100% em PORTUGUÊS (PT-BR)**

**⚠️ Esta é a versão para o Dev Pipeline Orchestrator.**

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
- **Working directory:** Dentro de um repo específico (ver `local_path` em `.pipeline-config.json`)
- Use paths relativos ao repo atual (ex: `src/`, `tests/`)

---

## 📂 Como Interpretar Paths de Arquivos JSON

**Quando o usuário menciona o arquivo JSON:**
```
@pipeline-task-definer pipelines/tasks/_new-{uuid}/.new-task-context.json
```

**O caminho relativo deve ser interpretado como:**
```
{PIPELINE_ROOT}/pipelines/tasks/_new-{uuid}/.new-task-context.json
```

**REGRA:** O path relativo `pipelines/tasks/...` é relativo ao repo `dev-pipeline/`, partindo do workspace root.

**SEMPRE use o caminho COMPLETO ao chamar a ferramenta Read:**
```python
Read(path="{PIPELINE_ROOT}/pipelines/tasks/_new-{uuid}/.new-task-context.json")
```

---

## Propósito

Ajudar o usuário a refinar uma **TASK standalone** (não uma história) que ainda não existe no Jira. O orquestrador já coletou o escopo inicial, agora você ajuda a definir os detalhes técnicos usando modo Plan e AskQuestion.

---

## Fluxo de governança (ordem obrigatória)

1. **Criar a definição colaborativa** — título, descrição, ACs, prioridade e componente partem de um plano claro no modo Plan.
2. **Incentivar discussão técnica** — use AskQuestion e diálogo para que escopo, riscos e critérios estejam **alinhados** entre todos (sem pressa para “fechar” com JSON incompleto).
3. **Depois** o pipeline seguirá para **TASK_PLANNING** com `pipeline-task-planner` e, em seguida, a **skill de revisão de plano** (`pipeline-plan-validator` / equivalente) sobre o `.plan.md`.
4. **Só então** o fluxo pode perguntar se pode **executar** (implementar). **Nunca** assuma que o usuário quer executar o plano ou criar a issue no Jira sem **confirmar explicitamente** que pode prosseguir após o refinamento desta skill (JSON salvo → Enter no terminal) e, mais adiante, após o plano de implementação revisado.

Esta skill cobre o **refino da task nova**; a **revisão do plano de implementação** é etapa separada no orquestrador. Não pule alinhamento técnico para “ganhar tempo”.

---

## PASSO 0: ATIVAR MODO PLAN

**OBRIGATÓRIO: Logo no início da skill, entre em modo Plan.**

Use `SwitchMode` com:
- target_mode_id: "plan"
- explanation: "Vamos planejar os detalhes técnicos da task antes de criar no Jira"

**Benefícios:**
- Discussão focada sem risco de alterações prematuras
- Usuário pode revisar e ajustar antes de finalizar
- Pensamento colaborativo para definir escopo

---

## Input Esperado

O orquestrador criou um arquivo JSON com contexto inicial:

```
pipelines/tasks/_new-{uuid}/.new-task-context.json
```

**Estrutura do JSON:**
```json
{
  "_instructions": "🎯 PLANEJAMENTO DE TASK STANDALONE - Leia com atenção!",
  "_context": "Esta é uma TASK individual, NÃO uma história (story)...",
  "_type": "single_task",
  "_workflow": [...],
  "_required_fields": {...},
  "temp_key": "_new-abc123",
  "parent_story": null,
  "initial_scope": "Descrição do que precisa ser feito",
  "additional_context": "Links, PRs, etc",
  "title": null,
  "description": null,
  "component": null,
  "priority": "Medium",
  "acceptance_criteria": null
}
```

---

## Workflow

```
Step 0: Ativar Modo Plan →
Step 1: Ler JSON e Contexto →
Step 2: Fazer Perguntas Técnicas (AskQuestion) →
Step 3: Definir Detalhes →
Step 4: Atualizar JSON
```

---

## Step 1: Ler JSON e Contexto

Use a ferramenta `Read` para ler o arquivo JSON que o usuário mencionou:

```python
# O usuário mencionou o arquivo com @
# Ler usando Read tool
```

**Apresentar ao usuário:**

```
📋 Contexto Inicial:
   Escopo: {initial_scope}
   Links: {additional_context or "Nenhum"}
   Parent Story: {parent_story or "Standalone (sem história pai)"}

🎯 Vou te ajudar a refinar essa task.
```

---

## Step 2: Fazer Perguntas Técnicas (AskQuestion)

**USE A FERRAMENTA `AskQuestion` para coletar todas as informações de uma vez.**

**Estrutura das perguntas:**

```json
{
  "title": "Refinamento Técnico da Task",
  "questions": [
    {
      "id": "technical_scope",
      "prompt": "Qual parte do sistema essa task afeta?",
      "options": [
        {"id": "backend", "label": "Backend (API, serviços, banco, workers)"},
        {"id": "frontend", "label": "Frontend (UI, componentes, páginas)"},
        {"id": "fullstack", "label": "Fullstack (Backend + Frontend)"},
        {"id": "infra", "label": "Infra (Deploy, CI/CD, configs)"},
        {"id": "docs", "label": "Documentação apenas"}
      ],
      "allow_multiple": false
    },
    {
      "id": "implementation_type",
      "prompt": "O que precisa ser feito tecnicamente?",
      "options": [
        {"id": "new", "label": "Criar novos endpoints/componentes"},
        {"id": "modify", "label": "Modificar código existente"},
        {"id": "fix", "label": "Corrigir bug ou comportamento"},
        {"id": "refactor", "label": "Refatorar sem mudar comportamento"}
      ],
      "allow_multiple": false
    },
    {
      "id": "priority",
      "prompt": "Qual a prioridade dessa task?",
      "options": [
        {"id": "high", "label": "High - Urgente/bloqueador"},
        {"id": "medium", "label": "Medium - Feature normal"},
        {"id": "low", "label": "Low - Pode esperar"}
      ],
      "allow_multiple": false
    }
  ]
}
```

**⚠️ IMPORTANTE:** Adapte as perguntas conforme o contexto específico da task.

---

## Step 3: Definir Detalhes com Base nas Respostas

Com base nas respostas do AskQuestion, defina automaticamente:

### 3.1 Component

Mapear da resposta `technical_scope`:
- "backend" → "Back"
- "frontend" → "Front"
- "fullstack" → null (múltiplos componentes)
- "infra" → "Infra"
- "docs" → "Docs"

### 3.2 Priority

Mapear da resposta `priority`:
- "high" → "High"
- "medium" → "Medium"
- "low" → "Low"

### 3.3 Título (title)

**Gerar baseado em:**
- initial_scope do JSON
- Respostas das perguntas

**Formato**: Verbo + Objeto + Contexto

**Exemplos:**
- ✅ "Adicionar paginação na listagem de orders"
- ✅ "Corrigir formato de prévia de faturamento"
- ✅ "Refatorar validação de inventory"
- ❌ "Melhorias" (muito vago)
- ❌ "Fazer o que o PM pediu" (não descritivo)

**Apresentar sugestão ao usuário:**

```
💡 Sugestão de título:
   "{título_sugerido}"

Esse título funciona ou quer ajustar?
```

### 3.4 Descrição (description)

Expanda o escopo inicial com detalhes técnicos baseado nas respostas:

**Formato:**
```
{O que precisa ser feito}

Detalhes técnicos:
- {Endpoint/componente afetado}
- {Mudanças específicas}
- {Casos especiais}

Contexto:
{Por que essa mudança é necessária}
```

**Apresentar:**

```
📝 Descrição gerada:

{description}

Funciona assim ou precisa ajustar?
```

### 3.5 Acceptance Criteria (acceptance_criteria)

**Gerar critérios SMART baseados em:**
- implementation_type (new/modify/fix/refactor)
- technical_scope (backend/frontend/etc)
- Escopo inicial

**Critérios SMART:**
- **S**pecific: "Endpoint retorna paginação" não "API funciona"
- **M**easurable: "Lista 20 items por página"
- **A**chievable: Realista
- **R**elevant: Relacionado ao escopo
- **T**estable: Pode ser verificado

**Formato:**
```
- [ ] Critério técnico 1
- [ ] Critério técnico 2
- [ ] Critério de UI/UX (se aplicável)
- [ ] Teste automatizado (se aplicável)
```

**Apresentar:**

```
✅ Acceptance Criteria gerados:

{lista_de_criterios}

Falta algum critério importante ou quer ajustar?
```

---

## Step 4: Atualizar JSON

Após confirmar com o usuário, **atualizar o JSON usando a ferramenta Write**:

**Mapeamento dos campos:**
```python
{
  "title": string,               # Definido no Step 3.3
  "description": string,         # Definido no Step 3.4
  "component": string | null,    # Mapeado do AskQuestion
  "priority": string,            # Mapeado do AskQuestion
  "acceptance_criteria": string, # Definido no Step 3.5
  "figma_url": string | null     # Do additional_context se houver
}
```

**Confirmar com o usuário:**

```
✅ JSON atualizado com sucesso!

📋 Resumo final:
   Título: {title}
   Component: {component}
   Priority: {priority}
   ACs: {X} critérios

Volte ao terminal e pressione ENTER para criar no Jira.
```

---

## Checklist Final

- [x] **Modo Plan ativado**
- [x] JSON lido corretamente
- [x] **AskQuestion usado para coletar informações**
- [x] Título definido (verbo + objeto + contexto)
- [x] Descrição expandida com detalhes técnicos
- [x] Component mapeado das respostas
- [x] Acceptance criteria SMART e testáveis
- [x] Priority definida (High/Medium/Low)
- [x] **JSON atualizado e salvo**
- [x] Usuário instruído a voltar ao terminal

---

## Exemplo Completo

### Input (JSON):
```json
{
  "initial_scope": "No histórico dos tickets de faturamento, as prévias disponíveis para download ainda estão no formato antigo (apenas 1 aba)",
  "additional_context": null,
  "parent_story": null
}
```

### Execução:

**Step 0:** Ativar modo Plan

**Step 1:** Ler JSON e apresentar contexto

**Step 2:** Usar AskQuestion com 3 perguntas:
- Parte do sistema (Backend/Frontend/Fullstack/Infra/Docs)
- Tipo de implementação (Criar novo/Modificar/Corrigir/Refatorar)
- Priority (High/Medium/Low)

**Respostas do usuário:**
- technical_scope: "backend"
- implementation_type: "modify"
- priority: "medium"

**Step 3:** Gerar detalhes:

Título sugerido:
```
"Atualizar formato de prévia de faturamento para múltiplas abas no Excel"
```

Descrição:
```
Atualizar a API de geração de prévia de faturamento para gerar Excel 
com múltiplas abas ao invés do formato antigo (1 aba única).

Detalhes técnicos:
- Endpoint: /api/billing/preview (atualizar geração)
- Formato novo: 3 abas (Resumo, Detalhes, Notas)
- Manter compatibilidade com formato antigo via flag

Contexto:
Histórico de tickets de faturamento precisa do formato expandido 
para melhor organização dos dados.
```

Acceptance Criteria:
```
- [ ] API gera Excel com 3 abas: Resumo, Detalhes, Notas
- [ ] Aba Resumo contém totais e período
- [ ] Aba Detalhes lista todos os tickets
- [ ] Aba Notas contém observações e disclaimers
- [ ] Endpoint aceita flag legacy=true para formato antigo
- [ ] Testes unitários cobrem ambos formatos
```

**Step 4:** Salvar JSON e confirmar

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| JSON não encontrado | Pedir caminho correto ao usuário |
| Usuário não sabe detalhes técnicos | Buscar no codebase usando SemanticSearch |
| Escopo muito vago | Fazer perguntas adicionais de forma conversacional |
| Respostas do AskQuestion insuficientes | Fazer follow-up conversacional |
| Múltiplos components | Deixar null e explicar no description |
| ACs muito genéricos | Tornar específicos e testáveis com detalhes técnicos |

---

## Regras Importantes

1. **SEMPRE ativar modo Plan no início**
2. **SEMPRE usar português (PT-BR) em toda comunicação**
3. **SEMPRE usar AskQuestion como primeiro passo de coleta**
4. **NÃO confunda com história**: Isso é uma TASK, não story
5. **NÃO crie no Jira**: Só atualize o JSON, o orquestrador cria
6. **NÃO peça story key**: Já está no JSON (pode ser null)
7. **SIM, seja específico**: Título, ACs e descrição claros
8. **SEMPRE salve o JSON**: Orquestrador espera JSON atualizado com campos obrigatórios preenchidos

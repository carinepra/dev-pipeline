---
name: pipeline-plan-validator
description: Executa 3 rounds de melhoria em planos do Dev Pipeline Orchestrator. Aplica padrões do projeto e atualiza o `.plan.md` in-place. Use APENAS quando chamado pelo orquestrador em TASK_PLANNING após gerar o plano inicial.
---

# Pipeline Plan Validator

**⚠️ Esta é a versão ADAPTADA para o Dev Pipeline Orchestrador.**

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

## ⚠️ DISCLAIMER CRÍTICO: Escopo e Foco

**🎯 REGRA FUNDAMENTAL: NÃO EXPANDA O ESCOPO SEM APROVAÇÃO**

### O Que Fazer

✅ **Melhorar SEM adicionar escopo:**
- Identificar lacunas (contexto faltante, edge cases não cobertos)
- Validar se implementação proposta atende os ACs
- Checar se padrões do projeto estão sendo seguidos
- Sugerir testes DENTRO do escopo da task
- Melhorar clareza e estrutura do plano

✅ **Se identificar melhorias FORA do escopo:**
- **NÃO adicione ao plano automaticamente**
- **USE MODO ASK** para validar:
  ```
  "Durante a análise, identifiquei que [X] poderia ser melhorado.
   Isso está FORA do escopo desta task.
   Deseja adicionar ao plano ou criar task separada?"
  ```
- Só adicione se usuário aprovar explicitamente

### O Que NÃO Fazer

❌ **Não adicione scope creep nas melhorias:**
- "O plano não menciona refatorar Y, mas deveria"
- "Seria bom aproveitar e adicionar testes de Z"
- "Faltou mencionar otimização de W"
- "Podemos melhorar X enquanto estamos aqui"

❌ **Não transforme task pequena em grande:**
- Task: "Adicionar botão" → NÃO sugerir "refatorar todo o componente"
- Task: "Corrigir bug X" → NÃO sugerir "revisar arquitetura de Y"
- Task: "Atualizar texto" → NÃO sugerir "redesenhar página"

❌ **Não presuma necessidades extras:**
- "Claramente precisa de [X]" → ASK FIRST se X não está nos ACs
- "Provavelmente querem [Y]" → ASK FIRST
- "Faz sentido adicionar [Z]" → ASK FIRST

### Tipos de Melhorias Permitidas (SEM pedir)

✅ **Lacunas técnicas DENTRO do escopo:**
- "Plano não menciona tratamento de erro para caso X" → ADICIONAR
- "Faltou validação de input Y (mencionado nos ACs)" → ADICIONAR
- "Edge case Z (do Figma) não foi coberto" → ADICIONAR

✅ **Padrões obrigatórios do projeto:**
- "Usar hook useXyz conforme padrão do repo" → ADICIONAR
- "Validação com Zod obrigatória" → ADICIONAR
- "Testes pytest obrigatórios para endpoint" → ADICIONAR

❌ **Melhorias "nice to have" FORA do escopo:**
- "Poderíamos adicionar feature W" → **ASK FIRST**
- "Seria bom refatorar X" → **ASK FIRST**
- "Oportunidade de melhorar Y" → **ASK FIRST**

### Por Quê?

**Problema:** Melhorias com escopo expandido geram:
- 🚫 Rejeição do plano (usuário não aprova)
- ⏱️ Mais tempo de revisão
- 🔄 Retrabalho (remover sugestões extras)
- 💸 Desperdício de tokens/tempo

**Solução:** Melhorar dentro do escopo → aprovação rápida → implementação eficiente

### Checklist de Escopo (Cada Round)

Antes de adicionar QUALQUER sugestão, perguntar a si mesmo:

- [ ] Isso está EXPLICITAMENTE solicitado na task/ACs?
- [ ] Isso é OBRIGATÓRIO por padrão do projeto?
- [ ] Isso é edge case do ESCOPO ATUAL (não feature nova)?
- [ ] Se TODAS as respostas são NÃO: **USE MODO ASK**

**Lema:** "Melhorar a execução do que foi pedido, não adicionar o que não foi."

---

**Diferenças da skill original:**
- ✅ Recebe caminho do `.plan.md` já criado
- ✅ Atualiza arquivo in-place com `StrReplace`
- ✅ Output curto no chat (apenas resumo)
- ✅ Usa mesmo workflow da skill original (3 rounds)

---

## Input Esperado

O orquestrador fornece:
- **Plan file**: Caminho do `.plan.md` (ex: `pipelines/tasks/PROJ-437/.plan.md`)
- **Story key**: Parent story (ex: `PROJ-436`)
- **Task key**: Task sendo planejada (ex: `PROJ-437`)

**Não** pedir o caminho — já foi informado.

---

## Workflow

```
Step 0: Ativar Modo Plan → Step 1: Detectar repo → Round 1: Lacunas óbvias → 
Round 2: Tech lead → Round 3: Advogado do diabo → Output: Atualizar plano
```

---

## Step 0: Ativar Modo Plan

**OBRIGATÓRIO: Logo no início da skill, entre em modo Plan.**

Use `SwitchMode` com:
- target_mode_id: "plan"
- explanation: "Vamos revisar e melhorar o plano colaborativamente em 3 rounds de análise"

**Benefícios:**
- Discussão focada sobre melhorias sem risco de alterar código
- Usuário pode acompanhar cada round de análise
- Pensamento crítico estruturado antes de implementar

---

## Step 1: Detectar repo e ler referências

Identificar o repo pelo workspace path ou pelo escopo:

- **Backend** (ver config): ler `~/.cursor/skills/skill-back-review-changes/refs/implementation.md` e `~/.cursor/skills/skill-back-review-changes/refs/review.md`
- **Frontend** (ver config): ler `.cursor/rules/*.mdc` (geral, components, hooks, services, tables)

Usar essas referências como checklist nos 3 rounds.

---

## Round 1 — Lacunas Óbvias

**Perspectiva:** Implementador seguindo o plano ao pé da letra.

Perguntas:
- [ ] Algum arquivo afetado não está listado?
- [ ] Algum passo pressupõe que outro já foi feito mas não está na ordem certa?
- [ ] Alguma etapa está vaga demais?
- [ ] Imports, constantes ou dependências órfãos após as mudanças?
- [ ] Testes que quebram silenciosamente (mocks, fixtures, asserts)?

**Buscar no codebase:** Grep/Read nos arquivos mencionados para validar.

---

## Round 2 — Tech Lead

**Perspectiva:** Tech lead revisando antes do merge.

Perguntas:
- [ ] Existe arquivo relacionado não-óbvio? (ex: `conftest.py`, `dependencies.py`, schema YAML)
- [ ] Decisão vai contra o padrão do projeto? (comparar com features similares)
- [ ] Edge cases: dict vazio? campo `None`? lista vazia?
- [ ] Compatibilidade retroativa: dados existentes no DynamoDB/banco afetados?
- [ ] Mudança pode quebrar outros order types / tickets / features?

### Verificação de padrões (obrigatório)

Para cada arquivo novo no plano:
1. **Encontrar referência:** Buscar arquivo existente do mesmo layer (handler, service, etc)
2. **Comparar ponto a ponto:** Imports (relativo vs absoluto?), constructor/init, chamadas a infra (DynamoDB, S3), response format, utilitários existentes
3. **Listar divergências** como WARN ou FAIL

---

## Round 3 — Advogado do Diabo

**Perspectiva:** Revisor que quer reprovar o PR.

Perguntas:
- [ ] Algum passo gera dead code novo?
- [ ] O plano remove algo usado em outro lugar?
- [ ] Magic strings, números inline que deveriam virar constante?
- [ ] Type hints ausentes?
- [ ] Criando arquivos novos desnecessariamente? (inline > service > script)
- [ ] Exceção capturada genericamente (`except Exception`)?

---

## Output

### Execução Interna (3 rounds)

Para cada round, **internamente** listar problemas e correções. Se um round não encontrar nada, seguir para o próximo.

Ao final dos 3 rounds, **atualizar o arquivo `.plan.md`** com `StrReplace`.

### Saída no Chat (obrigatório — resumo único)

**NÃO** colar transcrição completa dos rounds.

**Formato:**

1. **Se nenhum problema:**
   ```
   Plano revisado — nenhum ajuste necessário nos 3 passes.
   ```

2. **Se houve ajustes:**
   ```
   Plano melhorado (3 passes):
   - Adicionado arquivo X ao escopo (Round 1)
   - Corrigida ordem de passos Y antes de Z (Round 1)
   - Identificado utilitário existente para W (Round 2)
   - Removida constante desnecessária K (Round 3)
   
   Arquivo atualizado: pipelines/tasks/PROJ-437/.plan.md
   ```

**Máximo 6 bullets** com só o que mudou (sem recontar análise).

### Quando roda dentro de pipeline-pr-responder

- **Obrigatório** após `CreatePlan` na **mesma execução**
- Plano vem do Plan mode (`.cursor/plans/*.plan.md`)
- **No chat:** omitir este bloco (address-pr envia síntese dos comentários)

---

## Regras

- ❌ Não pular rounds mesmo que o anterior não encontre nada
- ❌ Não repetir problemas já corrigidos
- ✅ Ser definitivo: "X precisa mudar porque Y" (não "verificar se X")
- ❌ Não criar arquivos extras
- ✅ Chat: resumo curto; arquivo `.plan.md`: detalhe completo

---

## Diferenças da Skill Original

| Aspecto | Skill Original | Pipeline Version |
|---------|---------------|------------------|
| **Input** | Plano em qualquer lugar | Caminho fixo fornecido pelo orquestrador |
| **Modo Plan** | Não usa | **Ativa automaticamente** (Step 0) |
| **Output no chat** | Resumo curto | **Idêntico** (resumo curto) |
| **Arquivo atualizado** | Qualquer `.plan.md` | **Fixo**: `data/stories/{story_key}/{task_key}.plan.md` |
| **Contexto** | Infere do workspace | Usa escopo do `story_data` |

---

## Checklist Final

- [x] **Modo Plan foi ativado** (Step 0)
- [x] Plano foi lido
- [x] Refs de domínio foram carregadas (backend ou frontend)
- [x] Round 1 executado (lacunas óbvias)
- [x] Round 2 executado (tech lead + padrões)
- [x] Round 3 executado (advogado do diabo)
- [x] Arquivo `.plan.md` atualizado com `StrReplace`
- [x] Resumo curto enviado no chat

---

## Após esta skill (governança)

Esta skill **revisa e melhora** o `.plan.md`; ela **não** autoriza implementação.

- O orquestrador **só deve** perguntar se pode **executar** o plano **depois** que esta revisão tiver terminado (e após qualquer discussão de alinhamento que o usuário ainda precise).
- **Sempre** obter **confirmação explícita** de que o usuário aprova **executar** o plano antes de avançar para `IMPLEMENTATION` ou equivalente. Nunca assumir que o arquivo atualizado = “pode codar”.

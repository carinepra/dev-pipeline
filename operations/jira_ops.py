"""Operações Jira (CRUD de issues via API, sem análise)."""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

def _resolve_jira_base_url() -> str:
    try:
        from utils.config import get_jira_base_url
        return get_jira_base_url()
    except Exception:
        return os.getenv("JIRA_SERVER", "https://whitecompany.atlassian.net")

JIRA_BASE_URL = _resolve_jira_base_url()
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


# ── ADF Helpers ───────────────────────────────────────────────────────────────
#
# Atlassian Document Format helpers para formatação rica no Jira.
# 
# FORMATTING RULES:
# - panel() auto-adds hardBreak between items → compact single-paragraph layout.
# - NEVER pass br() in the lines list — panel() already handles line breaks.
# - Use txt("Title:", bold=True) for section headers within the same paragraph.
# - Prefix list items with "- " in the string itself.
#


def txt(text: str, bold: bool = False) -> dict[str, Any]:
    """Cria texto ADF (opcionalmente em negrito)."""
    node = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def code(text: str) -> dict[str, Any]:
    """Cria texto inline code ADF."""
    return {"type": "text", "text": text, "marks": [{"type": "code"}]}


def br() -> dict[str, str]:
    """Cria quebra de linha (hardBreak) ADF."""
    return {"type": "hardBreak"}


def link(url: str, label: str | None = None) -> dict[str, Any]:
    """Cria link ADF."""
    return {
        "type": "text",
        "text": label or url,
        "marks": [{"type": "link", "attrs": {"href": url}}],
    }


def panel(kind: str, lines: list[str | dict | list | None]) -> dict[str, Any]:
    """
    Cria painel ADF colorido.
    
    Args:
        kind: Tipo do painel (info=azul, success=verde, note=cinza, warning=amarelo)
        lines: Lista de strings, nós ADF (txt, link, code), ou None.
               None = separador (cria novo parágrafo, espaçamento visual)
    
    Returns:
        Nó ADF de painel
    """
    groups: list[list] = [[]]
    for line in lines:
        if line is None:
            groups.append([])
        else:
            groups[-1].append(line)
    
    content = []
    for group in groups:
        if not group:
            continue
        para_content = []
        for i, line in enumerate(group):
            if isinstance(line, list):
                for node in line:
                    para_content.append(node if isinstance(node, dict) else txt(node))
            elif isinstance(line, dict):
                para_content.append(line)
            else:
                para_content.append(txt(line))
            if i < len(group) - 1:
                para_content.append(br())
        content.append({"type": "paragraph", "content": para_content})
    
    return {
        "type": "panel",
        "attrs": {"panelType": kind},
        "content": content,
    }


def figma_panel(url: str) -> dict[str, Any]:
    """Cria painel de nota com link do Figma."""
    return {
        "type": "panel",
        "attrs": {"panelType": "note"},
        "content": [
            {"type": "paragraph", "content": [txt("🎨 Figma: "), link(url)]}
        ],
    }


def build_description(
    info_lines: list[str | dict | list | None],
    dod_lines: list[str | dict | list | None],
    figma_url: str | None = None,
) -> dict[str, Any]:
    """
    Constrói descrição ADF com 3 painéis: info + success (DOD) + note (Figma).
    
    Args:
        info_lines: Linhas do painel azul (contexto/descrição)
        dod_lines: Linhas do painel verde (Definition of Done)
        figma_url: URL do Figma (painel cinza, opcional)
    
    Returns:
        Descrição ADF completa
    """
    content = [panel("info", info_lines), panel("success", dod_lines)]
    if figma_url:
        content.append(figma_panel(figma_url))
    return {"type": "doc", "version": 1, "content": content}


def create_issue(
    project_key: str,
    summary: str,
    description: str | dict[str, Any],
    issue_type: str = "Task",
    parent_key: str | None = None,
    component: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    story_points: int | None = None,
    dry_run: bool = False,
) -> str:
    """
    Cria issue no Jira (CRUD puro, sem análise).

    Args:
        project_key: Projeto (ex: "PROJ")
        summary: Título da issue
        description: Descrição (string simples OU dict ADF completo)
        issue_type: Tipo (Task, Bug, Story, Sub-task)
        parent_key: Key da história pai (para subtasks)
        component: Component name (ex: "Front", "Back", "Produto")
        priority: Priority name (ex: "Highest", "High", "Medium", "Low", "Lowest")
        labels: Lista de labels
        story_points: Story points (customfield_10016)
        dry_run: Se True, não cria de verdade

    Returns:
        Issue key criada (ex: "PROJ-1235")
    """
    if dry_run:
        return f"DRY-{summary[:20]}"

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"

    # Construir descrição (ADF completo ou string simples)
    if isinstance(description, dict):
        # Já é ADF completo (build_description())
        description_adf = description
    else:
        # String simples → converter para ADF básico
        description_adf = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }

    payload: dict[str, Any] = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description_adf,
            "issuetype": {"name": issue_type},
        }
    }

    if parent_key:
        payload["fields"]["parent"] = {"key": parent_key}
    
    if component:
        payload["fields"]["components"] = [{"name": component}]
    
    if priority:
        payload["fields"]["priority"] = {"name": priority}
    
    if labels:
        payload["fields"]["labels"] = labels
    
    if story_points is not None:
        payload["fields"]["customfield_10016"] = story_points

    response = requests.post(
        url,
        json=payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    
    # Debug em caso de erro
    if response.status_code != 200 and response.status_code != 201:
        print(f"\n❌ Erro {response.status_code} ao criar issue no Jira")
        print(f"URL: {url}")
        print(f"Payload enviado:")
        import json as json_lib
        print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        print(f"\nResposta do Jira:")
        try:
            print(json_lib.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
    
    response.raise_for_status()

    data = response.json()
    return data["key"]


def update_issue_status(issue_key: str, status: str, dry_run: bool = False) -> None:
    """
    Atualiza status da issue via transição.

    Args:
        issue_key: Issue key
        status: Nome do status (ex: "In Progress")
        dry_run: Se True, não atualiza
    """
    if dry_run:
        return

    # Buscar transition ID para o status
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions"

    response = requests.get(
        url, auth=(JIRA_EMAIL, JIRA_API_TOKEN), timeout=30
    )
    response.raise_for_status()

    transitions = response.json()["transitions"]
    transition_id = None

    for transition in transitions:
        if transition["name"].lower() == status.lower():
            transition_id = transition["id"]
            break

    if not transition_id:
        raise ValueError(f"Transition '{status}' not found for {issue_key}")

    # Executar transição
    response = requests.post(
        url,
        json={"transition": {"id": transition_id}},
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()


def update_issue_description(issue_key: str, description: dict[str, Any] | str, dry_run: bool = False) -> None:
    """
    Atualiza apenas a descrição de uma issue existente.

    Args:
        issue_key: Key da issue (ex: "PROJ-1234")
        description: Nova descrição (ADF dict ou string simples)
        dry_run: Se True, não atualiza
    """
    if dry_run:
        print(f"[DRY-RUN] Atualizaria descrição de {issue_key}")
        return

    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}"

    # Converter descrição se necessário
    if isinstance(description, dict):
        description_adf = description
    else:
        description_adf = {
            "type": "doc",
            "version": 1,
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}],
        }

    payload = {"fields": {"description": description_adf}}

    response = requests.put(
        url,
        json=payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    
    if response.status_code != 204:
        print(f"\n❌ Erro {response.status_code} ao atualizar {issue_key}")
        import json as json_lib
        print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        try:
            print(json_lib.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
    
    response.raise_for_status()
    print(f"✅ {issue_key} descrição atualizada → {JIRA_BASE_URL}/browse/{issue_key}")


def add_blocking_link(blocking_key: str, blocked_key: str, dry_run: bool = False) -> None:
    """
    Cria link de bloqueio entre duas issues (blocking_key bloqueia blocked_key).

    Args:
        blocking_key: Issue que bloqueia (ex: "PROJ-100")
        blocked_key: Issue bloqueada (ex: "PROJ-101")
        dry_run: Se True, não cria
    """
    if dry_run:
        print(f"[DRY-RUN] {blocking_key} bloquearia {blocked_key}")
        return

    url = f"{JIRA_BASE_URL}/rest/api/3/issueLink"

    payload = {
        "type": {"name": "Blocks"},
        "inwardIssue": {"key": blocking_key},
        "outwardIssue": {"key": blocked_key},
    }

    response = requests.post(
        url,
        json=payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    
    if response.status_code not in [200, 201]:
        print(f"\n❌ Erro {response.status_code} ao criar link {blocking_key} → {blocked_key}")
        import json as json_lib
        print(json_lib.dumps(payload, indent=2, ensure_ascii=False))
        try:
            print(json_lib.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print(response.text)
    
    response.raise_for_status()
    print(f"🔗 {blocking_key} blocks {blocked_key}")

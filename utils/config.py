"""
Gerenciamento de configuração centralizada do pipeline (v3.0).

Lê .pipeline-config.json e fornece helpers para acessar projetos, repos e Jira.
Compatível com v2.1 (fallback para defaults Firebolt/HUB).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
import json
from datetime import datetime

from core.constants import (
    DEFAULT_STORIES_DIR,
    DEFAULT_TASKS_DIR,
)

_ISSUE_KEY_RE = re.compile(r"^([A-Z][A-Z0-9]*)-\d+$")

_V2_FALLBACK_PROJECTS = {
    "HUB": {
        "name": "Firebolt HUB",
        "repos": ["firebolt-backend", "firebolt-frontend", "docs"],
        "component_repo_map": {
            "Front": "firebolt-frontend",
            "Back": "firebolt-backend",
            "Infra": "firebolt-backend",
            "Docs": "docs",
        },
        "docs_search_paths": [
            "onze-docs-tech/app/docs/content/sistemas/firebolt/"
        ],
    }
}

_V2_FALLBACK_REPOSITORIES = {
    "firebolt-backend": {
        "github_repo": "onze-firebolt-api-online",
        "local_path": "onze-firebolt-api-online",
        "type": "backend",
        "tech_stack": "python/fastapi",
    },
    "firebolt-frontend": {
        "github_repo": "onze-firebolt-www-backoffice",
        "local_path": "onze-firebolt-www-backoffice",
        "type": "frontend",
        "tech_stack": "nextjs/typescript",
    },
    "docs": {
        "github_repo": "onze-docs-tech",
        "local_path": "onze-docs-tech",
        "type": "docs",
        "tech_stack": "markdown",
    },
}


def _config_path() -> Path:
    return Path(__file__).resolve().parents[1] / ".pipeline-config.json"


def get_pipeline_config() -> dict:
    """
    Lê config atual com fallback v2.1 -> v3.0.

    Returns:
        Dict completo com jira, github, repositories, paths.
    """
    path = _config_path()
    if not path.exists():
        generate_pipeline_config()
    cfg = json.loads(path.read_text(encoding="utf-8"))

    if cfg.get("version", "2.1") < "3.0":
        cfg.setdefault("jira", {
            "base_url": os.getenv("JIRA_SERVER", "https://redventures.atlassian.net"),
            "default_project": "HUB",
            "projects": _V2_FALLBACK_PROJECTS,
        })
        cfg.setdefault("github", {"org": "RedVentures"})
        cfg.setdefault("repositories", _V2_FALLBACK_REPOSITORIES)

    return cfg


def generate_pipeline_config(force: bool = False) -> Path:
    """Gera .pipeline-config.json v3.0 na raiz do projeto."""
    path = _config_path()
    if path.exists() and not force:
        return path

    config = {
        "version": "3.0",
        "jira": {
            "base_url": os.getenv("JIRA_SERVER", "https://redventures.atlassian.net"),
            "default_project": "HUB",
            "projects": _V2_FALLBACK_PROJECTS,
        },
        "github": {"org": "RedVentures"},
        "repositories": _V2_FALLBACK_REPOSITORIES,
        "paths": {
            "stories_dir": DEFAULT_STORIES_DIR,
            "tasks_dir": DEFAULT_TASKS_DIR,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generated_by": "utils.config",
    }

    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_project_key(issue_key: str) -> str:
    """
    Extrai project key de uma issue key.

    >>> extract_project_key("HUB-542")
    'HUB'
    >>> extract_project_key("INVEST-100")
    'INVEST'

    Raises:
        ValueError: Se formato inválido.
    """
    m = _ISSUE_KEY_RE.match(issue_key)
    if not m:
        raise ValueError(f"Issue key inválida: {issue_key}")
    return m.group(1)


def is_issue_key(value: str) -> bool:
    """Retorna True se valor é uma issue key válida (ex: HUB-542, INVEST-100)."""
    return bool(_ISSUE_KEY_RE.match(value))


def get_jira_base_url() -> str:
    """Retorna Jira base URL do config (fallback para env JIRA_SERVER)."""
    cfg = get_pipeline_config()
    return cfg.get("jira", {}).get(
        "base_url",
        os.getenv("JIRA_SERVER", "https://redventures.atlassian.net"),
    )


def get_default_project() -> str:
    """Retorna default project key do config."""
    cfg = get_pipeline_config()
    return cfg.get("jira", {}).get("default_project", "HUB")


def get_github_org() -> str:
    """Retorna GitHub org do config."""
    cfg = get_pipeline_config()
    return cfg.get("github", {}).get("org", "RedVentures")


def list_project_keys() -> list[str]:
    """Lista todas as project keys configuradas."""
    cfg = get_pipeline_config()
    return list(cfg.get("jira", {}).get("projects", {}).keys())


def get_project_config(project_key: str) -> dict:
    """
    Retorna config de um projeto Jira.

    Args:
        project_key: Ex: "HUB", "INVEST"

    Returns:
        Dict com name, repos, component_repo_map, docs_search_paths.

    Raises:
        KeyError: Se projeto não configurado.
    """
    cfg = get_pipeline_config()
    projects = cfg.get("jira", {}).get("projects", {})
    if project_key not in projects:
        available = ", ".join(projects.keys()) or "(nenhum)"
        raise KeyError(
            f"Projeto '{project_key}' não encontrado no config. "
            f"Projetos disponíveis: {available}. "
            f"Adicione em .pipeline-config.json -> jira.projects"
        )
    return projects[project_key]


def get_repo_config(repo_id: str) -> dict:
    """
    Retorna config de um repositório.

    Args:
        repo_id: ID do repo no config (ex: "firebolt-backend")

    Returns:
        Dict com github_repo, local_path, type, tech_stack + id.

    Raises:
        KeyError: Se repo não configurado.
    """
    cfg = get_pipeline_config()
    repos = cfg.get("repositories", {})
    if repo_id not in repos:
        available = ", ".join(repos.keys()) or "(nenhum)"
        raise KeyError(
            f"Repositório '{repo_id}' não encontrado no config. "
            f"Repos disponíveis: {available}. "
            f"Adicione em .pipeline-config.json -> repositories"
        )
    return {**repos[repo_id], "id": repo_id}


def get_repos_for_project(project_key: str) -> list[dict]:
    """
    Retorna lista de repos (com dados completos) de um projeto.

    Args:
        project_key: Ex: "HUB"

    Returns:
        Lista de dicts, cada um com id, github_repo, local_path, type, tech_stack.
    """
    project = get_project_config(project_key)
    return [get_repo_config(rid) for rid in project.get("repos", [])]


def resolve_component_to_repo(project_key: str, component: str | None) -> dict:
    """
    Resolve um Jira component para o repo correspondente.

    Args:
        project_key: Ex: "HUB"
        component: Ex: "Front", "Back", None

    Returns:
        Dict do repo (com id, github_repo, local_path, type, etc).
        Se component é None ou não mapeado, retorna primeiro repo do projeto.
    """
    project = get_project_config(project_key)
    comp_map = project.get("component_repo_map", {})

    repo_id = comp_map.get(component) if component else None
    if not repo_id:
        repo_ids = project.get("repos", [])
        repo_id = repo_ids[0] if repo_ids else None

    if not repo_id:
        raise ValueError(
            f"Nenhum repo configurado para projeto '{project_key}'"
        )

    repo = get_repo_config(repo_id)
    cfg = get_pipeline_config()
    org = cfg.get("github", {}).get("org", "RedVentures")
    repo["org"] = org
    repo["url"] = f"https://github.com/{org}/{repo['github_repo']}"
    return repo


def build_jira_url(issue_key: str) -> str:
    """Constrói URL completa para uma issue no Jira."""
    return f"{get_jira_base_url()}/browse/{issue_key}"


def get_all_repositories() -> dict[str, dict]:
    """Retorna todos os repos do config com id incluído em cada entry."""
    cfg = get_pipeline_config()
    repos = cfg.get("repositories", {})
    return {rid: {**data, "id": rid} for rid, data in repos.items()}


def get_repos_by_type(project_key: str, repo_type: str) -> list[dict]:
    """
    Retorna repos de um projeto filtrados por tipo (frontend/backend/docs).

    Args:
        project_key: Ex: "HUB"
        repo_type: Ex: "frontend", "backend"

    Returns:
        Lista de dicts com id, github_repo, local_path, type, tech_stack.
    """
    return [
        r for r in get_repos_for_project(project_key)
        if r.get("type") == repo_type
    ]


def get_stories_dir() -> str:
    """Retorna stories_dir do config (fallback para DEFAULT_STORIES_DIR)."""
    cfg = get_pipeline_config()
    return cfg.get("paths", {}).get("stories_dir", DEFAULT_STORIES_DIR)


def get_tasks_dir() -> str:
    """Retorna tasks_dir do config (fallback para DEFAULT_TASKS_DIR)."""
    cfg = get_pipeline_config()
    return cfg.get("paths", {}).get("tasks_dir", DEFAULT_TASKS_DIR)

"""Detecta o repositório correto baseado no component da task, lendo do config."""

from __future__ import annotations

from pathlib import Path


def get_repo_info_from_component(
    component: str | None,
    project_key: str | None = None,
) -> dict[str, str]:
    """
    Retorna informações do repositório baseado no component.

    Delega para config.resolve_component_to_repo() que lê .pipeline-config.json.

    Args:
        component: Component da task (Front, Back, Infra, Docs, etc)
        project_key: Projeto Jira (ex: "PROJ"). Se None, usa default_project.

    Returns:
        Dict com 'org', 'repo', 'url', 'local_path', 'id', 'type'
    """
    from utils.config import (
        resolve_component_to_repo,
        get_default_project,
    )

    pk = project_key or get_default_project()
    try:
        repo = resolve_component_to_repo(pk, component)
    except (KeyError, ValueError):
        import logging
        logger = logging.getLogger(__name__)
        default = get_default_project()
        if pk != default:
            logger.warning(
                f"Projeto '{pk}' não encontrado no config, "
                f"usando fallback para '{default}'. "
                f"Adicione '{pk}' em .pipeline-config.json -> jira.projects"
            )
        repo = resolve_component_to_repo(default, component)

    return {
        "org": repo.get("org", "WhiteCompany"),
        "repo": repo["github_repo"],
        "url": repo.get("url", f"https://github.com/{repo.get('org', 'WhiteCompany')}/{repo['github_repo']}"),
        "local_path": repo["local_path"],
        "id": repo["id"],
        "type": repo.get("type", "backend"),
    }


def detect_repo_from_working_directory() -> dict[str, str]:
    """
    Detecta o repositório baseado no working directory atual.

    Itera sobre todos os repos no config e compara local_path com CWD.

    Returns:
        Dict com 'org', 'repo', 'url', 'local_path', 'id', 'type'
    """
    from utils.config import get_all_repositories, get_github_org

    cwd = str(Path.cwd())
    try:
        org = get_github_org()
        repos = get_all_repositories()
    except Exception:
        return {
            "org": "unknown",
            "repo": "unknown",
            "url": "",
            "local_path": "",
            "id": "unknown",
            "type": "backend",
        }

    for repo_id, repo in repos.items():
        local_path = repo.get("local_path", "")
        if local_path and local_path in cwd:
            return {
                "org": org,
                "repo": repo["github_repo"],
                "url": f"https://github.com/{org}/{repo['github_repo']}",
                "local_path": local_path,
                "id": repo_id,
                "type": repo.get("type", "backend"),
            }

    first_repo = next(iter(repos.values()), None)
    if first_repo:
        return {
            "org": org,
            "repo": first_repo["github_repo"],
            "url": f"https://github.com/{org}/{first_repo['github_repo']}",
            "local_path": first_repo["local_path"],
            "id": first_repo["id"],
            "type": first_repo.get("type", "backend"),
        }

    return {
        "org": org,
        "repo": "unknown",
        "url": "",
        "local_path": "",
        "id": "unknown",
        "type": "backend",
    }


def build_pr_url(pr_number: int | str, component: str | None = None, project_key: str | None = None) -> str:
    """
    Constrói URL do PR baseado no component.

    Args:
        pr_number: Número do PR
        component: Component da task
        project_key: Projeto Jira

    Returns:
        URL completa do PR
    """
    repo_info = get_repo_info_from_component(component, project_key)
    return f"{repo_info['url']}/pull/{pr_number}"

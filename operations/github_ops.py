"""Operações GitHub (PR create, fetch comments) via gh CLI."""

import json
import subprocess
from pathlib import Path
from typing import Any


def create_pr(
    branch: str,
    title: str,
    body: str,
    base: str = "main",
    dry_run: bool = False,
    cwd: Path | None = None
) -> str:
    """
    gh pr create (mecânico).

    Se dry_run=True, retorna URL fake sem criar PR de verdade.

    Args:
        branch: Nome da branch
        title: Título da PR
        body: Corpo da PR
        base: Branch base (default: main)
        dry_run: Se True, não cria PR
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        URL da PR criada (ou string dry-run)
    """
    if dry_run:
        return f"DRY-RUN: Would create PR '{title}' from branch '{branch}' to '{base}'"

    cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base, "--head", branch]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=str(cwd) if cwd else None,
    )

    # Última linha contém URL
    pr_url = result.stdout.strip().split("\n")[-1]
    return pr_url


def fetch_pr_comments(pr_number: int, repo: str | None = None, cwd: Path | None = None) -> list[dict[str, Any]]:
    """
    gh api para fetch de comentários de PR (SEM analisar).

    Args:
        pr_number: Número da PR
        repo: Formato "owner/repo" (None = detecta do remote)
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        [{"file": "...", "line": 10, "body": "...", "user": "..."}, ...]
    """
    if repo is None:
        # Detectar repo do git remote usando cwd correto
        cmd = ["git", "remote", "get-url", "origin"]
        if cwd:
            cmd = ["git", "-C", str(cwd)] + cmd[1:]
        
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        remote_url = result.stdout.strip()
        # Parsear formato: git@github.com:owner/repo.git ou https://github.com/owner/repo
        if "github.com" in remote_url:
            parts = remote_url.replace(".git", "").split("github.com")[1].strip("/:")
            repo = parts

    # gh api (com cwd se fornecido)
    cmd = ["gh", "api", f"repos/{repo}/pulls/{pr_number}/comments"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=str(cwd) if cwd else None,
    )

    comments_data = json.loads(result.stdout)
    comments = []

    for comment in comments_data:
        comments.append(
            {
                "file": comment.get("path", ""),
                "line": comment.get("line", 0),
                "body": comment.get("body", ""),
                "user": comment.get("user", {}).get("login", ""),
                "created_at": comment.get("created_at", ""),
            }
        )

    return comments


def get_pr_status(pr_number: int, repo: str | None = None, cwd: Path | None = None) -> dict[str, Any]:
    """
    gh pr view para status da PR.

    Args:
        pr_number: Número da PR
        repo: Formato "owner/repo" (None = detecta)
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        {"state": "OPEN|CLOSED|MERGED", "reviews": [...], "checks": {...}}
    """
    repo_arg = ["-R", repo] if repo else []

    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "state,reviews,statusCheckRollup"]
        + repo_arg,
        capture_output=True,
        text=True,
        check=True,
        cwd=str(cwd) if cwd else None,
    )

    return json.loads(result.stdout)


def get_pr_status_simple(pr_url: str, cwd: Path | None = None) -> str:
    """
    Retorna status simplificado do PR: 'open' | 'merged' | 'closed'.
    
    Args:
        pr_url: URL completa do PR (e.g., https://github.com/owner/repo/pull/123)
        cwd: Diretório do repo (None = Path.cwd())
    
    Returns:
        "open" | "merged" | "closed"
    
    Raises:
        ValueError: Se URL for inválida
        subprocess.CalledProcessError: Se gh CLI falhar
    """
    import re
    
    # Extrair número do PR: /pull/393 → 393
    match = re.search(r'/pull/(\d+)', pr_url)
    if not match:
        raise ValueError(f"URL de PR inválida: {pr_url}")
    
    pr_number = match.group(1)
    
    result = subprocess.run(
        ["gh", "pr", "view", pr_number, "--json", "state", "-q", ".state"],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=True
    )
    
    # Retorna: "OPEN", "MERGED", "CLOSED"
    state = result.stdout.strip().upper()
    
    if state == "MERGED":
        return "merged"
    elif state == "CLOSED":
        return "closed"
    else:
        return "open"


# ===== NOVOS HELPERS PARA FINALIZAÇÃO DE HISTÓRIA (v1.6.0) =====


def get_pr_files(pr_url: str) -> list[str]:
    """
    Lista arquivos modificados em uma PR (qualquer repo).
    
    Args:
        pr_url: URL completa da PR (ex: https://github.com/org/repo/pull/123)
    
    Returns:
        Lista de paths ou [] se erro
    """
    from rich.console import Console
    console = Console()
    
    try:
        # Extrair org/repo/number da URL
        parts = pr_url.rstrip("/").split("/")
        if len(parts) < 5 or "github.com" not in pr_url:
            raise ValueError(f"URL de PR inválida: {pr_url}")
        
        org = parts[-4]
        repo = parts[-3]
        pr_number = parts[-1]
        
        result = subprocess.run(
            ["gh", "pr", "view", pr_number,
             "--repo", f"{org}/{repo}",  # Não depende de cwd
             "--json", "files"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        
        data = json.loads(result.stdout)
        return [f["path"] for f in data.get("files", [])]
        
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⚠️  Timeout ao buscar arquivos da PR {pr_url}[/yellow]")
        return []
    
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        console.print(f"[yellow]⚠️  Erro ao buscar PR: {error_msg}[/yellow]")
        console.print(f"[dim]Verifique: gh auth status[/dim]")
        return []
    
    except Exception as e:
        console.print(f"[red]❌ Erro inesperado: {e}[/red]")
        return []


def get_pr_details(pr_url: str) -> dict | None:
    """
    Busca detalhes de uma PR (título, body, autor, etc).
    
    Args:
        pr_url: URL completa da PR
    
    Returns:
        Dict com dados da PR ou None se erro
    """
    from rich.console import Console
    console = Console()
    
    try:
        parts = pr_url.rstrip("/").split("/")
        org = parts[-4]
        repo = parts[-3]
        pr_number = parts[-1]
        
        result = subprocess.run(
            ["gh", "pr", "view", pr_number,
             "--repo", f"{org}/{repo}",
             "--json", "number,title,body,author,state,files"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        
        data = json.loads(result.stdout)
        
        return {
            "number": data["number"],
            "title": data["title"],
            "body": data.get("body", ""),
            "author": data["author"]["login"] if data.get("author") else "unknown",
            "state": data["state"],
            "files_count": len(data.get("files", [])),
        }
        
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro ao buscar detalhes da PR {pr_url}: {e}[/yellow]")
        return None


def get_pr_file_diff(pr_url: str, file_path: str) -> str:
    """
    Busca diff de um arquivo específico em uma PR.
    
    Args:
        pr_url: URL completa da PR
        file_path: Path do arquivo (ex: "src/app/page.tsx")
    
    Returns:
        Diff do arquivo ou "" se erro
    """
    from rich.console import Console
    console = Console()
    
    try:
        parts = pr_url.rstrip("/").split("/")
        org = parts[-4]
        repo = parts[-3]
        pr_number = parts[-1]
        
        result = subprocess.run(
            ["gh", "pr", "diff", pr_number,
             "--repo", f"{org}/{repo}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,  # Diff pode ser grande
        )
        
        return _extract_file_from_diff(result.stdout, file_path)
        
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⚠️  Timeout ao buscar diff de {file_path}[/yellow]")
        return ""
    
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro ao buscar diff: {e}[/yellow]")
        return ""


def get_pr_full_diff(pr_url: str) -> str:
    """
    Busca diff completo de uma PR (otimização para múltiplos arquivos).
    
    Args:
        pr_url: URL completa da PR
    
    Returns:
        Diff completo ou "" se erro
    """
    from rich.console import Console
    console = Console()
    
    try:
        parts = pr_url.rstrip("/").split("/")
        org = parts[-4]
        repo = parts[-3]
        pr_number = parts[-1]
        
        result = subprocess.run(
            ["gh", "pr", "diff", pr_number,
             "--repo", f"{org}/{repo}"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        
        return result.stdout
        
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]⚠️  Timeout ao buscar diff completo da PR {pr_url}[/yellow]")
        return ""
    
    except Exception as e:
        console.print(f"[yellow]⚠️  Erro ao buscar diff completo: {e}[/yellow]")
        return ""


def _extract_file_from_diff(full_diff: str, file_path: str) -> str:
    """
    Extrai diff de um arquivo específico do diff completo.
    
    Args:
        full_diff: Diff completo da PR
        file_path: Path do arquivo a extrair
    
    Returns:
        Diff do arquivo específico
    """
    lines = full_diff.split("\n")
    file_diff_lines = []
    in_target_file = False
    
    for line in lines:
        if line.startswith("diff --git"):
            # Se encontrou próximo arquivo e já estava no target, parar
            if in_target_file:
                break
            # Verificar se é o arquivo target
            in_target_file = file_path in line
        
        if in_target_file:
            file_diff_lines.append(line)
    
    return "\n".join(file_diff_lines)

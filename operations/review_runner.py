"""Run linters e coleta erros (SEM análise com IA)."""

import os
import subprocess
from pathlib import Path
from typing import Any


def resolve_review_cwd(repo_type: str = "", repo_id: str = "") -> Path:
    """
    Resolve o diretório onde rodar git/linters.

    Tenta em ordem:
    1. Se repo_id fornecido, busca local_path no config.
    2. Se repo_type fornecido, busca primeiro repo desse type no config.
    3. Fallback para env vars FIREBOLT_LOCAL_* (backward compat).
    4. Fallback para Path.cwd().

    Args:
        repo_type: "backend", "frontend", ou "docs"
        repo_id: ID do repo no config (ex: "firebolt-backend")

    Returns:
        Path absoluto do repo alvo
    """
    base = Path(__file__).resolve().parents[1]

    if repo_id:
        try:
            from utils.config import get_repo_config
            repo = get_repo_config(repo_id)
            target = (base / ".." / repo["local_path"]).resolve()
            if target.exists():
                return target
        except (KeyError, Exception):
            pass

    if repo_type:
        try:
            from utils.config import get_all_repositories
            for _, repo in get_all_repositories().items():
                if repo.get("type") == repo_type:
                    target = (base / ".." / repo["local_path"]).resolve()
                    if target.exists():
                        return target
        except Exception:
            pass

    env_map = {
        "backend": "FIREBOLT_LOCAL_API",
        "frontend": "FIREBOLT_LOCAL_BACKOFFICE",
        "docs": "FIREBOLT_LOCAL_DOCS",
    }
    env_var = env_map.get(repo_type)
    if env_var:
        local_path = os.environ.get(env_var, "").strip()
        if local_path:
            target = (base / local_path).resolve()
            if target.exists():
                return target

    return Path.cwd()


def detect_repo_type(cwd: Path | None = None) -> str:
    """
    Detecta tipo de repo via config (local_path ou git remote).

    Args:
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        "backend", "frontend", "docs", etc.

    Raises:
        ValueError: Se repo desconhecido
    """
    if cwd is None:
        cwd = Path.cwd()

    cwd_str = str(cwd)

    try:
        from utils.config import get_all_repositories
        for _, repo in get_all_repositories().items():
            if repo.get("local_path") and repo["local_path"] in cwd_str:
                return repo.get("type", "backend")
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote = result.stdout.strip()
    except subprocess.CalledProcessError:
        return "backend"

    try:
        from utils.config import get_all_repositories
        for _, repo in get_all_repositories().items():
            if repo.get("github_repo") and repo["github_repo"] in remote:
                return repo.get("type", "backend")
    except Exception:
        pass

    if "api-online" in remote or "ia-firebolt" in remote or "sustentacao" in remote:
        return "backend"
    elif "backoffice" in remote or "www" in remote:
        return "frontend"
    
    import logging
    logging.getLogger(__name__).warning(
        f"Tipo de repo não identificado para remote '{remote}', usando 'backend' como fallback"
    )
    return "backend"


def run_linters(
    repo_type: str | None = None,
    files: list[str] | None = None,
    cwd: Path | None = None
) -> dict[str, Any]:
    """
    Roda linters e coleta erros (SEM analisar com IA).

    Backend: black --check, mypy, ruff (se disponível)
    Frontend: eslint, tsc --noEmit

    Args:
        repo_type: "backend" ou "frontend" (auto-detecta se None)
        files: Lista de arquivos específicos (None = repo inteiro)
        cwd: Diretório onde rodar os linters (None = resolve via env ou Path.cwd())

    Returns:
        {
            "errors": [
                {"file": "...", "line": 45, "rule": "...", "message": "..."},
                ...
            ],
            "warnings": [...],
            "summary": {"errors": 5, "warnings": 12}
        }
    """
    if repo_type is None:
        repo_type = detect_repo_type(cwd)

    if cwd is None:
        cwd = resolve_review_cwd(repo_type)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    # Se não especificou arquivos, usar "."
    if files is None:
        files = ["."]

    if repo_type == "backend":
        # Black
        result = subprocess.run(
            ["black", "--check", "--diff"] + files,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode != 0:
            errors.extend(_parse_black_output(result.stdout))

        # Mypy
        result = subprocess.run(
            ["mypy"] + files, capture_output=True, text=True, cwd=cwd
        )
        if result.returncode != 0:
            mypy_results = _parse_mypy_output(result.stdout)
            errors.extend(mypy_results["errors"])
            warnings.extend(mypy_results["warnings"])

        # Ruff (se disponível)
        ruff_available = subprocess.run(
            ["which", "ruff"], capture_output=True, text=True
        ).returncode == 0

        if ruff_available:
            result = subprocess.run(
                ["ruff", "check"] + files,
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode != 0:
                ruff_results = _parse_ruff_output(result.stdout)
                errors.extend(ruff_results["errors"])
                warnings.extend(ruff_results["warnings"])

    elif repo_type == "frontend":
        # ESLint
        result = subprocess.run(
            ["npx", "eslint", "--format", "json"] + files,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.stdout:
            eslint_results = _parse_eslint_output(result.stdout)
            errors.extend(eslint_results["errors"])
            warnings.extend(eslint_results["warnings"])

        # TypeScript (não aceita files específicos facilmente, usar projeto inteiro)
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"], capture_output=True, text=True, cwd=cwd
        )
        if result.returncode != 0:
            errors.extend(_parse_tsc_output(result.stdout))

    return {
        "linters": {"errors": errors, "warnings": warnings},
        "summary": {"errors": len(errors), "warnings": len(warnings)},
    }


def get_git_diff(cwd: Path | None = None) -> dict[str, Any]:
    """
    Coleta git diff --stat e arquivos modificados (staged + unstaged).

    Args:
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        {
            "files_changed": [...],
            "insertions": 150,
            "deletions": 30,
            "diff_unstaged": "...",
            "diff_staged": "..."
        }
    """
    if cwd is None:
        cwd = Path.cwd()

    # git diff --stat (unstaged)
    result_unstaged = subprocess.run(
        ["git", "-C", str(cwd), "diff", "--stat"],
        capture_output=True,
        text=True,
        check=True
    )

    # git diff --cached --stat (staged)
    result_staged = subprocess.run(
        ["git", "-C", str(cwd), "diff", "--cached", "--stat"],
        capture_output=True,
        text=True,
        check=True
    )

    # Parsear output (unstaged)
    lines = result_unstaged.stdout.strip().split("\n") if result_unstaged.stdout else []
    files_changed = []
    insertions = 0
    deletions = 0

    for line in lines[:-1] if len(lines) > 1 else []:
        if "|" in line:
            file_path = line.split("|")[0].strip()
            files_changed.append(file_path)

    # Última linha: "X files changed, Y insertions(+), Z deletions(-)"
    if lines:
        last_line = lines[-1]
        if "insertion" in last_line:
            parts = last_line.split()
            for i, part in enumerate(parts):
                if part == "insertion" or part == "insertions":
                    insertions = int(parts[i - 1])
        if "deletion" in last_line:
            parts = last_line.split()
            for i, part in enumerate(parts):
                if part == "deletion" or part == "deletions":
                    deletions = int(parts[i - 1])

    # Diff completo (truncado se muito grande)
    result_diff_unstaged = subprocess.run(
        ["git", "-C", str(cwd), "diff"], capture_output=True, text=True, check=True
    )
    result_diff_staged = subprocess.run(
        ["git", "-C", str(cwd), "diff", "--cached"],
        capture_output=True,
        text=True,
        check=True
    )

    diff_unstaged = result_diff_unstaged.stdout[:10000]  # Truncar em 10KB
    diff_staged = result_diff_staged.stdout[:10000]

    return {
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
        "diff_unstaged": diff_unstaged,
        "diff_staged": diff_staged,
    }


def _parse_black_output(output: str) -> list[dict[str, Any]]:
    """Parse black output (linhas com 'would reformat')."""
    errors = []
    for line in output.split("\n"):
        if "would reformat" in line:
            file_path = line.split("would reformat")[1].strip()
            errors.append(
                {"file": file_path, "line": 0, "rule": "black", "message": "Would reformat"}
            )
    return errors


def _parse_mypy_output(output: str) -> dict[str, list[dict[str, Any]]]:
    """Parse mypy output (formato: file.py:10: error: message)."""
    errors = []
    warnings = []

    for line in output.split("\n"):
        if ": error:" in line:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                errors.append(
                    {
                        "file": parts[0],
                        "line": int(parts[1]) if parts[1].isdigit() else 0,
                        "rule": "mypy",
                        "message": parts[3].strip(),
                    }
                )
        elif ": note:" in line or ": warning:" in line:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                warnings.append(
                    {
                        "file": parts[0],
                        "line": int(parts[1]) if parts[1].isdigit() else 0,
                        "rule": "mypy",
                        "message": parts[3].strip(),
                    }
                )

    return {"errors": errors, "warnings": warnings}


def _parse_eslint_output(json_output: str) -> dict[str, list[dict[str, Any]]]:
    """Parse ESLint JSON output."""
    import json

    errors = []
    warnings = []

    data = json.loads(json_output)
    for file_result in data:
        file_path = file_result.get("filePath", "")
        for message in file_result.get("messages", []):
            item = {
                "file": file_path,
                "line": message.get("line", 0),
                "rule": message.get("ruleId", "eslint"),
                "message": message.get("message", ""),
            }
            if message.get("severity") == 2:
                errors.append(item)
            else:
                warnings.append(item)

    return {"errors": errors, "warnings": warnings}


def _parse_tsc_output(output: str) -> list[dict[str, Any]]:
    """Parse TypeScript output (formato: file.ts(10,5): error TS2345: ...)."""
    errors = []
    for line in output.split("\n"):
        if "error TS" in line:
            # Exemplo: src/app.ts(10,5): error TS2345: message
            parts = line.split(":")
            if len(parts) >= 3:
                file_and_pos = parts[0]
                message = ":".join(parts[2:]).strip()

                # Extrair file e linha
                if "(" in file_and_pos:
                    file_path = file_and_pos.split("(")[0]
                    line_num_str = file_and_pos.split("(")[1].split(",")[0]
                    line_num = int(line_num_str) if line_num_str.isdigit() else 0
                else:
                    file_path = file_and_pos
                    line_num = 0

                errors.append(
                    {"file": file_path, "line": line_num, "rule": "tsc", "message": message}
                )

    return errors


def _parse_ruff_output(output: str) -> dict[str, list[dict[str, Any]]]:
    """Parse Ruff output (formato: file.py:10:5: E501 message)."""
    errors = []
    warnings = []

    for line in output.split("\n"):
        if not line.strip():
            continue

        # Exemplo: src/app.py:10:5: E501 Line too long
        parts = line.split(":")
        if len(parts) >= 4:
            file_path = parts[0]
            line_num = int(parts[1]) if parts[1].isdigit() else 0
            # parts[2] é coluna, ignorar
            message_parts = parts[3].strip().split(" ", 1)
            rule = message_parts[0] if message_parts else "ruff"
            message = message_parts[1] if len(message_parts) > 1 else parts[3].strip()

            # Classificar por severidade (E* = errors, W* = warnings)
            if rule.startswith("E") or rule.startswith("F"):
                errors.append(
                    {"file": file_path, "line": line_num, "rule": rule, "message": message}
                )
            else:
                warnings.append(
                    {"file": file_path, "line": line_num, "rule": rule, "message": message}
                )

    return {"errors": errors, "warnings": warnings}

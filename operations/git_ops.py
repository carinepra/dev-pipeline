"""Operações Git (status, add, commit, push, branch)."""

import subprocess
from pathlib import Path
from typing import Any


def get_changed_files(cwd: Path | None = None) -> dict[str, list[str]]:
    """
    git status + parse de arquivos modificados.

    Args:
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        {"modified": [...], "added": [...], "deleted": [...], "untracked": [...]}
    """
    cmd = ["git", "status", "--short"]
    if cwd:
        cmd = ["git", "-C", str(cwd), "status", "--short"]
    
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )

    modified = []
    added = []
    deleted = []
    untracked = []

    for line in result.stdout.split("\n"):
        if not line.strip():
            continue

        status = line[:2]
        file_path = line[3:].strip()

        if status == " M" or status == "M ":
            modified.append(file_path)
        elif status == "A " or status == "AM":
            added.append(file_path)
        elif status == " D" or status == "D ":
            deleted.append(file_path)
        elif status == "??":
            untracked.append(file_path)
        elif status == "MM":  # Modificado em staging e working
            modified.append(file_path)

    return {"modified": modified, "added": added, "deleted": deleted, "untracked": untracked}


def create_branch(branch_name: str, cwd: Path | None = None) -> str:
    """
    Cria e faz checkout de nova branch.

    Args:
        branch_name: Nome da branch
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        Nome da branch criada

    Raises:
        subprocess.CalledProcessError: Se git falhar
    """
    # Verificar se já existe
    if cwd:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--verify", branch_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Branch existe, apenas checkout
            subprocess.run(["git", "-C", str(cwd), "checkout", branch_name], check=True)
        else:
            # Criar nova branch
            subprocess.run(["git", "-C", str(cwd), "checkout", "-b", branch_name], check=True)
    else:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name], capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Branch existe, apenas checkout
            subprocess.run(["git", "checkout", branch_name], check=True)
        else:
            # Criar nova branch
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)

    return branch_name


def commit(files: list[str], message: str, cwd: Path | None = None) -> None:
    """
    git add + commit.

    Args:
        files: Lista de arquivos para adicionar
        message: Mensagem de commit
        cwd: Diretório do repo (None = Path.cwd())
    """
    if cwd:
        # git add
        subprocess.run(["git", "-C", str(cwd), "add"] + files, check=True)
        # git commit
        subprocess.run(["git", "-C", str(cwd), "commit", "-m", message], check=True)
    else:
        # git add
        subprocess.run(["git", "add"] + files, check=True)
        # git commit
        subprocess.run(["git", "commit", "-m", message], check=True)


def push(branch: str | None = None, cwd: Path | None = None) -> None:
    """
    git push (com -u se branch nova).

    Args:
        branch: Nome da branch (None = current branch)
        cwd: Diretório do repo (None = Path.cwd())
    """
    if cwd:
        if branch:
            subprocess.run(["git", "-C", str(cwd), "push", "-u", "origin", branch], check=True)
        else:
            subprocess.run(["git", "-C", str(cwd), "push"], check=True)
    else:
        if branch:
            subprocess.run(["git", "push", "-u", "origin", branch], check=True)
        else:
            subprocess.run(["git", "push"], check=True)


def get_current_branch(cwd: Path | None = None) -> str:
    """
    Retorna nome da branch atual.

    Args:
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        Nome da branch
    """
    cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    if cwd:
        cmd = ["git", "-C", str(cwd)] + cmd[1:]
    
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def get_remote_url(cwd: Path | None = None) -> str:
    """
    Retorna URL do remote origin.

    Args:
        cwd: Diretório do repo (None = Path.cwd())

    Returns:
        URL do remote
    """
    cmd = ["git", "remote", "get-url", "origin"]
    if cwd:
        cmd = ["git", "-C", str(cwd)] + cmd[1:]
    
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()

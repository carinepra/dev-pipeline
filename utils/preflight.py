"""Pre-flight checks (env, git, gh, MCPs)."""

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table


def run_preflight_checks(console: Console | None = None) -> bool:
    """
    Verifica pré-requisitos antes de iniciar pipeline.

    Args:
        console: Console do Rich (opcional)

    Returns:
        False se algum check crítico falhar
    """
    if console is None:
        console = Console()

    checks = []

    # 1. Env vars obrigatórias
    checks.append(("JIRA_EMAIL", os.getenv("JIRA_EMAIL") is not None, "CRITICAL"))
    checks.append(("JIRA_API_TOKEN", os.getenv("JIRA_API_TOKEN") is not None, "CRITICAL"))
    checks.append(("GITHUB_TOKEN", os.getenv("GITHUB_TOKEN") is not None, "CRITICAL"))

    # 2. Git config
    try:
        subprocess.run(
            ["git", "config", "user.name"], check=True, capture_output=True, timeout=5
        )
        checks.append(("Git user.name", True, "CRITICAL"))
    except Exception:
        checks.append(("Git user.name", False, "CRITICAL"))

    try:
        subprocess.run(
            ["git", "config", "user.email"], check=True, capture_output=True, timeout=5
        )
        checks.append(("Git user.email", True, "CRITICAL"))
    except Exception:
        checks.append(("Git user.email", False, "CRITICAL"))

    # 3. GitHub CLI auth
    try:
        subprocess.run(["gh", "auth", "status"], check=True, capture_output=True, timeout=5)
        checks.append(("GitHub CLI auth", True, "CRITICAL"))
    except Exception:
        checks.append(("GitHub CLI auth", False, "CRITICAL"))

    # 4. Python version
    import sys

    python_ok = sys.version_info >= (3, 12)
    checks.append(("Python 3.12+", python_ok, "CRITICAL"))

    # 5. Atlassian MCP (opcional)
    checks.append(("Atlassian MCP", _check_mcp_auth(), "WARNING"))

    # 6. OpenAI API (opcional)
    checks.append(("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY") is not None, "INFO"))

    # Mostrar tabela
    table = Table(title="🔍 Pre-flight Checks")
    table.add_column("Check", style="white")
    table.add_column("Status", width=10)
    table.add_column("Level", width=10)

    has_critical_failure = False
    for name, passed, level in checks:
        icon = "✅" if passed else ("❌" if level == "CRITICAL" else "⚠️")
        color = "green" if passed else ("red" if level == "CRITICAL" else "yellow")
        table.add_row(name, f"[{color}]{icon}[/{color}]", level)
        if not passed and level == "CRITICAL":
            has_critical_failure = True

    console.print(table)

    if has_critical_failure:
        console.print("\n❌ Falha em checks críticos. Configure antes de continuar.\n")
        console.print("Dicas:")
        console.print("  • Configure Git: git config --global user.name 'Your Name'")
        console.print("  • Autentique GitHub CLI: gh auth login")
        console.print("  • Configure .env com JIRA_EMAIL, JIRA_API_TOKEN, GITHUB_TOKEN")
        return False

    return True


def _check_mcp_auth() -> bool:
    """Verifica se Atlassian MCP está autenticado."""
    # Tentar ler MCP auth status (simplificado)
    mcp_auth_file = Path.home() / ".cursor/mcp/user-atlassian/auth.json"
    return mcp_auth_file.exists()

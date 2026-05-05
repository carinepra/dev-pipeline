"""Rich UI components (tables, panels, progress)."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from typing import Any


class PipelineUI:
    """Helper para renderizar UI do pipeline com Rich."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def show_header(self, story_key: str, summary: str, project_name: str | None = None) -> None:
        """Mostra header do pipeline."""
        title = "Dev Pipeline Orchestrator"
        if project_name:
            title += f" — {project_name}"

        self.console.print(
            Panel(
                f"[bold cyan]{title}[/bold cyan]\n\n"
                f"[bold]Story:[/bold] {story_key}\n"
                f"[dim]{summary}[/dim]",
                border_style="cyan",
            )
        )
    
    def show_state(self, state: str, message: str) -> None:
        """Mostra estado atual do pipeline."""
        self.console.print(f"\n[bold cyan]▶ {state}:[/bold cyan] {message}\n")

    def show_tasks_table(self, tasks: list[dict[str, Any]]) -> None:
        """Mostra tabela de tasks propostas."""
        table = Table(title="📋 Tasks Propostas", show_header=True, header_style="bold magenta")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Summary", style="white")
        table.add_column("Type", style="yellow", width=10)
        table.add_column("Estimate", style="green", width=10)
        table.add_column("Depends On", style="dim", width=12)

        for i, task in enumerate(tasks, 1):
            # Converter estimate para string (pode ser int ou string)
            estimate = task.get("estimate", "—")
            estimate_str = str(estimate) if estimate and estimate != "—" else "—"
            
            # Converter depends_on para string (pode ser lista ou string)
            depends_on = task.get("depends_on", "—")
            if isinstance(depends_on, list):
                depends_on_str = ", ".join(depends_on) if depends_on else "—"
            else:
                depends_on_str = str(depends_on) if depends_on else "—"
            
            table.add_row(
                str(i),
                task.get("summary", ""),
                task.get("type", "—") or "—",
                estimate_str,
                depends_on_str,
            )

        self.console.print(table)
        self.console.print(f"\n[dim]Total: {len(tasks)} tasks[/dim]\n")

    def show_files_table(self, files: dict[str, list[str]]) -> None:
        """Mostra tabela de arquivos a commitar."""
        table = Table(title="📦 Files to Commit", show_header=True)
        table.add_column("Status", width=8)
        table.add_column("File", style="white")

        for f in files.get("modified", []):
            table.add_row("[yellow]M[/yellow]", f)
        for f in files.get("added", []):
            table.add_row("[green]A[/green]", f)
        for f in files.get("deleted", []):
            table.add_row("[red]D[/red]", f)

        self.console.print(table)

        # Untracked (NÃO serão commitados)
        if files.get("untracked"):
            self.console.print("\n[dim]Untracked (will NOT commit):[/dim]")
            for f in files["untracked"][:5]:
                self.console.print(f"  [dim]?? {f}[/dim]")
            if len(files["untracked"]) > 5:
                self.console.print(f"  [dim]... e mais {len(files['untracked']) - 5} arquivos[/dim]")

        total = len(files.get("modified", [])) + len(files.get("added", [])) + len(files.get("deleted", []))
        self.console.print(f"\n[bold]Total a commitar: {total} arquivos[/bold]\n")

    def show_progress_panel(self, current_state: str, story_key: str, task_summary: str | None = None) -> None:
        """Mostra painel de progresso."""
        states = [
            ("Story Analysis", "STORY_ANALYSIS"),
            ("Task Breakdown", "TASK_BREAKDOWN"),
            ("Task Planning", "TASK_PLANNING"),
            ("Implementation", "IMPLEMENTATION"),
            ("Review Changes", "REVIEW_CHANGES"),
            ("Git Publish", "GIT_PUBLISH"),
            ("Aguardando Merge", "AGUARDANDO_MERGE"),
            ("Documentation", "DOCUMENTATION"),
        ]

        lines = []
        for name, state_enum in states:
            if state_enum == current_state:
                lines.append(f"🔄 {name} ← [bold cyan]YOU ARE HERE[/bold cyan]")
            elif self._is_before(state_enum, current_state):
                lines.append(f"✅ {name}")
            else:
                lines.append(f"⏳ {name}")

        content = "\n".join(lines)
        if task_summary:
            content += f"\n\n[dim]Current task: {task_summary}[/dim]"

        self.console.print(Panel(content, title="📊 Progress", border_style="blue"))

    def show_skill_instruction(self, skill_name: str, command: str, expected_output: str) -> None:
        """Mostra painel com instrução para executar skill."""
        self.console.print(
            Panel(
                f"[bold cyan]Execute no Cursor:[/bold cyan]\n\n"
                f"  [yellow]{command}[/yellow]\n\n"
                f"[dim]O skill irá processar e gerar output.\n"
                f"Quando concluir, informe o caminho do arquivo gerado.\n\n"
                f"Output esperado: {expected_output}[/dim]",
                title=f"🤖 Skill: {skill_name}",
                border_style="cyan",
            )
        )

    def _is_before(self, state: str, current: str) -> bool:
        """Checa se state vem antes de current na ordem."""
        order = [
            "STORY_ANALYSIS",
            "TASK_BREAKDOWN",
            "TASK_PLANNING",
            "IMPLEMENTATION",
            "REVIEW_CHANGES",
            "GIT_PUBLISH",
            "AGUARDANDO_MERGE",
            "DOCUMENTATION",
        ]
        try:
            return order.index(state) < order.index(current)
        except ValueError:
            return False

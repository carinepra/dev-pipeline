"""Command: status (v2.0)."""

from pathlib import Path

from rich.console import Console

from core.persistence import PipelineState
from utils.pipeline_resolver import resolve_pipeline_key

from cli.commands import format_task_story_label


def cmd_status(
    story: str | None,
    task: str | None,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    """
    Show detailed status of story or task pipeline (v2.0).

    Examples:
        make dev-pipeline-status STORY=PROJ-542
        make dev-pipeline-status TASK=PROJ-645
    """
    from rich.panel import Panel
    from rich.table import Table

    try:
        resolved_story, resolved_task, pipeline_type = resolve_pipeline_key(
            story=story, task=task, persistence=persistence
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    if pipeline_type == "story":
        key = resolved_story
        saved_state = persistence.load_story(key)
        if not saved_state:
            console.print(f"[red]❌ Story não encontrada: {key}[/red]")
            return 1

        console.print(Panel.fit(
            f"""[bold cyan]Story Pipeline: {key}[/bold cyan]
            
[bold]Estado:[/bold] {saved_state['current_state']}
[bold]Criada:[/bold] {saved_state['created_at'][:19]}
[bold]Atualizada:[/bold] {saved_state['updated_at'][:19]}
[bold]Tasks:[/bold] {len(saved_state.get('tasks', []))} task(s)
""",
            title="📊 Status da História",
        ))

        tasks = saved_state.get("tasks", [])
        if tasks:
            console.print("\n📋 [bold]Tasks:[/bold]\n")
            table = Table(show_header=True)
            table.add_column("#", style="dim")
            table.add_column("Key", style="cyan")
            table.add_column("Summary", style="white")
            table.add_column("Estado", style="yellow")
            table.add_column("PR", style="green")

            for idx, t in enumerate(tasks, 1):
                pr_status = t.get("pr_status", "-")
                if pr_status == "merged":
                    icon = "✅"
                elif pr_status == "open":
                    icon = "🔀"
                else:
                    icon = "📝"

                table.add_row(
                    str(idx),
                    t["jira_key"],
                    t.get("summary", "")[:40],
                    f"{icon} {t.get('last_synced_state', 'unknown')}",
                    pr_status,
                )

            console.print(table)

        return 0

    elif pipeline_type == "task":
        key = resolved_task
        saved_state = persistence.load_task(key)
        if not saved_state:
            console.print(f"[red]❌ Task não encontrada: {key}[/red]")
            return 1

        task_data = saved_state.get("task_data", {})
        console.print(Panel.fit(
            f"""[bold cyan]Task Pipeline: {key}[/bold cyan]
            
[bold]Story:[/bold] {format_task_story_label(saved_state.get("story_key"))}
[bold]Estado:[/bold] {saved_state['current_state']}
[bold]Criada:[/bold] {saved_state['created_at'][:19]}
[bold]Atualizada:[/bold] {saved_state['updated_at'][:19]}
[bold]Summary:[/bold] {task_data.get('summary', 'N/A')}
[bold]PR:[/bold] {saved_state.get('pr_url', 'Não criado')}
""",
            title="📊 Status da Task",
        ))

        return 0

    console.print("[red]❌ Tipo de pipeline desconhecido.[/red]")
    return 1

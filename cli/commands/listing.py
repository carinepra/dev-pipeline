"""Commands: list, list-stories, list-tasks (v2.0)."""

from rich.console import Console

from core.persistence import PipelineState

from cli.commands import format_task_story_label


def cmd_list(
    persistence: PipelineState,
    console: Console,
    story_filter: str | None = None,
    state_filter: str | None = None
) -> int:
    """
    List all stories and tasks (v2.0).

    Exibe:
    - Story Pipelines (v2.0) com progresso das tasks
    - Task Pipelines independentes (v2.0)
    - Pipelines v1.0 (monolíticos) ainda não migrados
    """
    from rich.table import Table
    from rich.panel import Panel

    console = Console(width=110, force_terminal=True)

    stories_v2 = persistence.list_active_stories()
    tasks_v2 = persistence.list_active_tasks(story_key=story_filter)
    pipelines_v1 = persistence.list_active()

    if story_filter:
        stories_v2 = [s for s in stories_v2 if s["story_key"] == story_filter]
        pipelines_v1 = [p for p in pipelines_v1 if p["story_key"] == story_filter]

    if not stories_v2 and not tasks_v2 and not pipelines_v1:
        console.print("📭 Nenhum pipeline em andamento.")
        return 0

    if stories_v2:
        _print_stories_section(stories_v2, console)

    if tasks_v2:
        _print_tasks_section(tasks_v2, state_filter, console)

    if pipelines_v1:
        _print_v1_section(pipelines_v1, console)

    return 0


def cmd_list_stories(persistence: PipelineState, console: Console) -> int:
    """List all active stories (v1.0 legacy command)."""
    console.print("[yellow]⚠️ Comando legacy v1.0. Use 'make dev-pipeline-list' para v2.0.[/yellow]\n")
    return cmd_list(persistence, console, None, None)


def cmd_list_tasks(
    persistence: PipelineState,
    console: Console,
    story_filter: str | None = None,
    state_filter: str | None = None
) -> int:
    """List all tasks (v1.0 legacy command)."""
    console.print("[yellow]⚠️ Comando legacy v1.0. Use 'make dev-pipeline-list' para v2.0.[/yellow]\n")
    return cmd_list(persistence, console, story_filter, state_filter)


# ── internal helpers ──────────────────────────────────────────────


def _print_stories_section(stories_v2: list[dict], console: Console) -> None:
    from rich.table import Table
    from utils.config import build_jira_url

    stories_table = Table(title="📚 Story Pipelines (v2.0)", show_header=True)
    stories_table.add_column("Story", style="cyan", no_wrap=True)
    stories_table.add_column("Título", style="white")
    stories_table.add_column("Estado", style="yellow", no_wrap=True)
    stories_table.add_column("Prog", style="green", justify="center")
    stories_table.add_column("Próxima Ação", style="dim")

    for s in stories_v2:
        tasks = s.get("tasks", [])
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("pr_status") == "merged")
        pending_tasks = [t for t in tasks if t.get("pr_status") != "merged"]
        progress = f"{completed}/{total}"

        story_summary = s.get("story_data", {}).get("summary", "")
        if len(story_summary) > 18:
            story_summary = story_summary[:15] + "..."

        state_raw = s["current_state"]
        state_upper = state_raw.upper()

        state_display = {
            "coordinating": "Coordenando",
            "idle": "Idle",
            "completed": "Completo",
            "paused": "Pausado",
            "cancelled": "Cancelado",
            "documentation": "Documentando",
            "error": "Erro",
        }.get(state_raw, state_raw.title())

        if state_upper == "COMPLETED":
            icon = "✅"
        elif state_upper == "PAUSED":
            icon = "⏸️"
        elif state_upper == "CANCELLED":
            icon = "❌"
        else:
            icon = "🔄"

        story_key = s["story_key"]
        if state_upper == "COMPLETED":
            next_action = "✅ Concluído"
        elif state_upper == "CANCELLED":
            next_action = "❌ Cancelado"
        elif state_upper == "PAUSED":
            next_action = f"make dev-pipeline-resume STORY={story_key}"
        elif state_upper in ["ERROR"]:
            next_action = "⚠️ Verificar logs"
        elif state_upper == "COORDINATING":
            if pending_tasks:
                if len(pending_tasks) == 1:
                    next_action = f"⏳ Aguardando {pending_tasks[0]['jira_key']}"
                elif len(pending_tasks) <= 3:
                    task_list = ", ".join([t["jira_key"] for t in pending_tasks])
                    next_action = f"⏳ Aguardando {task_list}"
                else:
                    remaining = len(pending_tasks) - 2
                    first_two = ", ".join([t["jira_key"] for t in pending_tasks[:2]])
                    next_action = f"⏳ Aguardando {first_two} +{remaining}"
            else:
                next_action = f"make dev-pipeline-next STORY={story_key}"
        elif state_upper == "DOCUMENTATION":
            next_action = f"make dev-pipeline-next STORY={story_key}"
        else:
            next_action = f"make dev-pipeline-next STORY={story_key}"

        story_key_link = f"[link={build_jira_url(story_key)}]{story_key}[/link]"

        stories_table.add_row(
            story_key_link,
            story_summary,
            f"{icon} {state_display}",
            progress,
            next_action,
        )

    console.print(stories_table)
    console.print(f"📊 Total: {len(stories_v2)} história(s)\n")


def _print_tasks_section(
    tasks_v2: list[dict], state_filter: str | None, console: Console
) -> None:
    from rich.table import Table
    from utils.config import is_issue_key, build_jira_url

    if state_filter:
        tasks_v2 = [t for t in tasks_v2 if t["current_state"].upper() == state_filter.upper()]

    tasks_with_story = [t for t in tasks_v2 if t.get("story_key")]
    tasks_no_story = [t for t in tasks_v2 if not t.get("story_key")]

    def _row_cells(t: dict) -> tuple[str, str, str, str, str, str]:
        task_key = t["task_key"]
        state = t["current_state"]
        summary = t["task_data"].get("summary", "")
        if len(summary) > 21:
            summary = summary[:18] + "..."
        state_display = {
            "task_discussion": "Discussão",
            "aguardando_merge": "Aguard. Merge",
            "completed": "Completo",
            "planning": "Planejando",
            "task_planning": "Planejando",
            "implementation": "Codificando",
            "review_changes": "Em Review",
            "git_publish": "Publicando",
            "paused": "Pausado",
        }.get(state, state.title())
        if state == "completed":
            icon = "✅"
        elif state == "paused":
            icon = "⏸️"
        elif state == "aguardando_merge":
            icon = "⏳"
        elif state in ["implementation", "review_changes", "git_publish"]:
            icon = "🔄"
        else:
            icon = "📝"
        pr_display = "-"
        pr_url = t.get("pr_url")
        if pr_url:
            pr_num = pr_url.rstrip("/").split("/")[-1]
            pr_display = f"[link={pr_url}]#{pr_num}[/link]"
        if state == "completed":
            next_action = "✅ Concluído"
        elif state == "paused":
            next_action = f"resume TASK={task_key}"
        elif state == "aguardando_merge":
            next_action = "💬 reviews?"
        else:
            next_action = f"next TASK={task_key}"

        if is_issue_key(task_key):
            task_key_link = f"[link={build_jira_url(task_key)}]{task_key}[/link]"
        else:
            task_key_link = task_key

        story_key = t.get("story_key")
        if story_key:
            story_cell = f"[link={build_jira_url(story_key)}]{story_key}[/link]"
        else:
            story_cell = format_task_story_label(None)

        return (story_cell, task_key_link, summary, f"{icon} {state_display}", pr_display, next_action)

    def _print_table(rows: list, title: str, *, include_story_column: bool) -> None:
        if not rows:
            return
        tbl = Table(title=title, show_header=True)
        if include_story_column:
            tbl.add_column("Story", style="cyan", no_wrap=True)
        tbl.add_column("Task", style="cyan", no_wrap=True)
        tbl.add_column("Título", style="white")
        tbl.add_column("Estado", style="yellow", no_wrap=True)
        tbl.add_column("PR", style="dim", no_wrap=True)
        tbl.add_column("Próxima Ação", style="dim")
        for t in rows:
            cells = _row_cells(t)
            if include_story_column:
                tbl.add_row(*cells)
            else:
                tbl.add_row(*cells[1:])
        console.print(tbl)
        console.print(f"📊 Total: {len(rows)} task(s)\n")

        tasks_with_pr = [t for t in rows if t.get("pr_url")]
        if tasks_with_pr:
            console.print("[dim]🔗 PRs abertos:[/dim]")
            for t in tasks_with_pr:
                console.print(f"   [cyan]{t['task_key']}[/cyan]: {t['pr_url']}")
            console.print()

    if tasks_with_story:
        _print_table(tasks_with_story, "📋 Task Pipelines (v2.0)", include_story_column=True)
    if tasks_no_story:
        _print_table(tasks_no_story, "📋 Task Pipelines — sem história (v2.0)", include_story_column=False)


def _print_v1_section(pipelines_v1: list[dict], console: Console) -> None:
    from rich.table import Table

    v1_table = Table(title="⚠️ Pipelines v1.0 (Não Migrados)", show_header=True)
    v1_table.add_column("Story", style="cyan", width=10)
    v1_table.add_column("Estado", style="yellow", width=15)
    v1_table.add_column("Próxima Ação", style="dim", width=50)

    for p in pipelines_v1:
        story_key = p["story_key"]
        state = p["current_state"]

        if state == "COMPLETED":
            icon = "✅"
        elif state == "PAUSED":
            icon = "⏸️"
        else:
            icon = "⚠️"

        next_action = f"make dev-pipeline-migrate STORY={story_key}"

        v1_table.add_row(
            story_key,
            f"{icon} {state}",
            next_action,
        )

    console.print(v1_table)
    console.print(f"⚠️ Total: {len(pipelines_v1)} pipeline(s) não migrado(s)\n")

"""Command: next (advance pipeline) (v2.0)."""

from pathlib import Path

from rich.console import Console

from core.persistence import PipelineState
from pipelines.story_pipeline import StoryPipeline
from pipelines.task_pipeline import TaskPipeline
from utils.pipeline_resolver import resolve_pipeline_key

from cli.commands import reload_task_context_from_json


def cmd_next(
    story: str | None,
    task: str | None,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    """
    Avança para o próximo estágio (v2.0).

    Examples:
        make dev-pipeline-next STORY=HUB-542
        make dev-pipeline-next TASK=HUB-645
    """
    try:
        resolved_story, resolved_task, pipeline_type = resolve_pipeline_key(
            story=story, task=task, persistence=persistence
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    if pipeline_type == "story":
        return _advance_story(resolved_story, state_dir, log_dir, console, persistence)
    elif pipeline_type == "task":
        return _advance_task(resolved_task, state_dir, log_dir, console, persistence)

    console.print("[red]❌ Tipo de pipeline desconhecido.[/red]")
    return 1


def _advance_story(
    key: str,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    saved_state = persistence.load_story(key)
    if not saved_state:
        console.print(f"[red]❌ Story não encontrada: {key}[/red]")
        return 1

    console.print(f"⏭️  Advancing Story Pipeline: {key}...\n")

    pipeline = StoryPipeline(story_key=key, state_dir=state_dir, log_dir=log_dir)
    pipeline.state_data = saved_state

    current = saved_state["current_state"]

    state_map = {
        "story_analysis": pipeline.story_analysis,
        "task_breakdown": pipeline.task_breakdown,
        "coordinating": pipeline.coordinating,
        "documentation": pipeline.documentation,
        "completed": pipeline.completed,
        "paused": pipeline.paused,
        "cancelled": pipeline.cancelled,
    }

    target_state = state_map.get(current)
    if target_state:
        pipeline.current_state = target_state
    else:
        console.print(f"[red]❌ Estado inválido: {current}[/red]")
        return 1

    if current == "story_analysis":
        pipeline.start()
    elif current == "task_breakdown":
        pipeline.breakdown_done()
    elif current == "coordinating":
        pipeline.all_tasks_done()
    elif current == "documentation":
        pipeline.docs_done()
    else:
        console.print(f"[yellow]⚠️ Pipeline em estado final: {current}[/yellow]")
        return 0

    pipeline._save_state()
    saved = persistence.load_story(key)
    console.print(f"✅ Story avançada para: {saved['current_state']}")
    return 0


def _advance_task(
    key: str,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    saved_state = persistence.load_task(key)
    if not saved_state:
        console.print(f"[red]❌ Task não encontrada: {key}[/red]")
        return 1

    console.print(f"⏭️  Advancing Task Pipeline: {key}...\n")

    pipeline = TaskPipeline(
        task_key=key,
        story_key=saved_state.get("story_key"),
        state_dir=state_dir,
        log_dir=log_dir,
    )
    pipeline.state_data = saved_state

    current = saved_state["current_state"]

    if current == "paused":
        paused_from = saved_state.get("paused_from_state")
        if paused_from:
            console.print(f"✅ Task pausada de: [yellow]{paused_from}[/yellow] — avançando...")
            current = paused_from
        else:
            console.print("[red]❌ Task pausada sem paused_from_state definido.[/red]")
            return 1

    state_map = {
        "pending": pipeline.pending,
        "task_discussion": pipeline.task_discussion,
        "task_planning": pipeline.task_planning,
        "implementation": pipeline.implementation,
        "review_changes": pipeline.review_changes,
        "git_publish": pipeline.git_publish,
        "aguardando_merge": pipeline.aguardando_merge,
        "completed": pipeline.completed,
        "paused": pipeline.paused,
        "cancelled": pipeline.cancelled,
    }

    target_state = state_map.get(current)
    if target_state:
        pipeline.current_state = target_state
    else:
        console.print(f"[red]❌ Estado inválido: {current}[/red]")
        return 1

    if current in ("pending", "task_discussion") and saved_state.get("is_new_task"):
        reload_task_context_from_json(pipeline, key, console)

    if current == "pending":
        if saved_state.get("is_new_task"):
            pipeline.start_discussion()
        else:
            pipeline.start_planning()
    elif current == "task_discussion":
        pipeline.discussion_done()
    elif current == "task_planning":
        pipeline.plan_approved()
    elif current == "implementation":
        pipeline.implementation_done()
    elif current == "review_changes":
        pipeline.review_approved()
    elif current == "git_publish":
        pipeline.pr_created()
    elif current == "aguardando_merge":
        return _handle_aguardando_merge(pipeline, saved_state, key, console)
    else:
        console.print(f"[yellow]⚠️ Task em estado final: {current}[/yellow]")
        return 0

    pipeline._save_state()
    saved = persistence.load_task(key)
    console.print(f"✅ Task avançada para: {saved['current_state']}")
    return 0


def _handle_aguardando_merge(pipeline, saved_state: dict, key: str, console: Console) -> int:
    """Verifica merge do PR antes de completar a task."""
    pr_url = saved_state.get("pr_url")
    if not pr_url:
        console.print("[red]❌ Erro: PR URL não encontrada. Task não pode ser completada.[/red]")
        console.print(f"[yellow]💡 Use 'make dev-pipeline-goto git_publish TASK={key}' para criar o PR.[/yellow]")
        return 1

    try:
        from operations.github_ops import get_pr_status_simple
        pr_status = get_pr_status_simple(pr_url)

        if pr_status == "merged":
            console.print(f"[green]✅ PR mergeado confirmado: {pr_url}[/green]")
            pipeline.pr_merged()
        else:
            console.print(f"[yellow]⚠️ PR ainda não foi mergeado (status: {pr_status})[/yellow]")
            console.print(f"   {pr_url}")
            console.print("\n[cyan]💡 Aguarde o merge do PR antes de avançar.[/cyan]")
            console.print("[dim]Se o PR foi recém-mergeado, tente novamente em alguns segundos.[/dim]")
            return 1
    except Exception as e:
        console.print(f"[red]❌ Erro ao verificar status do PR: {e}[/red]")
        console.print(f"[yellow]⚠️ Não foi possível confirmar merge do PR: {pr_url}[/yellow]")

        from questionary import confirm
        force_complete = confirm(
            "O PR foi mergeado? (confirme manualmente)",
            default=False
        ).ask()

        if force_complete:
            console.print("[yellow]⚠️ Completando task baseado em confirmação manual[/yellow]")
            pipeline.pr_merged()
        else:
            console.print("[cyan]✅ Task mantida em aguardando_merge[/cyan]")
            return 1

    pipeline._save_state()
    from core.persistence import PipelineState
    persistence = pipeline.persistence
    saved = persistence.load_task(key)
    console.print(f"✅ Task avançada para: {saved['current_state']}")
    return 0

"""Command: resume (v2.0)."""

from pathlib import Path

from rich.console import Console

from core.persistence import PipelineState
from pipelines.story_pipeline import StoryPipeline
from pipelines.task_pipeline import TaskPipeline
from utils.pipeline_resolver import resolve_pipeline_key

from cli.commands import reload_task_context_from_json


def cmd_resume(
    story: str | None,
    task: str | None,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    """
    Retoma um pipeline pausado ou re-executa o handler do estado atual (v2.0).

    - Se pausado: restaura o estado anterior (paused_from_state) e re-executa o handler.
    - Se não pausado: re-executa o handler do estado atual (útil para retry ou
      quando dados externos foram atualizados, ex: .new-task-context.json).
    """
    try:
        resolved_story, resolved_task, pipeline_type = resolve_pipeline_key(
            story=story, task=task, persistence=persistence
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    if pipeline_type == "story":
        return _resume_story(resolved_story, state_dir, log_dir, console, persistence)
    elif pipeline_type == "task":
        return _resume_task(resolved_task, state_dir, log_dir, console, persistence)

    console.print("[red]❌ Tipo de pipeline desconhecido.[/red]")
    return 1


def _resume_story(
    key: str,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    console.print(f"🔄 Resuming Story Pipeline for {key}...\n")

    saved_state = persistence.load_story(key)
    if not saved_state:
        console.print(f"[red]❌ Story Pipeline não encontrado: {key}[/red]")
        return 1

    pipeline = StoryPipeline(story_key=key, state_dir=state_dir, log_dir=log_dir)
    pipeline.state_data = saved_state

    current_state = saved_state["current_state"]
    if current_state == "paused":
        paused_from = saved_state.get("paused_from_state")
        console.print(f"✅ Story pausada de: [yellow]{paused_from}[/yellow]")

        if paused_from:
            state_map = {
                "story_analysis": pipeline.story_analysis,
                "task_breakdown": pipeline.task_breakdown,
                "coordinating": pipeline.coordinating,
                "documentation": pipeline.documentation,
            }
            target_state = state_map.get(paused_from)
            if target_state:
                pipeline.current_state = target_state
                console.print(f"⏭️  Retomando em {paused_from}...\n")
            else:
                console.print(f"[red]❌ Estado desconhecido: {paused_from}[/red]")
                return 1
    else:
        console.print(f"🔄 Re-executando estado atual: [cyan]{current_state}[/cyan]...\n")

        state_map = {
            "story_analysis": pipeline.story_analysis,
            "task_breakdown": pipeline.task_breakdown,
            "coordinating": pipeline.coordinating,
            "documentation": pipeline.documentation,
        }
        target_state = state_map.get(current_state)
        if not target_state:
            console.print(f"[yellow]⚠️ Estado {current_state} não suporta re-execução[/yellow]")
            return 0

        pipeline.current_state = target_state

        try:
            handler = {
                "story_analysis": pipeline.on_enter_story_analysis,
                "task_breakdown": pipeline.on_enter_task_breakdown,
                "coordinating": pipeline.on_enter_coordinating,
                "documentation": pipeline.on_enter_documentation,
            }.get(current_state)
            if handler:
                handler()
            return 0
        except Exception as e:
            console.print(f"[red]❌ Erro ao re-executar: {e}[/red]")
            return 1

    return 0


def _resume_task(
    key: str,
    state_dir: Path,
    log_dir: Path,
    console: Console,
    persistence: PipelineState,
) -> int:
    saved_state = persistence.load_task(key)
    if not saved_state:
        console.print(f"[red]❌ Task Pipeline não encontrado: {key}[/red]")
        return 1

    console.print(f"🔄 Resuming Task Pipeline for {key}...\n")

    pipeline = TaskPipeline(
        task_key=key,
        story_key=saved_state.get("story_key"),
        state_dir=state_dir,
        log_dir=log_dir,
    )
    pipeline.state_data = saved_state

    current_state = saved_state["current_state"]

    task_state_map = {
        "pending": pipeline.pending,
        "task_discussion": pipeline.task_discussion,
        "task_planning": pipeline.task_planning,
        "implementation": pipeline.implementation,
        "review_changes": pipeline.review_changes,
        "git_publish": pipeline.git_publish,
        "aguardando_merge": pipeline.aguardando_merge,
    }

    task_handlers = {
        "task_discussion": pipeline.on_enter_task_discussion,
        "task_planning": pipeline.on_enter_task_planning,
        "implementation": pipeline.on_enter_implementation,
        "review_changes": pipeline.on_enter_review_changes,
        "git_publish": pipeline.on_enter_git_publish,
        "aguardando_merge": pipeline.on_enter_aguardando_merge,
    }

    if current_state == "paused":
        paused_from = saved_state.get("paused_from_state")
        console.print(f"✅ Task pausada de: [yellow]{paused_from}[/yellow]")

        if paused_from:
            console.print(f"⏭️  Retomando em {paused_from}...\n")

            target_state = task_state_map.get(paused_from)
            if not target_state:
                console.print(f"[red]❌ Estado desconhecido: {paused_from}[/red]")
                return 1

            pipeline.current_state = target_state

            try:
                handler = task_handlers.get(paused_from)
                if handler:
                    handler()
                return 0
            except Exception as e:
                console.print(f"[red]❌ Erro ao retomar pipeline: {e}[/red]")
                return 1
    else:
        console.print(f"🔄 Re-executando estado atual: [cyan]{current_state}[/cyan]...\n")

        target_state = task_state_map.get(current_state)
        if not target_state:
            console.print(f"[yellow]⚠️ Estado {current_state} não suporta re-execução[/yellow]")
            return 0

        pipeline.current_state = target_state

        if current_state in ("pending", "task_discussion"):
            reload_task_context_from_json(pipeline, key, console)

        try:
            if current_state == "pending":
                if saved_state.get("is_new_task"):
                    pipeline.start_discussion()
                else:
                    pipeline.start_planning()
            else:
                handler = task_handlers.get(current_state)
                if handler:
                    handler()
            return 0
        except Exception as e:
            console.print(f"[red]❌ Erro ao re-executar: {e}[/red]")
            return 1

    return 0

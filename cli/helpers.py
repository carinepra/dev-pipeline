"""Helper functions for CLI commands (v2.0)."""

from pathlib import Path

from rich.console import Console

from core.persistence import PipelineState
from utils.pipeline_resolver import resolve_pipeline_key


STORY_STATE_ORDER = [
    "story_analysis", "task_breakdown", "coordinating", "documentation", "completed",
]

TASK_STATE_ORDER = [
    "pending", "task_discussion", "task_planning", "implementation",
    "review_changes", "git_publish", "aguardando_merge", "completed",
]


def cmd_previous(
    story_key: str | None,
    task_key: str | None,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Volta para o estágio anterior do pipeline (Story ou Task).

    Se o pipeline estiver pausado, volta para o paused_from_state.
    Se estiver cancelado, não permite voltar.
    Caso contrário, retrocede um passo na sequência de estados.
    """
    try:
        story, task, pipeline_type = resolve_pipeline_key(story_key, task_key, persistence)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    key = task if task else story

    if pipeline_type == "story":
        saved_state = persistence.load_story(story)
        if not saved_state:
            console.print(f"[red]❌ Story não encontrada: {story}[/red]")
            return 1

        current = saved_state["current_state"]
        order = STORY_STATE_ORDER

        if current == "cancelled":
            console.print(f"[red]❌ Story cancelada — não é possível voltar[/red]")
            return 1

        if current == "paused":
            target = saved_state.get("paused_from_state")
            if not target:
                console.print("[red]❌ Estado paused sem paused_from_state registrado[/red]")
                return 1
            console.print(f"[yellow]⏪ Story pausada — restaurando estado anterior: {target}[/yellow]")
        else:
            if current not in order:
                console.print(f"[red]❌ Estado desconhecido: {current}[/red]")
                return 1
            idx = order.index(current)
            if idx == 0:
                console.print(f"[yellow]⚠️  Já está no primeiro estágio ({current})[/yellow]")
                return 0
            target = order[idx - 1]

        console.print(f"[yellow]⏪ Recovery mode: {current} → {target}[/yellow]")
        saved_state["current_state"] = target
        persistence.save_story(story, saved_state)
        console.print(f"✅ Story voltou para: [cyan]{target}[/cyan]")

    else:  # task
        saved_state = persistence.load_task(task)
        if not saved_state:
            console.print(f"[red]❌ Task não encontrada: {task}[/red]")
            return 1

        current = saved_state["current_state"]
        order = TASK_STATE_ORDER

        if current == "cancelled":
            console.print(f"[red]❌ Task cancelada — não é possível voltar[/red]")
            return 1

        if current == "paused":
            target = saved_state.get("paused_from_state")
            if not target:
                console.print("[red]❌ Estado paused sem paused_from_state registrado[/red]")
                return 1
            console.print(f"[yellow]⏪ Task pausada — restaurando estado anterior: {target}[/yellow]")
        else:
            if current not in order:
                console.print(f"[red]❌ Estado desconhecido: {current}[/red]")
                return 1
            idx = order.index(current)
            if idx == 0:
                console.print(f"[yellow]⚠️  Já está no primeiro estágio ({current})[/yellow]")
                return 0
            target = order[idx - 1]

        console.print(f"[yellow]⏪ Recovery mode: {current} → {target}[/yellow]")
        saved_state["current_state"] = target
        persistence.save_task(task, saved_state)
        console.print(f"✅ Task voltou para: [cyan]{target}[/cyan]")

    console.print(f"[dim]Use 'make dev-pipeline-next' para avançar novamente[/dim]")
    return 0


def cmd_cancel(
    story_key: str | None,
    task_key: str | None,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Cancel pipeline (Story ou Task) e marca como cancelled (v2.0).

    Args:
        story_key: Story key (opcional)
        task_key: Task key (opcional)
        persistence: PipelineState instance
        console: Rich console

    Returns:
        Exit code
    """
    try:
        story, task, pipeline_type = resolve_pipeline_key(story_key, task_key, persistence)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    key = task if task else story
    console.print(f"❌ Canceling {pipeline_type} {key}...")

    # Carregar estado v2.0
    if pipeline_type == "story":
        saved_state = persistence.load_story(story)
        if not saved_state:
            console.print(f"[red]❌ No saved story state for {story}[/red]")
            return 1
        
        saved_state["current_state"] = "cancelled"
        persistence.save_story(story, saved_state)
        console.print(f"✅ Story {story} cancelada")
        console.print(f"[dim]Estado salvo em: .pipeline-state/{story}-story.json[/dim]")
    
    else:  # task
        saved_state = persistence.load_task(task)
        if not saved_state:
            console.print(f"[red]❌ No saved task state for {task}[/red]")
            return 1
        
        saved_state["current_state"] = "cancelled"
        persistence.save_task(task, saved_state)
        console.print(f"✅ Task {task} cancelada")
        console.print(f"[dim]Estado salvo em: .pipeline-state/{task}-task.json[/dim]")

    return 0


def cmd_goto(
    story_key: str | None,
    task_key: str | None,
    target_stage: str,
    state_dir: Path,
    log_dir: Path,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Go to specific stage (recovery mode - v2.0).

    Args:
        story_key: Story key (opcional)
        task_key: Task key (opcional)
        target_stage: Target state (lowercase: story_analysis, task_planning, etc)
        state_dir: State directory
        log_dir: Log directory
        persistence: PipelineState instance
        console: Rich console

    Returns:
        Exit code
    """
    try:
        story, task, pipeline_type = resolve_pipeline_key(story_key, task_key, persistence)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    key = task if task else story
    console.print(f"🎯 Going to stage '{target_stage}' for {pipeline_type} {key}...")

    # Carregar estado v2.0
    if pipeline_type == "story":
        saved_state = persistence.load_story(story)
        if not saved_state:
            console.print(f"[red]❌ No saved story state for {story}[/red]")
            return 1
        
        current = saved_state["current_state"]
        
        # Validar estado target existe (StoryPipeline states)
        valid_states = [
            "story_analysis", "task_breakdown", "coordinating",
            "documentation", "completed", "paused", "cancelled"
        ]
        if target_stage not in valid_states:
            console.print(f"[red]❌ Invalid story state: {target_stage}[/red]")
            console.print(f"Valid: {valid_states}")
            return 1
        
        console.print(f"[yellow]⚠️  Recovery mode: {current} → {target_stage}[/yellow]")
        saved_state["current_state"] = target_stage
        persistence.save_story(story, saved_state)
        console.print(f"✅ Story moved to: [cyan]{target_stage}[/cyan]")
    
    else:  # task
        saved_state = persistence.load_task(task)
        if not saved_state:
            console.print(f"[red]❌ No saved task state for {task}[/red]")
            return 1
        
        current = saved_state["current_state"]
        
        # Validar estado target existe (TaskPipeline states)
        valid_states = [
            "pending", "task_planning", "task_discussion", "implementation",
            "review_changes", "git_publish", "aguardando_merge", "completed",
            "paused", "cancelled"
        ]
        if target_stage not in valid_states:
            console.print(f"[red]❌ Invalid task state: {target_stage}[/red]")
            console.print(f"Valid: {valid_states}")
            return 1
        
        console.print(f"[yellow]⚠️  Recovery mode: {current} → {target_stage}[/yellow]")
        saved_state["current_state"] = target_stage
        persistence.save_task(task, saved_state)
        console.print(f"✅ Task moved to: [cyan]{target_stage}[/cyan]")

    console.print(f"[dim]Use 'make dev-pipeline-next' to continue[/dim]")
    return 0


def cmd_unlock(
    story_key: str | None,
    task_key: str | None,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Force unlock pipeline (v2.0).

    Args:
        story_key: Story key (opcional)
        task_key: Task key (opcional)
        persistence: PipelineState instance
        console: Rich console

    Returns:
        Exit code
    """
    try:
        story, task, pipeline_type = resolve_pipeline_key(story_key, task_key, persistence)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    key = task if task else story
    console.print(f"🔓 Force unlocking {pipeline_type} {key}...")
    
    # v2.0: force_unlock funciona com qualquer key
    persistence.force_unlock(key)
    console.print("✅ Unlocked")
    return 0


def cmd_validate(
    story_key: str | None,
    task_key: str | None,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Validate state JSON (v2.0).

    Args:
        story_key: Story key (opcional)
        task_key: Task key (opcional)
        persistence: PipelineState instance
        console: Rich console

    Returns:
        Exit code
    """
    from core.persistence import (
        StoryPipelineSchema,
        TaskPipelineSchema,
    )
    from pydantic import ValidationError

    try:
        story, task, pipeline_type = resolve_pipeline_key(story_key, task_key, persistence)
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    key = task if task else story
    console.print(f"🔍 Validating {pipeline_type} state for {key}...\n")

    # Carregar e validar schema v2.0
    if pipeline_type == "story":
        saved_state = persistence.load_story(story)
        if not saved_state:
            console.print(f"[red]❌ No saved story state for {story}[/red]")
            return 1
        
        try:
            StoryPipelineSchema(**saved_state)
            console.print("✅ Story state is valid (v2.0 schema)")
            return 0
        except ValidationError as e:
            console.print(f"[red]❌ Story state is invalid:[/red]\n{e}")
            return 1
    
    else:  # task
        saved_state = persistence.load_task(task)
        if not saved_state:
            console.print(f"[red]❌ No saved task state for {task}[/red]")
            return 1
        
        try:
            TaskPipelineSchema(**saved_state)
            console.print("✅ Task state is valid (v2.0 schema)")
            return 0
        except ValidationError as e:
            console.print(f"[red]❌ Task state is invalid:[/red]\n{e}")
            return 1


def cmd_finalize(
    story_key: str,
    state_dir: Path,
    log_dir: Path,
    persistence: PipelineState,
    console: Console,
) -> int:
    """
    Finaliza história: documentação + cleanup (v2.0).

    Fluxo:
    1. Valida StoryPipeline existe e está em coordinating/paused
    2. Valida todas TaskPipelines foram mergeadas
    3. Transita StoryPipeline para documentation
    4. Executa on_enter_documentation (skill-create-docs)
    5. Cleanup automático

    Args:
        story_key: Story key (ex: PROJ-542)
        state_dir: State directory
        log_dir: Log directory
        persistence: PipelineState instance
        console: Rich console

    Returns:
        Exit code
    """
    from rich.panel import Panel
    from pipelines.story_pipeline import StoryPipeline

    console.print(
        Panel(
            f"[bold cyan]Finalizando História {story_key}[/bold cyan]\n\n"
            f"[dim]Este comando irá:[/dim]\n"
            f"  1. Validar todas tasks foram mergeadas\n"
            f"  2. Gerar documentação técnica consolidada\n"
            f"  3. Revisar qualidade automaticamente\n"
            f"  4. Abrir PR de documentação\n"
            f"  5. Limpar arquivos temporários",
            title="📚 Finalização de História (v2.0)",
            border_style="cyan",
        )
    )
    console.print()

    # 1. Verificar se story existe
    story_state = persistence.load_story(story_key)
    if not story_state:
        console.print(f"[red]❌ Story {story_key} não encontrada[/red]")
        console.print(f"[dim]Use 'make dev-pipeline-list' para ver stories ativas[/dim]")
        return 1

    # 2. Validar estado atual da story
    current_state = story_state.get("current_state")
    valid_states = ["coordinating", "paused", "documentation"]

    if current_state not in valid_states:
        console.print(f"[red]❌ Estado inválido para finalização: {current_state}[/red]")
        console.print(f"[yellow]Estados válidos: {', '.join(valid_states)}[/yellow]")
        console.print(
            f"\n[dim]A story precisa estar em coordinating (todas tasks prontas) ou paused.[/dim]"
        )
        return 1

    # 3. Verificar se todas tasks foram mergeadas
    tasks = persistence.list_active_tasks(story_key)

    if not tasks:
        console.print(f"[yellow]⚠️  Nenhuma task encontrada para {story_key}[/yellow]")
        console.print(f"[dim]Story sem tasks - prosseguindo com documentação...[/dim]\n")
    else:
        # Verificar estado de cada task
        pending_tasks = []
        for task_file in tasks:
            task_key = task_file.stem.replace("-task", "")
            task_state = persistence.load_task(task_key)

            if not task_state:
                continue

            state = task_state.get("current_state")
            pr_url = task_state.get("pr_url")
            pr_status = task_state.get("pr_status")

            # Task precisa estar completed OU aguardando_merge com PR merged
            is_done = state == "completed" or (
                state == "aguardando_merge" and pr_status == "MERGED"
            )

            if not is_done:
                pending_tasks.append(
                    {"key": task_key, "state": state, "pr_url": pr_url, "pr_status": pr_status}
                )

        if pending_tasks:
            console.print(f"[red]❌ {len(pending_tasks)} task(s) não finalizadas:[/red]\n")

            for task in pending_tasks:
                console.print(f"   - {task['key']}: {task['state']}")
                if task["pr_url"]:
                    console.print(f"     PR: {task['pr_url']} (status: {task['pr_status']})")
                else:
                    console.print(f"     [yellow]PR não criada[/yellow]")

            console.print(f"\n[yellow]Finalize todas tasks antes de gerar documentação.[/yellow]")
            return 1

        console.print(f"[green]✅ Todas {len(tasks)} tasks mergeadas[/green]\n")

    # 4. Restaurar StoryPipeline e transitar para documentation
    console.print(f"Restaurando StoryPipeline e transitando para DOCUMENTATION...\n")

    try:
        pipeline = StoryPipeline(
            story_key=story_key, state_dir=state_dir, log_dir=log_dir, dry_run=False
        )

        # Carregar estado
        pipeline.state_data = story_state

        # Restaurar estado da máquina de estados
        if current_state == "coordinating":
            pipeline._set_state(pipeline.coordinating)
        elif current_state == "paused":
            pipeline._set_state(pipeline.paused)
        elif current_state == "documentation":
            # Já está em documentation, apenas re-executar
            pipeline._set_state(pipeline.documentation)

        # Transitar para documentation (se necessário)
        if current_state != "documentation":
            console.print(f"[cyan]→ Transitando para documentation...[/cyan]\n")
            pipeline.all_tasks_done()  # coordinating → documentation
        else:
            console.print(f"[cyan]→ Re-executando documentation...[/cyan]\n")
            pipeline.on_enter_documentation()

        console.print(f"\n[green]✅ História finalizada com sucesso![/green]")
        return 0

    except Exception as e:
        console.print(f"[red]❌ Erro ao finalizar: {e}[/red]")
        console.print(f"[dim]Log: {log_dir / f'pipeline-{story_key}.log'}[/dim]")
        return 1

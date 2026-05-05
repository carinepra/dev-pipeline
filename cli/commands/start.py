"""Commands: start, start_new_task (v2.0)."""

from pathlib import Path

from rich.console import Console

from core.constants import PipelineStateEnum
from core.persistence import PipelineState
from pipelines.story_pipeline import StoryPipeline
from pipelines.task_pipeline import TaskPipeline
from utils.pipeline_resolver import resolve_pipeline_key
from utils.preflight import run_preflight_checks
from utils.validators import PipelineValidators


def _ask_component_and_repo(project_key: str, console: Console) -> tuple[str, str | None]:
    """
    Pergunta ao usuário o tipo (Front/Back) e o repositório específico a usar.

    Quando há apenas um repo do tipo escolhido, seleciona automaticamente.
    Quando há múltiplos, exibe lista para o usuário escolher.

    Returns:
        (component, repo_id) — component é "Front" ou "Back";
        repo_id é None se o usuário cancelar.
    """
    from questionary import select as q_select
    from utils.config import get_repos_by_type

    component = q_select(
        "Esta task é de Front ou Back?",
        choices=[
            {"name": "⚛️  Front (frontend)", "value": "Front"},
            {"name": "🐍 Back (backend / infra)", "value": "Back"},
        ],
    ).ask()

    if not component:
        return ("Front", None)

    repo_type = "frontend" if component == "Front" else "backend"
    candidates = get_repos_by_type(project_key, repo_type)

    if not candidates:
        console.print(
            f"[red]❌ Nenhum repositório do tipo '{repo_type}' configurado "
            f"para o projeto '{project_key}'.[/red]"
        )
        return (component, None)

    if len(candidates) == 1:
        repo_id = candidates[0]["id"]
        console.print(
            f"[dim]Repositório selecionado automaticamente: {repo_id}[/dim]"
        )
        return (component, repo_id)

    choices = [
        {
            "name": f"{r['id']}  ({r.get('tech_stack', '?')} · {r.get('local_path', '?')})",
            "value": r["id"],
        }
        for r in candidates
    ]
    repo_id = q_select(
        f"Qual repositório {component} esta task impacta?",
        choices=choices,
    ).ask()

    return (component, repo_id)


def cmd_start(
    story: str | None,
    task: str | None,
    state_dir: Path,
    log_dir: Path,
    console: Console,
) -> int:
    """
    Inicia um pipeline (v2.0).

    Examples:
        make dev-pipeline-start STORY=HUB-542
        make dev-pipeline-start TASK=HUB-645
        make dev-pipeline-start TASK=NEW
        make dev-pipeline-start TASK=NEW STORY=HUB-542
    """
    from utils.pipeline_resolver import TASK_NEW_FLAG

    try:
        resolved_story, resolved_task, pipeline_type = resolve_pipeline_key(
            story=story, task=task, persistence=PipelineState(state_dir=state_dir)
        )
    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        return 1

    if pipeline_type == "new_task":
        return cmd_start_new_task(resolved_story, state_dir, log_dir, console)

    if pipeline_type == "story":
        key = resolved_story
        console.print(f"\n🚀 Starting Story Pipeline for {key}...\n")

        run_preflight_checks(console)

        pipeline = StoryPipeline(story_key=key, state_dir=state_dir, log_dir=log_dir)

        saved_state = pipeline.persistence.load_story(key)
        if saved_state:
            current = saved_state["current_state"]
            if current.lower() not in ["completed", "cancelled"]:
                console.print(f"[yellow]⚠️ Story já iniciada (estado: {current})[/yellow]")
                console.print(
                    f"[dim]Use 'make dev-pipeline-resume STORY={key}' para retomar.[/dim]"
                )
                return 1

        pipeline.start_story()
        console.print("✅ Story pipeline started successfully!")
        return 0

    elif pipeline_type == "task":
        key = resolved_task
        parent_story = resolved_story
        console.print(f"\n🚀 Starting Task Pipeline for {key}...\n")

        run_preflight_checks(console)

        if not resolved_story:
            console.print(f"[yellow]📌 Task standalone (sem história pai)[/yellow]\n")

        pipeline = TaskPipeline(
            task_key=key,
            story_key=parent_story,
            state_dir=state_dir,
            log_dir=log_dir,
        )

        saved_state = pipeline.persistence.load_task(key)
        if saved_state:
            current = saved_state["current_state"]
            if current.lower() not in ["completed", "cancelled"]:
                console.print(f"[yellow]⚠️ Task já iniciada (estado: {current})[/yellow]")
                console.print(
                    f"[dim]Use 'make dev-pipeline-resume TASK={key}' para retomar.[/dim]"
                )
                return 1

        from utils.config import extract_project_key, get_default_project
        project_key = get_default_project()
        try:
            project_key = extract_project_key(key)
        except ValueError:
            pass

        component, target_repo = _ask_component_and_repo(project_key, console)
        if target_repo is None:
            console.print("[yellow]Cancelado pelo usuário.[/yellow]")
            return 0

        pipeline.init_new_task(
            task_summary=key,
            component=component,
            is_new_task=False,
            project_key=project_key,
            target_repos=[target_repo],
        )
        console.print("✅ Task pipeline started successfully!")
        return 0

    console.print("[red]❌ Tipo de pipeline desconhecido.[/red]")
    return 1


def cmd_start_new_task(
    story_key: str | None,
    state_dir: Path,
    log_dir: Path,
    console: Console,
) -> int:
    """
    Inicia pipeline para task não criada (TASK=NEW).

    Workflow:
    1. Valida parent story (se fornecida)
    2. Coleta contexto via questionary
    3. Cria TaskPipeline com temp key
    4. Task discussion -> cria no Jira -> planning
    """
    import json
    import uuid
    from datetime import datetime, timezone

    from questionary import confirm, select, text
    from rich.panel import Panel
    from rich.table import Table

    from utils.config import extract_project_key, get_default_project, list_project_keys
    from utils.paths import get_task_context_path

    console.print("\n[bold cyan]🆕 Criar Nova Task[/bold cyan]\n")

    # 1. Perguntar sobre história pai (se não fornecida)
    if not story_key:
        has_parent = confirm(
            "Esta task faz parte de alguma história (story) existente?",
            default=False
        ).ask()

        if has_parent:
            story_key = text(
                "Key da história (ex: HUB-542, INVEST-100):",
                validate=lambda s: bool(__import__('re').match(r'^[A-Z][A-Z0-9]*-\d+$', s.strip().upper())) or "Formato inválido (ex: HUB-542)"
            ).ask()

            if not story_key:
                console.print("[yellow]Cancelado pelo usuário[/yellow]")
                return 0

            story_key = story_key.strip().upper()

            story_file = state_dir / f"{story_key}-story.json"
            if not story_file.exists():
                console.print(f"[red]❌ Story {story_key} não encontrada[/red]")
                console.print(f"[dim]Verifique se a key está correta ou crie a story primeiro[/dim]")
                return 1

            console.print(f"[green]✅ Vinculada à história: {story_key}[/green]\n")
        else:
            console.print("[yellow]📌 Task standalone (sem história pai)[/yellow]\n")
    else:
        story_file = state_dir / f"{story_key}-story.json"
        if not story_file.exists():
            console.print(f"[red]❌ Story {story_key} não encontrada[/red]")
            return 1
        console.print(f"[green]✅ Vinculada à história: {story_key}[/green]\n")

    # 1.5. Determinar projeto Jira
    project_key = None
    if story_key:
        try:
            project_key = extract_project_key(story_key)
        except ValueError:
            pass

    if not project_key:
        available_projects = list_project_keys()
        if len(available_projects) > 1:
            validators_inst = PipelineValidators(console)
            project_key = validators_inst.ask_jira_project()
        elif len(available_projects) == 1:
            project_key = available_projects[0]
        else:
            project_key = get_default_project()

    console.print(f"[dim]Projeto Jira: {project_key}[/dim]\n")

    # 2. Coletar escopo inicial (mínimo)
    console.print("[bold]Vamos discutir o escopo da task:[/bold]\n")

    try:
        initial_scope = text(
            "Descreva brevemente o que precisa ser feito:",
            validate=lambda d: len(d.strip()) >= 20 or "Descrição muito curta (mín 20 chars)",
            multiline=False
        ).ask()

        if not initial_scope:
            console.print("[yellow]Cancelado pelo usuário[/yellow]")
            return 0

        additional_context = text(
            "Links relevantes (Figma, docs, PRs) - opcional:",
            default=""
        ).ask()

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelado pelo usuário[/yellow]")
        return 0

    # 2.5. Perguntar componente e repositório alvo
    component, target_repo = _ask_component_and_repo(project_key, console)
    if target_repo is None:
        console.print("[yellow]Cancelado pelo usuário.[/yellow]")
        return 0

    # 3. Salvar contexto inicial em arquivo para discussão
    temp_key = f"_new-{uuid.uuid4().hex[:8]}"

    context_file = get_task_context_path(temp_key)
    context_file.parent.mkdir(parents=True, exist_ok=True)

    initial_context = {
        "_instructions": "🎯 PLANEJAMENTO DE TASK STANDALONE - Leia com atenção!",
        "_context": "Esta é uma TASK individual, NÃO uma história (story). Ajude a refinar os detalhes técnicos.",
        "_type": "single_task",
        "_workflow": [
            "1. Leia o escopo inicial abaixo",
            "2. Faça perguntas técnicas para refinar (arquitetura, APIs, etc)",
            "3. Sugira um título conciso para a task",
            "4. Determine o component apropriado (Back/Front/Infra/Docs)",
            "5. Liste acceptance criteria claros e testáveis",
            "6. Defina priority (High/Medium/Low)",
            "7. ATUALIZE este JSON com os campos finais (veja estrutura abaixo)"
        ],
        "_required_fields": {
            "title": "Título conciso da task (será o summary no Jira)",
            "description": "Descrição técnica detalhada (pode expandir o escopo inicial)",
            "component": "Back | Front | Infra | Docs | null",
            "priority": "High | Medium | Low",
            "acceptance_criteria": "Lista de critérios testáveis (string com \\n entre itens)"
        },
        "temp_key": temp_key,
        "project_key": project_key,
        "parent_story": story_key if story_key else None,
        "parent_story_note": "null = task standalone" if not story_key else f"Task vinculada à {story_key}",
        "initial_scope": initial_scope,
        "additional_context": additional_context or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": None,
        "description": None,
        "component": component,
        "target_repo": target_repo,
        "priority": "Medium",
        "acceptance_criteria": None,
        "figma_url": None
    }
    context_file.write_text(json.dumps(initial_context, indent=2, ensure_ascii=False))

    # 4. Criar pipeline AGORA (em task_discussion) para aparecer no list
    console.print(f"\n[dim]Criando pipeline: {temp_key}[/dim]\n")

    try:
        pipeline = TaskPipeline(
            task_key=temp_key,
            story_key=story_key,
            state_dir=state_dir,
            log_dir=log_dir,
            dry_run=False
        )

        pipeline.init_new_task(
            task_summary=initial_context.get("initial_scope", "")[:80],
            component=component,
            is_new_task=True,
            collected_context=initial_context,
            project_key=project_key,
            target_repos=[target_repo] if target_repo else [],
        )

        console.print(f"[green]✅ Pipeline criada: {temp_key} (estado: task_discussion)[/green]")
        console.print(f"[dim]State file: {state_dir}/{temp_key}-task.json[/dim]")
        console.print(f"[dim]Já aparece no: make dev-pipeline-list[/dim]\n")

    except Exception as e:
        console.print(f"[red]❌ Erro ao criar pipeline: {e}[/red]")
        return 1

    # 5. Redirecionar para discussão no chat do Cursor
    console.print("="*80 + "\n")
    console.print(Panel(
        f"[bold cyan]💬 DISCUSSÃO TÉCNICA NO CHAT DO CURSOR[/bold cyan]\n\n"
        f"[yellow]📋 Contexto salvo:[/yellow] {context_file}\n\n"
        f"[green]🎯 Execute no Cursor:[/green]\n\n"
        f"   [bold cyan]@pipeline-task-definer {context_file}[/bold cyan]\n\n"
        f"[dim]A skill vai:[/dim]\n"
        f"   • Ler o contexto inicial\n"
        f"   • Fazer perguntas técnicas\n"
        f"   • Definir título, component, ACs, priority\n"
        f"   • Atualizar o JSON automaticamente\n\n"
        f"[yellow]Quando a skill concluir, volte aqui e pressione ENTER[/yellow]",
        title="💬 Discussão Técnica",
        border_style="cyan"
    ))

    from questionary import press_any_key_to_continue
    press_any_key_to_continue(
        "\n[bold yellow]⏸ Pipeline em discussão[/bold yellow] - "
        "[bold]Pressione ENTER após atualizar o JSON no chat[/bold]"
    ).ask()

    # 6. Recarregar contexto (pode ter sido modificado no chat)
    console.print("\n[cyan]⏳ Recarregando contexto (verificando modificações do chat)...[/cyan]")
    try:
        with open(context_file, encoding="utf-8") as f:
            final_context = json.load(f)
    except FileNotFoundError:
        console.print(f"[red]❌ Arquivo não encontrado: {context_file}[/red]")
        return 1
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ JSON inválido: {e}[/red]")
        return 1

    required_fields = ["title", "description"]
    missing = [f for f in required_fields if not final_context.get(f)]
    if missing:
        console.print(f"[red]❌ Campos obrigatórios faltando: {', '.join(missing)}[/red]")
        console.print("[yellow]Atualize o JSON no chat e tente novamente[/yellow]")
        return 1

    # 7. Mostrar resumo e confirmar
    console.print("\n[green]✅ Contexto atualizado![/green]\n")
    console.print(Panel(
        f"[cyan]Título:[/cyan] {final_context.get('title', 'N/A')}\n"
        f"[cyan]Descrição:[/cyan] {final_context.get('description', 'N/A')[:80]}...\n"
        f"[cyan]Component:[/cyan] {final_context.get('component', 'N/A')}\n"
        f"[cyan]Parent Story:[/cyan] {story_key or 'Nenhuma (standalone)'}\n"
        f"[cyan]Priority:[/cyan] {final_context.get('priority', 'Medium')}\n"
        f"[cyan]Acceptance Criteria:[/cyan] {'Sim' if final_context.get('acceptance_criteria') else 'Não'}",
        title="📋 Resumo Final da Task",
        border_style="cyan"
    ))

    confirmed = confirm(
        "Confirmar e avançar para criação no Jira?",
        default=True
    ).ask()

    if not confirmed:
        console.print("[yellow]Pipeline mantida em task_discussion.[/yellow]")
        console.print(f"[dim]Para retomar: make dev-pipeline-resume TASK={temp_key}[/dim]")
        return 0

    # 8. Atualizar pipeline com contexto refinado e prosseguir
    console.print(f"\n[cyan]Avançando pipeline {temp_key} para criação no Jira...[/cyan]\n")

    pipeline.load_existing_task()
    pipeline.state_data["collected_context"] = final_context
    pipeline.state_data["task_data"]["summary"] = final_context.get("title", "")
    pipeline._save_state()

    pipeline.on_enter_task_discussion()

    console.print(f"[green]✅ Fluxo concluído![/green]")
    console.print(f"[dim]Use 'make dev-pipeline-list' para ver a task criada[/dim]\n")

    return 0

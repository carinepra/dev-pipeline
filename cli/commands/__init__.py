"""CLI command modules for Dev Pipeline Orchestrator (v2.0)."""

from rich.console import Console


def reload_task_context_from_json(pipeline, key: str, console: Console) -> bool:
    """
    Recarrega collected_context do .new-task-context.json no state_data.
    Retorna True se o contexto foi recarregado com sucesso.
    """
    import json
    from utils.paths import get_task_context_path

    context_file = get_task_context_path(key)
    if not context_file.exists():
        return False

    try:
        with open(context_file, encoding="utf-8") as f:
            fresh_context = json.load(f)
        pipeline.state_data["collected_context"] = fresh_context
        pipeline.state_data["task_data"]["summary"] = fresh_context.get("title", "")
        console.print(f"[green]✅ Contexto recarregado de {context_file}[/green]\n")
        return True
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ JSON inválido em {context_file}: {e}[/red]")
        return False


def format_task_story_label(story_key: str | None) -> str:
    """Texto para coluna Story / painel de status (task avulsa = sem história pai)."""
    if not story_key:
        return "Sem história"
    return story_key

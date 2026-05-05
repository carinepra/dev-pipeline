"""Resolve STORY e TASK keys, inferindo um do outro quando necessário."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.persistence import PipelineState

# Constantes
TASK_NEW_FLAG = "NEW"


def resolve_pipeline_key(
    story: str | None,
    task: str | None,
    persistence: PipelineState,
) -> tuple[str | None, str | None, str]:
    """
    Resolve STORY e TASK, inferindo um do outro se necessário.
    
    MELHORIA #15: Valida que TASK pertence a STORY quando ambos são fornecidos.
    
    Args:
        story: Story key fornecido (ex: HUB-542)
        task: Task key fornecido (ex: HUB-645 ou "NEW")
        persistence: PipelineState instance
    
    Returns:
        (story_key or None, task_key or None, pipeline_type)
        pipeline_type: "story", "task", "new_task", ou "unknown"
    
    Examples:
        STORY=HUB-542           → ("HUB-542", None, "story")
        TASK=HUB-645            → ("HUB-542", "HUB-645", "task")  # infere story
        TASK=HUB-645 avulsa     → (None, "HUB-645", "task")      # sem história
        STORY=HUB-542 TASK=645  → ("HUB-542", "HUB-645", "task") # valida
        TASK=NEW                → (None, "NEW", "new_task")
        TASK=NEW STORY=HUB-542  → ("HUB-542", "NEW", "new_task")
    
    Raises:
        ValueError: Se nenhum fornecido ou se validação falhar
    """
    if not story and not task:
        raise ValueError("Forneça STORY ou TASK")
    
    # Caso especial: TASK=NEW (task não criada)
    if task and task.upper() == TASK_NEW_FLAG:
        # Validar story se fornecida
        if story:
            story_file = persistence.state_dir / f"{story}-story.json"
            if not story_file.exists():
                raise ValueError(f"Story {story} não encontrada")
        
        return (story, TASK_NEW_FLAG, "new_task")
    
    # Caso 1: Apenas STORY fornecida
    if story and not task:
        return (story, None, "story")
    
    # Caso 2: Apenas TASK fornecida
    if task and not story:
        # Buscar story_key da task
        task_file = persistence.state_dir / f"{task}-task.json"
        if task_file.exists():
            task_data = json.loads(task_file.read_text())
            story_key = task_data.get("story_key")  # Pode ser None (task avulsa)
            return (story_key, task, "task")
        else:
            # Task pipeline não existe, buscar em stories
            story_key = find_story_for_task(task, persistence)
            return (story_key, task, "task")
    
    # Caso 3: Ambos fornecidos → MELHORIA #15: validar consistência
    if story and task:
        # Normalizar task: só prefixar se task é número puro (ex: 645 → HUB-645)
        if task.isdigit():
            task = f"{story.split('-')[0]}-{task}"
        
        task_file = persistence.state_dir / f"{task}-task.json"
        if task_file.exists():
            task_data = json.loads(task_file.read_text())
            task_story = task_data.get("story_key")
            
            # Validar: task deve pertencer à story fornecida
            if task_story and task_story != story:
                raise ValueError(
                    f"❌ Task {task} pertence à história {task_story}, não {story}.\n"
                    f"   Use: make dev-pipeline-resume TASK={task}"
                )
        
        return (story, task, "task")
    
    return (None, None, "unknown")


def find_story_for_task(task_key: str, persistence: PipelineState) -> str | None:
    """
    Busca qual história contém a task.
    
    Busca em:
    1. *-task.json (task pipeline) → lê story_key
    2. *-story.json (story pipeline v2.0) → busca em tasks[]
    3. *-pipeline.json (monolítico v1.0) → busca em tasks[]
    
    Args:
        task_key: HUB-645
        persistence: PipelineState instance
    
    Returns:
        story_key ou None se não encontrar
    """
    # 1. Buscar task pipeline
    task_file = persistence.state_dir / f"{task_key}-task.json"
    if task_file.exists():
        try:
            data = json.loads(task_file.read_text())
            return data.get("story_key")
        except (json.JSONDecodeError, KeyError):
            pass
    
    # 2. Buscar em story pipelines v2.0
    for story_file in persistence.state_dir.glob("*-story.json"):
        try:
            data = json.loads(story_file.read_text())
            for task in data.get("tasks", []):
                if task.get("jira_key") == task_key:
                    return data.get("story_key")
        except (json.JSONDecodeError, KeyError):
            continue
    
    # 3. Buscar em pipelines v1.0 (monolítico)
    for pipeline_file in persistence.state_dir.glob("*-pipeline.json"):
        try:
            data = json.loads(pipeline_file.read_text())
            for task in data.get("tasks", []):
                if task.get("jira_key") == task_key:
                    return data.get("story_key")
        except (json.JSONDecodeError, KeyError):
            continue
    
    # Não encontrado (task avulsa ou não existe)
    return None

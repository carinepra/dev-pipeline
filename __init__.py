"""Dev Pipeline - Orchestrator v2.1 (Config Centralizado)."""

__version__ = "2.1.0"

from pipelines.story_pipeline import StoryPipeline
from pipelines.task_pipeline import TaskPipeline
from utils.pipeline_resolver import (
    find_story_for_task,
    resolve_pipeline_key,
)

# Gerar/atualizar config centralizado para skills
try:
    from utils.config import generate_pipeline_config
    generate_pipeline_config()
except Exception:
    # Não quebrar se houver erro de import circular ou permissões
    pass

__all__ = [
    "StoryPipeline",
    "TaskPipeline",
    "resolve_pipeline_key",
    "find_story_for_task",
]

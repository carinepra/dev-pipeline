"""Constantes e enums para o Dev Pipeline Orchestrator (v2.0)."""

from enum import Enum


class PipelineStateEnum(str, Enum):
    """
    Estados do pipeline (evita magic strings).

    Story: story_analysis -> task_breakdown -> coordinating -> documentation -> completed
    Task:  pending -> task_discussion -> task_planning -> implementation ->
           review_changes -> git_publish -> aguardando_merge -> completed
    """

    IDLE = "IDLE"
    STORY_ANALYSIS = "STORY_ANALYSIS"
    TASK_BREAKDOWN = "TASK_BREAKDOWN"
    TASK_PLANNING = "TASK_PLANNING"
    IMPLEMENTATION = "IMPLEMENTATION"
    REVIEW_CHANGES = "REVIEW_CHANGES"
    GIT_PUBLISH = "GIT_PUBLISH"
    AGUARDANDO_MERGE = "AGUARDANDO_MERGE"
    DOCUMENTATION = "DOCUMENTATION"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


class RepoScope(str, Enum):
    """Escopo de repos afetados pela história."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    BOTH = "both"
    DOCS = "docs"
    INFRA = "infra"


# Paths (v2.1: Estrutura pipelines/{stories,tasks})
DEFAULT_STATE_DIR = ".pipeline-state"
DEFAULT_LOG_DIR = "logs"
DEFAULT_STORIES_DIR = "pipelines/stories"
DEFAULT_TASKS_DIR = "pipelines/tasks"

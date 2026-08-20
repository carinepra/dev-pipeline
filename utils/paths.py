"""Path helpers para estrutura de diretórios do pipeline v2.1+."""

from pathlib import Path

from core.constants import DEFAULT_STATE_DIR


def _stories_dir() -> str:
    try:
        from utils.config import get_stories_dir
        return get_stories_dir()
    except Exception:
        from core.constants import DEFAULT_STORIES_DIR
        return DEFAULT_STORIES_DIR


def _tasks_dir() -> str:
    try:
        from utils.config import get_tasks_dir
        return get_tasks_dir()
    except Exception:
        from core.constants import DEFAULT_TASKS_DIR
        return DEFAULT_TASKS_DIR


def get_story_dir(story_key: str) -> Path:
    """
    Retorna diretório da story.
    
    Args:
        story_key: Ex: PROJ-542, INVEST-100
    
    Returns:
        pipelines/stories/PROJ-542
    """
    return Path(_stories_dir()) / story_key


def get_task_dir(task_key: str, story_key: str | None = None) -> Path:
    """
    Retorna diretório da task (independente de ter story pai ou não).
    
    Args:
        task_key: Ex: PROJ-645 ou _new-xxx
        story_key: Ignorado (mantido para compatibilidade)
    
    Returns:
        pipelines/tasks/PROJ-645
        pipelines/tasks/_new-xxx
    """
    return Path(_tasks_dir()) / task_key


def get_story_plan_path(story_key: str) -> Path:
    """
    Path do story plan.
    
    Returns:
        pipelines/stories/PROJ-542/.story-plan.md
    """
    return get_story_dir(story_key) / ".story-plan.md"


def get_story_tasks_proposed_path(story_key: str) -> Path:
    """
    Path do tasks proposed.
    
    Returns:
        pipelines/stories/PROJ-542/.tasks-proposed.json
    """
    return get_story_dir(story_key) / ".tasks-proposed.json"


def get_task_plan_path(task_key: str) -> Path:
    """
    Path do task plan.
    
    Returns:
        pipelines/tasks/PROJ-645/.plan.md
    """
    return get_task_dir(task_key) / ".plan.md"


def get_task_context_path(task_key: str) -> Path:
    """
    Path do context file para TASK=NEW.
    
    Returns:
        pipelines/tasks/_new-xxx/.new-task-context.json
    """
    return get_task_dir(task_key) / ".new-task-context.json"


def get_task_review_report_path(task_key: str) -> Path:
    """
    Path do review report.
    
    Returns:
        pipelines/tasks/PROJ-645/.review-report.md
    """
    return get_task_dir(task_key) / ".review-report.md"


def get_task_pr_response_path(task_key: str) -> Path:
    """
    Path do PR response plan.
    
    Returns:
        pipelines/tasks/PROJ-645/.pr-response-plan.md
    """
    return get_task_dir(task_key) / ".pr-response-plan.md"


def get_task_review_data_path(task_key: str) -> Path:
    """
    Path do review data (input para review skills).
    
    Returns:
        pipelines/tasks/PROJ-645/.review-data.json
    """
    return get_task_dir(task_key) / ".review-data.json"


def get_task_discussion_context_path(task_key: str) -> Path:
    """
    Path do discussion context (usado durante task_discussion state).
    
    Returns:
        pipelines/tasks/_new-xxx/.discussion-context.json
    """
    return get_task_dir(task_key) / ".discussion-context.json"


def get_task_state_path(task_key: str) -> Path:
    """
    Path do arquivo de estado da task (pipeline state).
    
    Returns:
        .pipeline-state/PROJ-645-task.json
    """
    return Path(DEFAULT_STATE_DIR) / f"{task_key}-task.json"


def get_story_state_path(story_key: str) -> Path:
    """
    Path do arquivo de estado da story (pipeline state).
    
    Returns:
        .pipeline-state/PROJ-542-story.json
    """
    return Path(DEFAULT_STATE_DIR) / f"{story_key}-story.json"

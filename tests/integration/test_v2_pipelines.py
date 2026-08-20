"""
Testes de integração para v2.0: Pipelines Independentes.

Testa:
- Criação de Story e Task Pipelines
- Migração v1.0 → v2.0
- Rollback
- Paralelismo (múltiplas tasks)
"""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from pipelines import StoryPipeline, TaskPipeline
from core.persistence import PipelineState


@pytest.fixture
def temp_dirs():
    """Cria diretórios temporários para testes."""
    state_dir = Path(tempfile.mkdtemp())
    log_dir = Path(tempfile.mkdtemp())
    
    yield state_dir, log_dir
    
    # Cleanup
    shutil.rmtree(state_dir, ignore_errors=True)
    shutil.rmtree(log_dir, ignore_errors=True)


def test_story_pipeline_init(temp_dirs):
    """Testa criação de Story Pipeline v2.0."""
    state_dir, log_dir = temp_dirs
    
    # Criar story pipeline
    pipeline = StoryPipeline("PROJ-999", state_dir, log_dir)
    pipeline.init_new_story()
    
    # Verificar arquivo criado
    story_file = state_dir / "PROJ-999-story.json"
    assert story_file.exists()
    
    # Verificar schema
    data = json.loads(story_file.read_text())
    assert data["version"] == "2.0"
    assert data["pipeline_type"] == "story"
    assert data["story_key"] == "PROJ-999"
    assert data["current_state"] == "story_analysis"


def test_task_pipeline_init(temp_dirs):
    """Testa criação de Task Pipeline v2.0."""
    state_dir, log_dir = temp_dirs

    pipeline = TaskPipeline("PROJ-998", "PROJ-999", state_dir, log_dir)
    with patch.object(pipeline, "start_planning"):
        pipeline.init_new_task("Test task", "Back")

    task_file = state_dir / "PROJ-998-task.json"
    assert task_file.exists()

    data = json.loads(task_file.read_text())
    assert data["version"] == "2.0"
    assert data["pipeline_type"] == "task"
    assert data["task_key"] == "PROJ-998"
    assert data["story_key"] == "PROJ-999"
    assert data["current_state"] == "pending"




def test_persistence_list_active(temp_dirs):
    """Testa listagem de pipelines ativos."""
    state_dir, log_dir = temp_dirs
    persistence = PipelineState(state_dir)
    
    # Criar múltiplos pipelines
    story1 = StoryPipeline("PROJ-991", state_dir, log_dir)
    story1.init_new_story()
    
    story2 = StoryPipeline("PROJ-990", state_dir, log_dir)
    story2.init_new_story()
    
    task1 = TaskPipeline("PROJ-989", "PROJ-991", state_dir, log_dir)
    with patch.object(task1, "start_planning"):
        task1.init_new_task("Test task 1", "Back")

    task2 = TaskPipeline("PROJ-988", "PROJ-991", state_dir, log_dir)
    with patch.object(task2, "start_planning"):
        task2.init_new_task("Test task 2", "Front")
    
    # Listar stories
    stories = persistence.list_active_stories()
    assert len(stories) == 2
    assert all(s["version"] == "2.0" for s in stories)
    
    # Listar tasks
    all_tasks = persistence.list_active_tasks()
    assert len(all_tasks) == 2
    
    # Listar tasks de uma story específica
    story_tasks = persistence.list_active_tasks(story_key="PROJ-991")
    assert len(story_tasks) == 2
    assert all(t["story_key"] == "PROJ-991" for t in story_tasks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

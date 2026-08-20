"""Persistência de estado do pipeline (JSON + lock + backup + migration)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError, field_validator

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

import re

from core.constants import PipelineStateEnum

_ISSUE_KEY_PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9]*-")


# ===== BACKWARD COMPATIBILITY: Path normalization =====


def normalize_legacy_path(path: str | Path | None) -> str | None:
    """
    Converte paths antigos para novos (v2.1).
    
    Exemplos:
        pipelines/stories/PROJ-542/.story-plan.md
        -> pipelines/stories/PROJ-542/.story-plan.md
        
        data/stories/PROJ-542/PROJ-645.plan.md
        -> pipelines/tasks/PROJ-645/.plan.md
        
        data/stories/_standalone/_new-xxx.plan.md
        -> pipelines/tasks/_new-xxx/.plan.md
    
    Args:
        path: Path antigo ou novo
    
    Returns:
        Path normalizado ou None
    """
    if not path:
        return None
    
    path_str = str(path)
    
    # Ignorar se já está no formato novo (v2.1)
    if "pipelines/" in path_str:
        return path_str
    
    # Padrões a converter
    if "data/stories" in path_str or "pipelines/stories" in path_str:
        # Extrair componentes
        parts = Path(path_str).parts
        
        # Encontrar índice de 'stories'
        try:
            stories_idx = parts.index('stories')
        except ValueError:
            return path_str
        
        # Pegar o que vem depois de 'stories/'
        after_stories = parts[stories_idx + 1:]
        
        if not after_stories:
            return path_str
        
        first_part = after_stories[0]
        
        # Story plan ou tasks proposed
        if _ISSUE_KEY_PREFIX_RE.match(first_part) and len(after_stories) > 1:
            filename = after_stories[-1]
            if filename in [".story-plan.md", ".tasks-proposed.json"]:
                # É arquivo de story
                story_key = first_part
                return f"pipelines/stories/{story_key}/{filename}"
            else:
                # É arquivo de task (PROJ-645.plan.md ou similar)
                if "." in filename:
                    # Pode ser PROJ-645.plan.md ou .plan.md
                    if _ISSUE_KEY_PREFIX_RE.match(filename) or filename.startswith("_new-"):
                        # Formato antigo: PROJ-645.plan.md
                        task_key = filename.split(".")[0]
                        ext = ".".join(filename.split(".")[1:])
                        return f"pipelines/tasks/{task_key}/.{ext}"
                    else:
                        # Formato novo já: .plan.md (pegar task_key de after_stories)
                        if len(after_stories) >= 2:
                            task_key = after_stories[-2]
                            return f"pipelines/tasks/{task_key}/{filename}"
        
        # Standalone task
        elif first_part == "_standalone" and len(after_stories) > 1:
            filename = after_stories[-1]
            if "." in filename:
                # _new-xxx.plan.md ou _new-xxx.new-task-context.json
                if filename.startswith("_new-"):
                    task_key = filename.split(".")[0]
                    ext = ".".join(filename.split(".")[1:])
                    return f"pipelines/tasks/{task_key}/.{ext}"
                else:
                    # Já está no formato .xxx.md
                    if len(after_stories) >= 2:
                        task_key = after_stories[-2]
                        return f"pipelines/tasks/{task_key}/{filename}"
        
        # Task key direto como primeiro nível (ex: _new-xxx/.plan.md já no formato novo)
        elif (_ISSUE_KEY_PREFIX_RE.match(first_part) or first_part.startswith("_new-")) and len(after_stories) > 1:
            task_key = first_part
            filename = after_stories[-1]
            return f"pipelines/tasks/{task_key}/{filename}"
    
    return path_str


def normalize_state_paths(state_data: dict) -> dict:
    """
    Normaliza todos os paths em um state dict.
    
    Aplica normalize_legacy_path() em todos os campos que contêm paths.
    """
    if "plan_path" in state_data:
        state_data["plan_path"] = normalize_legacy_path(state_data["plan_path"])
    
    # Normalizar em nested contexts
    if "collected_context" in state_data:
        ctx = state_data["collected_context"]
        for key in ["context_file", "plan_path"]:
            if key in ctx:
                ctx[key] = normalize_legacy_path(ctx[key])
    
    # Normalizar em task_data (se houver paths)
    if "task_data" in state_data:
        td = state_data["task_data"]
        for key in ["plan_file", "review_file"]:
            if key in td:
                td[key] = normalize_legacy_path(td[key])
    
    return state_data


class PipelineStateSchema(BaseModel):
    """Schema Pydantic para validar estado JSON v1.0 (monolítico - deprecated)."""

    version: str = "1.0"
    story_key: str
    current_state: str
    created_at: str
    updated_at: str
    user: str = Field(default_factory=lambda: os.getenv("USER", "unknown"))
    lock: dict[str, Any] = Field(default_factory=dict)
    story_data: dict[str, Any]
    tasks: list[dict[str, Any]]
    current_task_index: int
    prs: list[dict[str, Any]] = Field(default_factory=list)
    validations: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class StoryPipelineSchema(BaseModel):
    """Schema v2.0 para Story Pipeline (coordenadora)."""

    version: str = "2.0"
    pipeline_type: str = "story"
    story_key: str
    project_key: str | None = None
    current_state: str
    created_at: str
    updated_at: str
    user: str = Field(default_factory=lambda: os.getenv("USER", "unknown"))
    lock: dict[str, Any] = Field(default_factory=dict)
    story_data: dict[str, Any]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    validations: list[dict[str, Any]] = Field(default_factory=list)
    plan_path: str | None = None
    plan_generated: bool = False
    errors: list[dict[str, Any]] = Field(default_factory=list)


class TaskPipelineSchema(BaseModel):
    """Schema v2.0 para Task Pipeline (independente)."""

    version: str = "2.0"
    pipeline_type: str = "task"
    task_key: str
    story_key: str | None
    project_key: str | None = None
    target_repos: list[str] = Field(default_factory=list)
    current_state: str

    @field_validator("target_repos", mode="before")
    @classmethod
    def _coerce_target_repos(cls, v: Any) -> list[str]:
        return v if isinstance(v, list) else []
    paused_from_state: str | None = None
    created_at: str
    updated_at: str
    last_activity_at: str
    user: str = Field(default_factory=lambda: os.getenv("USER", "unknown"))
    lock: dict[str, Any] = Field(default_factory=dict)
    task_data: dict[str, Any]
    plan_path: str | None = None
    plan_generated: bool = False
    pr_url: str | None = None
    pr_status_cached: str | None = None
    pr_last_checked: str | None = None
    # Campos para TASK=NEW
    is_new_task: bool = False
    temp_key: bool = False
    old_temp_key: str | None = None
    collected_context: dict[str, Any] = Field(default_factory=dict)
    validations: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class PipelineState:
    """Gerencia save/load de estado do pipeline com lock e backup."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True, parents=True)

    def save(self, story_key: str, data: dict[str, Any]) -> None:
        """
        Salva estado com backup automático e lock.

        Args:
            story_key: Issue key (ex: PROJ-1234)
            data: Dados do estado

        Raises:
            ValueError: Se schema inválido
        """
        file_path = self.state_dir / f"{story_key}-pipeline.json"
        lock_path = self.state_dir / f"{story_key}.lock"

        # Backup se já existe
        if file_path.exists():
            backup = self.state_dir / f"{story_key}-pipeline.backup.json"
            shutil.copy(file_path, backup)

        # Validar schema
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            PipelineStateSchema(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid pipeline state schema: {e}")

        # Salvar com lock
        with FileLock(lock_path, timeout=10):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self, story_key: str) -> dict[str, Any] | None:
        """
        Carrega estado com validação de schema.

        Args:
            story_key: Issue key

        Returns:
            Dados do estado ou None se não existir
        """
        file_path = self.state_dir / f"{story_key}-pipeline.json"
        if not file_path.exists():
            return None

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Normalizar paths antigos para v2.0 (backward compatibility)
        data = normalize_state_paths(data)

        # Validar schema (migrar se versão antiga)
        try:
            PipelineStateSchema(**data)
            return data
        except ValidationError:
            # Tentar migrar de versão antiga
            return self._migrate_schema(data)

    def _migrate_schema(self, old_data: dict[str, Any]) -> dict[str, Any]:
        """
        Migra estado de versões antigas para schema atual.

        Args:
            old_data: Estado na versão antiga

        Returns:
            Estado migrado
        """
        version = old_data.get("version", "0.0")
        if version == "0.0":  # estado sem version (pre-migration)
            old_data["version"] = "1.0"
            old_data.setdefault("user", os.getenv("USER", "unknown"))
            old_data.setdefault("lock", {})
            old_data.setdefault("prs", [])
            old_data.setdefault("errors", [])
        return old_data

    def list_active(self) -> list[dict[str, Any]]:
        """
        Lista pipelines ativos (não COMPLETED nem CANCELLED).

        Returns:
            Lista de estados de pipelines ativos
        """
        pipelines = []
        for file in self.state_dir.glob("*-pipeline.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Comparação case-insensitive
                    state = data.get("current_state", "").lower()
                    if state not in ("completed", "cancelled"):
                        pipelines.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return pipelines

    def acquire_lock(self, story_key: str) -> bool:
        """
        Tenta adquirir lock (prevenir concorrência).

        Também valida se PID antigo ainda está vivo; se não, força unlock.

        Args:
            story_key: Issue key

        Returns:
            True se conseguiu adquirir lock
        """
        lock_path = self.state_dir / f"{story_key}.lock"
        state_file = self.state_dir / f"{story_key}-pipeline.json"

        # Se lock existe, verificar se PID ainda está vivo
        if PSUTIL_AVAILABLE and lock_path.exists() and state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    data = json.load(f)
                    old_pid = data.get("lock", {}).get("pid")
                    if old_pid and not psutil.pid_exists(old_pid):
                        # PID morreu, pode remover lock stale
                        lock_path.unlink()
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                pass

        try:
            lock = FileLock(lock_path, timeout=0)
            lock.acquire()
            return True
        except Exception:
            return False

    def force_unlock(self, story_key: str) -> None:
        """
        Força unlock (use com cuidado!).

        Args:
            story_key: Issue key
        """
        lock_path = self.state_dir / f"{story_key}.lock"
        if lock_path.exists():
            lock_path.unlink()
    
    # ===== v2.0: STORY PIPELINES =====
    
    def save_story(self, story_key: str, data: dict[str, Any]) -> None:
        """
        Salva Story Pipeline (v2.0) com backup e lock.
        
        Args:
            story_key: PROJ-XXX
            data: Dados do estado da história
        """
        file_path = self.state_dir / f"{story_key}-story.json"
        lock_path = self.state_dir / f"{story_key}-story.lock"
        
        # Backup se já existe
        if file_path.exists():
            backup = self.state_dir / f"{story_key}-story.backup.json"
            shutil.copy(file_path, backup)
        
        # Validar schema v2.0
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            StoryPipelineSchema(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid story pipeline schema: {e}")
        
        # Salvar com lock
        with FileLock(lock_path, timeout=10):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_story(self, story_key: str) -> dict[str, Any] | None:
        """
        Carrega Story Pipeline (v2.0) com validação.
        
        Args:
            story_key: PROJ-XXX
        
        Returns:
            Dados do estado ou None se não existir
        """
        file_path = self.state_dir / f"{story_key}-story.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        
        # Normalizar paths antigos para v2.0 (backward compatibility)
        data = normalize_state_paths(data)
        
        try:
            StoryPipelineSchema(**data)
            return data
        except ValidationError as e:
            raise ValueError(f"Invalid story schema: {e}")
    
    def list_active_stories(self) -> list[dict[str, Any]]:
        """
        Lista Story Pipelines ativos (v2.0).
        
        Returns:
            Lista de estados de histórias ativas
        """
        stories = []
        for file in self.state_dir.glob("*-story.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Validar schema v2.0
                    if data.get("version") != "2.0":
                        continue
                    
                    # Filtrar finalizadas (comparação case-insensitive)
                    state = data.get("current_state", "").lower()
                    if state not in ("completed", "cancelled"):
                        stories.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return stories
    
    # ===== v2.0: TASK PIPELINES =====
    
    def save_task(self, task_key: str, data: dict[str, Any]) -> None:
        """
        Salva Task Pipeline (v2.0) com backup e lock.
        
        Args:
            task_key: PROJ-XXX
            data: Dados do estado da task
        """
        file_path = self.state_dir / f"{task_key}-task.json"
        lock_path = self.state_dir / f"{task_key}-task.lock"
        
        # Backup se já existe
        if file_path.exists():
            backup = self.state_dir / f"{task_key}-task.backup.json"
            shutil.copy(file_path, backup)
        
        # Validar schema v2.0
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        data["last_activity_at"] = datetime.now(timezone.utc).isoformat()
        try:
            TaskPipelineSchema(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid task pipeline schema: {e}")
        
        # Salvar com lock
        with FileLock(lock_path, timeout=10):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_task(self, task_key: str) -> dict[str, Any] | None:
        """
        Carrega Task Pipeline (v2.0) com validação.
        
        Args:
            task_key: PROJ-XXX
        
        Returns:
            Dados do estado ou None se não existir
        """
        file_path = self.state_dir / f"{task_key}-task.json"
        if not file_path.exists():
            return None
        
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        
        # Normalizar paths antigos para v2.0 (backward compatibility)
        data = normalize_state_paths(data)
        
        try:
            TaskPipelineSchema(**data)
            return data
        except ValidationError as e:
            raise ValueError(f"Invalid task schema: {e}")
    
    def list_active_tasks(self, story_key: str | None = None) -> list[dict[str, Any]]:
        """
        Lista Task Pipelines ativos (v2.0), opcionalmente filtrados por história.
        
        MELHORIA #6: Filtro correto por story_key (não prefixo).
        
        Args:
            story_key: Filtrar tasks de uma história específica (ex: PROJ-542)
        
        Returns:
            Lista de estados de tasks ativas
        """
        tasks = []
        
        for file in self.state_dir.glob("*-task.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Validar schema v2.0
                    if data.get("version") != "2.0":
                        continue
                    
                    # Filtrar por story (comparação exata)
                    if story_key is not None:
                        if data.get("story_key") != story_key:
                            continue  # Task de outra história ou avulsa
                    
                    # Excluir finalizadas (comparação case-insensitive)
                    state = data.get("current_state", "").lower()
                    if state not in ("completed", "cancelled"):
                        tasks.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        
        return tasks
    
    # ===== CACHE DE FINALIZAÇÃO (v1.6.0) =====
    
    def save_finalization_data(self, story_key: str, data: dict[str, Any]) -> None:
        """
        Salva dados de finalização em cache (TTL 1h).
        
        Args:
            story_key: PROJ-XXX
            data: {
                "all_files_changed": [...],
                "critical_diffs": {...},
                "db_changes": [...],
                "pr_descriptions": [...],
                "categorized": {...},
                "collected_at": "2026-03-26T15:30:00",
            }
        """
        cache_file = self.state_dir / f"{story_key}-finalization-cache.json"
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def load_finalization_data(self, story_key: str) -> dict[str, Any] | None:
        """
        Carrega dados de finalização do cache.
        
        Returns:
            Dict com dados ou None se não existir/inválido/expirado
        """
        cache_file = self.state_dir / f"{story_key}-finalization-cache.json"
        
        if not cache_file.exists():
            return None
        
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            
            # Verificar expiração (1 hora)
            collected_at = datetime.fromisoformat(data["collected_at"])
            age_minutes = (datetime.now(timezone.utc) - collected_at).total_seconds() / 60
            
            if age_minutes > 60:
                return None  # Cache expirado
            
            return data
        
        except Exception:
            # Cache corrompido ou formato inválido
            return None

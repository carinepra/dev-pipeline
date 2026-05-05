"""Base class for pipeline state machines."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from statemachine import State, StateMachine

from core.constants import DEFAULT_LOG_DIR, DEFAULT_STATE_DIR
from core.persistence import PipelineState


class BasePipeline(StateMachine):
    """Shared infrastructure for Story and Task pipelines."""

    _persist_key: str  # set by subclass
    _persist_type: str  # "story" or "task"

    def __init__(
        self,
        state_dir: Path | str = DEFAULT_STATE_DIR,
        log_dir: Path | str = DEFAULT_LOG_DIR,
        dry_run: bool = False,
    ):
        self.state_dir = Path(state_dir)
        self.log_dir = Path(log_dir)
        self.dry_run = dry_run
        self.persistence = PipelineState(state_dir=self.state_dir)
        self.console = Console()
        self.state_data: dict[str, Any] = {}
        super().__init__()

    # ── persistence helpers ───────────────────────────────────────

    def _save_state(self) -> None:
        """Persiste estado atual no disco."""
        current = self._get_current_state_id()
        if current:
            self.state_data["current_state"] = current
        saver = getattr(self.persistence, f"save_{self._persist_type}")
        saver(self._persist_key, self.state_data)

    def _set_state(self, target_state: State) -> None:
        """Força estado (recovery mode)."""
        self.current_state = target_state

    def _get_current_state_id(self) -> str:
        """Retorna ID do estado atual (compatível com statemachine v2 e v3)."""
        try:
            cfg = self.configuration
            if cfg:
                return next(iter(cfg)).id
        except (AttributeError, StopIteration):
            pass
        return self.current_state.id

    def _extract_project_key(self) -> str | None:
        """Extrai project key da key principal."""
        try:
            from utils.config import extract_project_key
            return extract_project_key(self._persist_key)
        except (ValueError, ImportError):
            return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _current_user() -> str:
        return os.getenv("USER", "unknown")

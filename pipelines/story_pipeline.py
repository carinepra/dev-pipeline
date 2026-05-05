"""Story Pipeline — coordena o ciclo de vida de uma história Jira."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from statemachine import State

from core.constants import DEFAULT_STATE_DIR, DEFAULT_LOG_DIR
from pipelines.base import BasePipeline


class StoryPipeline(BasePipeline):
    """
    State machine para Story Pipeline (v2.0).

    Estados:
        story_analysis -> task_breakdown -> coordinating -> documentation -> completed

    Qualquer estado pode pausar -> paused (e retomar).
    """

    _persist_type = "story"

    # --- States ---
    story_analysis = State(initial=True)
    task_breakdown = State()
    coordinating = State()
    documentation = State()
    completed = State(final=True)
    paused = State()
    cancelled = State(final=True)

    # --- Transitions ---
    start = story_analysis.to(task_breakdown)
    breakdown_done = task_breakdown.to(coordinating)
    all_tasks_done = coordinating.to(documentation)
    docs_done = documentation.to(completed)

    pause = (
        story_analysis.to(paused)
        | task_breakdown.to(paused)
        | coordinating.to(paused)
        | documentation.to(paused)
    )

    cancel = (
        story_analysis.to(cancelled)
        | task_breakdown.to(cancelled)
        | coordinating.to(cancelled)
        | documentation.to(cancelled)
        | paused.to(cancelled)
    )

    resume_to_analysis = paused.to(story_analysis)
    resume_to_breakdown = paused.to(task_breakdown)
    resume_to_coordinating = paused.to(coordinating)
    resume_to_documentation = paused.to(documentation)

    def __init__(
        self,
        story_key: str,
        state_dir: Path | str = DEFAULT_STATE_DIR,
        log_dir: Path | str = DEFAULT_LOG_DIR,
        dry_run: bool = False,
    ):
        self.story_key = story_key
        self._persist_key = story_key
        super().__init__(state_dir=state_dir, log_dir=log_dir, dry_run=dry_run)

    # --- Public API ---

    def init_new_story(self) -> None:
        """Inicializa nova story pipeline e persiste estado."""
        now = self._now_iso()
        self.state_data = {
            "version": "2.0",
            "pipeline_type": "story",
            "story_key": self.story_key,
            "project_key": self._extract_project_key(),
            "current_state": "story_analysis",
            "created_at": now,
            "updated_at": now,
            "user": self._current_user(),
            "lock": {},
            "story_data": {"summary": "", "description": ""},
            "tasks": [],
            "validations": [],
            "plan_path": None,
            "plan_generated": False,
            "errors": [],
        }
        self._save_state()

    def start_story(self) -> None:
        """Alias para init_new_story + on_enter_story_analysis."""
        self.init_new_story()
        self.on_enter_story_analysis()

    def load_existing_story(self) -> bool:
        """Carrega estado existente do disco."""
        data = self.persistence.load_story(self.story_key)
        if data:
            self.state_data = data
            return True
        return False

    # --- State handlers ---

    def on_enter_story_analysis(self) -> None:
        """Handler: análise da história (executa pipeline-story-analyzer)."""
        if not self.state_data:
            return

        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "story_analysis"
        self._save_state()

        runner = SkillsRunner(self.console)
        plan_path = runner.run_story_planner(
            self.story_key, self.state_data.get("story_data", {})
        )
        self.state_data["plan_path"] = str(plan_path)
        self.state_data["plan_generated"] = True
        self._save_state()

    def on_enter_task_breakdown(self) -> None:
        """Handler: quebra em tasks (executa pipeline-task-breaker)."""
        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "task_breakdown"
        self._save_state()

        runner = SkillsRunner(self.console)
        tasks_data = runner.run_jira_task_creator(self.story_key)

        self.state_data["tasks"] = tasks_data.get("tasks", [])
        self._save_state()

    def on_enter_coordinating(self) -> None:
        """Handler: coordena execução das tasks."""
        self.state_data["current_state"] = "coordinating"
        self._save_state()
        self.console.print(
            f"[cyan]Story {self.story_key} em modo coordenação — "
            f"aguardando tasks finalizarem.[/cyan]"
        )

    def on_enter_documentation(self) -> None:
        """Handler: gera documentação técnica consolidada."""
        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "documentation"
        self._save_state()

        runner = SkillsRunner(self.console)

        finalization = self.persistence.load_finalization_data(self.story_key)
        if finalization:
            doc_path = runner.run_create_docs(
                story_key=self.story_key,
                files_changed=finalization.get("all_files_changed", []),
                critical_diffs=finalization.get("critical_diffs", {}),
                db_changes=finalization.get("db_changes", []),
                pr_descriptions=finalization.get("pr_descriptions", []),
                story_data=self.state_data.get("story_data", {}),
                tasks=self.state_data.get("tasks", []),
            )
            self.console.print(f"[green]✅ Documentação gerada: {doc_path}[/green]")
        else:
            self.console.print(
                "[yellow]⚠️ Sem dados de finalização em cache. "
                "Execute 'make dev-pipeline-finalize' para coletar dados.[/yellow]"
            )

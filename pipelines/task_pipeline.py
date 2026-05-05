"""Task Pipeline — ciclo de vida de uma task individual."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from statemachine import State

from core.constants import DEFAULT_STATE_DIR, DEFAULT_LOG_DIR
from pipelines.base import BasePipeline


class TaskPipeline(BasePipeline):
    """
    State machine para Task Pipeline (v2.0).

    Estados:
        pending -> task_discussion -> task_planning -> implementation ->
        review_changes -> git_publish -> aguardando_merge -> completed

    Qualquer estado pode pausar -> paused (e retomar).
    """

    _persist_type = "task"

    # --- States ---
    pending = State(initial=True)
    task_discussion = State()
    task_planning = State()
    implementation = State()
    review_changes = State()
    git_publish = State()
    aguardando_merge = State()
    completed = State(final=True)
    paused = State()
    cancelled = State(final=True)

    # --- Transitions ---
    start_discussion = pending.to(task_discussion)
    start_planning = pending.to(task_planning)
    discussion_done = task_discussion.to(task_planning)
    plan_approved = task_planning.to(implementation)
    implementation_done = implementation.to(review_changes)
    review_approved = review_changes.to(git_publish)
    review_needs_fixes = review_changes.to(implementation)
    pr_created = git_publish.to(aguardando_merge)
    pr_merged = aguardando_merge.to(completed)
    pr_needs_fixes = aguardando_merge.to(implementation)

    pause = (
        pending.to(paused)
        | task_discussion.to(paused)
        | task_planning.to(paused)
        | implementation.to(paused)
        | review_changes.to(paused)
        | git_publish.to(paused)
        | aguardando_merge.to(paused)
    )

    cancel = (
        pending.to(cancelled)
        | task_discussion.to(cancelled)
        | task_planning.to(cancelled)
        | implementation.to(cancelled)
        | review_changes.to(cancelled)
        | git_publish.to(cancelled)
        | aguardando_merge.to(cancelled)
        | paused.to(cancelled)
    )

    resume_to_pending = paused.to(pending)
    resume_to_discussion = paused.to(task_discussion)
    resume_to_planning = paused.to(task_planning)
    resume_to_implementation = paused.to(implementation)
    resume_to_review = paused.to(review_changes)
    resume_to_publish = paused.to(git_publish)
    resume_to_merge = paused.to(aguardando_merge)

    def __init__(
        self,
        task_key: str,
        story_key: str | None = None,
        state_dir: Path | str = DEFAULT_STATE_DIR,
        log_dir: Path | str = DEFAULT_LOG_DIR,
        dry_run: bool = False,
    ):
        self.task_key = task_key
        self.story_key = story_key
        self._persist_key = task_key
        super().__init__(state_dir=state_dir, log_dir=log_dir, dry_run=dry_run)

    def _extract_project_key(self) -> str | None:
        """Extrai project key da task ou story key."""
        key = self.story_key or self.task_key
        try:
            from utils.config import extract_project_key
            return extract_project_key(key)
        except (ValueError, ImportError):
            return None

    # --- Public API ---

    def init_new_task(
        self,
        task_summary: str,
        component: str,
        is_new_task: bool = False,
        collected_context: dict[str, Any] | None = None,
        project_key: str | None = None,
        target_repos: list[str] | None = None,
    ) -> None:
        """
        Inicializa task pipeline e persiste estado.

        Args:
            task_summary: Resumo da task
            component: "Front" ou "Back"
            is_new_task: True se TASK=NEW (ainda sem Jira key)
            collected_context: Contexto coletado (TASK=NEW)
            project_key: Projeto Jira
            target_repos: Lista de repo IDs alvo
        """
        now = self._now_iso()
        self.state_data = {
            "version": "2.0",
            "pipeline_type": "task",
            "task_key": self.task_key,
            "story_key": self.story_key,
            "project_key": project_key or self._extract_project_key(),
            "target_repos": target_repos or [],
            "current_state": "task_discussion" if is_new_task else "pending",
            "paused_from_state": None,
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now,
            "user": self._current_user(),
            "lock": {},
            "task_data": {
                "summary": task_summary,
                "component": component,
                "description": "",
            },
            "plan_path": None,
            "plan_generated": False,
            "pr_url": None,
            "pr_status_cached": None,
            "pr_last_checked": None,
            "is_new_task": is_new_task,
            "temp_key": self.task_key.startswith("_new-"),
            "old_temp_key": None,
            "collected_context": collected_context or {},
            "validations": [],
            "errors": [],
        }

        if is_new_task:
            self.current_state = self.task_discussion

        self._save_state()

        if not is_new_task:
            self.start_planning()

    def load_existing_task(self) -> bool:
        """Carrega estado existente do disco."""
        data = self.persistence.load_task(self.task_key)
        if data:
            self.state_data = data
            return True
        return False

    # --- State handlers ---

    def on_enter_task_discussion(self) -> None:
        """Handler: discussão técnica (TASK=NEW — refinar com pipeline-task-definer)."""
        self.state_data["current_state"] = "task_discussion"
        self._save_state()

        context = self.state_data.get("collected_context", {})
        title = context.get("title")

        if not title:
            self.console.print(
                f"[cyan]Task {self.task_key} em discussão — "
                f"aguardando refinamento via @pipeline-task-definer[/cyan]"
            )
            return

        self.console.print(f"[green]✅ Contexto refinado: {title}[/green]")
        self.console.print("[dim]Avançando para criação no Jira...[/dim]")

        if not self.dry_run:
            self._create_jira_issue_from_context(context)

    def on_enter_task_planning(self) -> None:
        """Handler: planejamento (executa pipeline-task-planner)."""
        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "task_planning"
        self._save_state()

        runner = SkillsRunner(self.console)
        plan_path = runner.run_task_planner_with_improvement(
            self.task_key, self.story_key or "_standalone"
        )
        self.state_data["plan_path"] = str(plan_path)
        self.state_data["plan_generated"] = True
        self._save_state()

    def on_enter_implementation(self) -> None:
        """Handler: implementação (dev codifica seguindo o plano)."""
        from rich.panel import Panel

        self.state_data["current_state"] = "implementation"
        self._save_state()

        plan_path = self.state_data.get("plan_path", "N/A")
        self.console.print(
            Panel(
                f"[bold cyan]Implementação — {self.task_key}[/bold cyan]\n\n"
                f"📋 Plano: {plan_path}\n\n"
                f"Implemente seguindo o plano e depois avance:\n"
                f"  [green]make dev-pipeline-next TASK={self.task_key}[/green]",
                title="🔨 Implementation",
                border_style="blue",
            )
        )

    def on_enter_review_changes(self) -> None:
        """Handler: review de código (linters + skill de review)."""
        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "review_changes"
        self._save_state()

        runner = SkillsRunner(self.console)
        component = self.state_data.get("task_data", {}).get("component", "Back")
        repo_type = "frontend" if component == "Front" else "backend"

        if repo_type == "frontend":
            runner.run_front_review_changes(self.task_key, self.story_key)
        else:
            runner.run_back_review_changes(self.task_key, self.story_key)

    def on_enter_git_publish(self) -> None:
        """Handler: commit, push e criar PR."""
        from utils.skills_runner import SkillsRunner

        self.state_data["current_state"] = "git_publish"
        self._save_state()

        runner = SkillsRunner(self.console)
        pr_url = runner.run_git_publish(self.task_key, self.story_key)

        self.state_data["pr_url"] = pr_url
        self._save_state()

    def on_enter_aguardando_merge(self) -> None:
        """Handler: aguardando merge do PR."""
        from rich.panel import Panel

        self.state_data["current_state"] = "aguardando_merge"
        self._save_state()

        pr_url = self.state_data.get("pr_url", "N/A")
        self.console.print(
            Panel(
                f"[bold cyan]Aguardando Merge — {self.task_key}[/bold cyan]\n\n"
                f"🔗 PR: {pr_url}\n\n"
                f"Quando o PR for mergeado, avance:\n"
                f"  [green]make dev-pipeline-next TASK={self.task_key}[/green]",
                title="⏳ Aguardando Merge",
                border_style="yellow",
            )
        )

    # --- Internal helpers ---

    def _create_jira_issue_from_context(self, context: dict[str, Any]) -> None:
        """Cria issue no Jira a partir do contexto refinado (TASK=NEW)."""
        from operations.jira_ops import create_issue

        self.console.print("[cyan]Criando issue no Jira...[/cyan]")
        try:
            issue_key = create_issue(
                project_key=context.get("project_key", "HUB"),
                summary=context.get("title", ""),
                description=context.get("description", ""),
                issue_type="Task",
                parent_key=self.story_key,
                component=context.get("component"),
                priority=context.get("priority", "Medium"),
                acceptance_criteria=context.get("acceptance_criteria"),
                dry_run=self.dry_run,
            )
            self.console.print(f"[green]✅ Issue criada: {issue_key}[/green]")

            if issue_key != self.task_key:
                old_key = self.task_key
                self.state_data["old_temp_key"] = old_key
                self.task_key = issue_key
                self._persist_key = issue_key
                self.state_data["task_key"] = issue_key
                self.state_data["temp_key"] = False
                self._save_state()

        except Exception as e:
            self.console.print(f"[red]❌ Erro ao criar issue: {e}[/red]")
            self.state_data["errors"].append({
                "stage": "task_discussion",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._save_state()

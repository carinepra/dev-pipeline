"""Prompts de validação (questionary + rich)."""

from __future__ import annotations

from typing import Any

from questionary import confirm, select, text
from rich.console import Console

from core.constants import RepoScope
from utils.ui import PipelineUI


class PipelineValidators:
    """Validações interativas com usuário."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.ui = PipelineUI(self.console)

    def ask_repo_scope(self) -> RepoScope:
        """
        Pergunta quais repos são afetados (legacy, mantido para backward compat).

        Returns:
            RepoScope
        """
        choice = select(
            "Quais repos são afetados por esta história?",
            choices=[
                {"name": "🐍 Backend (API Python/FastAPI)", "value": "backend"},
                {"name": "⚛️  Frontend (Backoffice Next.js)", "value": "frontend"},
                {"name": "🔄 Ambos (Backend + Frontend)", "value": "both"},
                {"name": "📚 Docs only", "value": "docs"},
            ],
        ).ask()

        return RepoScope(choice)

    def ask_target_repos(self, project_key: str | None = None) -> list[str]:
        """
        Pergunta quais repos serão impactados, lendo opções do config.

        Args:
            project_key: Projeto Jira (ex: "HUB"). Se None, mostra todos os repos.

        Returns:
            Lista de repo IDs selecionados.
        """
        from utils.config import (
            get_repos_for_project,
            get_all_repositories,
        )

        if project_key:
            try:
                repos = get_repos_for_project(project_key)
            except KeyError:
                repos = list(get_all_repositories().values())
        else:
            repos = list(get_all_repositories().values())

        if not repos:
            self.console.print("[yellow]Nenhum repositório configurado.[/yellow]")
            return []

        choices = []
        for r in repos:
            label = f"{r['id']} ({r.get('type', '?')} - {r.get('tech_stack', '?')})"
            choices.append({"name": label, "value": r["id"], "checked": True})

        from questionary import checkbox
        selected = checkbox(
            "Quais repositórios esta história/task impacta?",
            choices=choices,
        ).ask()

        return selected or []

    def ask_jira_project(self) -> str:
        """
        Pergunta qual projeto Jira usar (para TASK=NEW).

        Returns:
            Project key (ex: "HUB").
        """
        from utils.config import list_project_keys, get_project_config, get_default_project

        keys = list_project_keys()
        default = get_default_project()

        if not keys:
            return default

        if len(keys) == 1:
            return keys[0]

        choices = []
        for k in keys:
            try:
                proj = get_project_config(k)
                name = proj.get("name", k)
            except KeyError:
                name = k
            choices.append({"name": f"{k} — {name}", "value": k})

        selected = select(
            "Qual projeto Jira?",
            choices=choices,
            default=default,
        ).ask()

        return selected or default

    def confirm_task_breakdown(self, tasks: list[dict[str, Any]], after_chat_discussion: bool = False) -> tuple[bool, list[dict[str, Any]]]:
        """
        Mostra tabela de tasks e pede confirmação.

        Args:
            tasks: Lista de tasks propostas
            after_chat_discussion: Se True, assume que usuário já discutiu no chat

        Returns:
            (approved: bool, final_tasks: list)
        """
        self.ui.show_tasks_table(tasks)

        if after_chat_discussion:
            # Confirmação simples após discussão no chat
            choice = select(
                "Criar estas tasks no Jira?",
                choices=[
                    {"name": "✅ Yes — criar no Jira", "value": "yes"},
                    {"name": "❌ Cancel — abortar pipeline", "value": "cancel"},
                ],
            ).ask()

            if choice == "cancel":
                return False, []
            else:
                return True, tasks
        
        # Modo legado (sem discussão no chat)
        choice = select(
            "Aprovar tasks?",
            choices=[
                {"name": "✅ Yes — criar no Jira", "value": "yes"},
                {"name": "✏️  Edit — editar JSON manualmente", "value": "edit"},
                {"name": "❌ Cancel — abortar pipeline", "value": "cancel"},
            ],
        ).ask()

        if choice == "cancel":
            return False, []
        elif choice == "edit":
            # Permitir editar JSON manualmente
            self.console.print(
                "\n[cyan]Para editar tasks:[/cyan]\n"
                "1. Abra e edite o JSON gerado pelo skill\n"
                "2. Salve as alterações\n"
                "3. Pressione Enter para reler\n"
            )
            
            # Pedir caminho do JSON (já foi informado antes)
            json_path = text(
                "Caminho do JSON editado:",
                default="pipelines/stories/STORY/.tasks-proposed.json"
            ).ask()
            
            try:
                import json as json_lib
                with open(json_path, encoding="utf-8") as f:
                    edited_tasks = json_lib.load(f).get("tasks", [])
                
                self.console.print(f"✅ Carregadas {len(edited_tasks)} tasks do JSON editado")
                
                # Mostrar novamente e pedir confirmação
                return self.confirm_task_breakdown(edited_tasks)
            except Exception as e:
                self.console.print(f"[red]❌ Erro ao ler JSON: {e}[/red]")
                return False, []

        return True, tasks

    def confirm_files_to_commit(self, files: dict[str, list[str]]) -> tuple[bool, list[str]]:
        """
        Mostra arquivos modificados e pede confirmação.

        Args:
            files: {"modified": [...], "added": [...], "deleted": [...], "untracked": [...]}

        Returns:
            (approved: bool, selected_files: list)
        """
        self.ui.show_files_table(files)

        approved = confirm("Commit these files?", default=True).ask()

        all_staged = (
            files.get("modified", []) + files.get("added", []) + files.get("deleted", [])
        )

        return approved, all_staged if approved else []

    def confirm_plan(self, plan_file: str) -> str:
        """
        Pede confirmação do plano.

        Args:
            plan_file: Caminho do .plan.md

        Returns:
            "approve", "review" ou "reject"
        """
        self.console.print(f"\n📝 Plano gerado: [cyan]{plan_file}[/cyan]\n")

        choice = select(
            "Plano pronto. O que deseja fazer?",
            choices=[
                {"name": "✅ Approve — avançar para implementação", "value": "approve"},
                {"name": "👀 Review — abrir no editor", "value": "review"},
                {"name": "❌ Reject — regenerar plano", "value": "reject"},
            ],
        ).ask()

        if choice == "review":
            # Abrir arquivo no editor
            from utils.misc import open_file_cross_platform
            
            try:
                open_file_cross_platform(plan_file)
                self.console.print(f"✅ Arquivo aberto: {plan_file}")
            except OSError as e:
                self.console.print(f"[yellow]⚠️ Erro ao abrir arquivo: {e}[/yellow]")
                self.console.print(f"[dim]Abra manualmente: {plan_file}[/dim]")

        return choice

    def confirm_review(self, report_file: str) -> bool:
        """
        Pede confirmação do review.

        Args:
            report_file: Caminho do relatório MD

        Returns:
            True se aprovado
        """
        self.console.print(f"\n🔍 Review completo: [cyan]{report_file}[/cyan]\n")

        choice = select(
            "Review completo. O que deseja fazer?",
            choices=[
                {"name": "✅ Approve — continuar para commit", "value": "approve"},
                {"name": "👀 Ver Relatório — abrir no editor", "value": "view"},
                {"name": "🔧 Fix — voltar para implementação", "value": "fix"},
            ],
        ).ask()

        if choice == "view":
            # Abrir arquivo no editor (cross-platform)
            from utils.misc import open_file_cross_platform
            
            try:
                open_file_cross_platform(report_file)
                self.console.print(f"✅ Relatório aberto: {report_file}")
            except OSError as e:
                self.console.print(f"[yellow]⚠️ Erro ao abrir arquivo: {e}[/yellow]")
                self.console.print(f"[dim]Abra manualmente: {report_file}[/dim]")
            
            # Re-pedir confirmação
            return self.confirm_review(report_file)

        return choice == "approve"

    def confirm_implementation_done(self) -> bool:
        """Pede confirmação de implementação concluída."""
        return confirm("Implementação concluída?", default=False).ask()

    def ask_skill_output_path(self, expected_path: str) -> str:
        """
        Pede caminho do output do skill.

        Args:
            expected_path: Path esperado (default)

        Returns:
            Path informado pelo usuário
        """
        return text(
            "Caminho do arquivo gerado pelo skill:",
            default=expected_path,
        ).ask()

    def ask_repo_for_task(self, project_key: str, component: str | None) -> str | None:
        """
        Pergunta qual repositório específico usar para uma task.

        Chamado quando o component Jira (ex: "Front", "Back") mapeia para mais de
        um repo do mesmo tipo no projeto (ex: firebolt-frontend e dashboard-frontend).

        Args:
            project_key: Ex: "HUB"
            component: Component da task no Jira (ex: "Front", "Back")

        Returns:
            Repo ID selecionado (ex: "firebolt-frontend"), ou None se cancelado.
        """
        from utils.config import (
            get_repos_by_type,
            resolve_component_to_repo,
            get_repo_config,
        )

        # Determinar tipo esperado a partir do component
        component_lower = (component or "").lower()
        if "front" in component_lower:
            repo_type = "frontend"
        elif "back" in component_lower or "infra" in component_lower:
            repo_type = "backend"
        else:
            repo_type = None

        # Buscar repos do tipo correspondente
        if repo_type:
            candidates = get_repos_by_type(project_key, repo_type)
        else:
            # Component desconhecido → listar todos
            from utils.config import get_repos_for_project
            candidates = get_repos_for_project(project_key)

        # Apenas um candidato → selecionar automaticamente
        if len(candidates) == 1:
            return candidates[0]["id"]

        # Nenhum candidato → fallback para resolve padrão
        if not candidates:
            try:
                repo = resolve_component_to_repo(project_key, component)
                return repo["id"]
            except (KeyError, ValueError):
                return None

        # Múltiplos candidatos → perguntar ao usuário
        type_label = {"frontend": "Front", "backend": "Back"}.get(repo_type, component or "?")
        self.console.print(
            f"\n[yellow]⚠️  O component [bold]{component or '?'}[/bold] tem múltiplos "
            f"repositórios disponíveis.[/yellow]\n"
        )

        choices = []
        for r in candidates:
            label = (
                f"{r['id']}  "
                f"[dim]({r.get('tech_stack', '?')} · {r.get('local_path', '?')})[/dim]"
            )
            choices.append({"name": label, "value": r["id"]})

        selected = select(
            f"Qual repositório {type_label} esta task impacta?",
            choices=choices,
        ).ask()

        return selected

    def ask_pr_url(self) -> str:
        """
        Pede URL do PR criado.

        Returns:
            URL do PR no GitHub
        """
        return text(
            "URL do PR criado no GitHub:",
            validate=lambda url: url.startswith("https://github.com/") if url else False,
        ).ask()

"""
Testes para as melhorias implementadas no plano de melhorias.

Fase 1: Bug fixes
Fase 2: CLI split em commands/
Fase 3: Código morto removido
Fase 4: BasePipeline extraída
Fase 5: Documentação atualizada
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# ── fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def temp_dirs():
    state_dir = Path(tempfile.mkdtemp())
    log_dir = Path(tempfile.mkdtemp())
    yield state_dir, log_dir
    shutil.rmtree(state_dir, ignore_errors=True)
    shutil.rmtree(log_dir, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════
#  FASE 1 — Bug fixes
# ══════════════════════════════════════════════════════════════════


class TestFase1BugFixes:
    """Fase 1: 3 bugs corrigidos."""

    def test_1_1_github_ops_import_path(self):
        """Bug 1.1: import github_ops agora vem de operations/, não utils/."""
        import ast, inspect
        from cli.commands import advance

        source = inspect.getsource(advance._handle_aguardando_merge)
        tree = ast.parse(source)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module)

        assert "operations.github_ops" in imports, (
            "Bug 1.1 não corrigido: import deveria ser de operations.github_ops"
        )

    def test_1_2_finalize_subparser_registered(self):
        """Bug 1.2: comando 'finalize' deve existir no argparser."""
        import sys
        from unittest.mock import patch as _patch

        with _patch.object(sys, "argv", ["cli", "finalize", "--story", "HUB-1"]):
            from cli.main import parse_args
            args = parse_args()
            assert args.command == "finalize"
            assert args.story == "HUB-1"

    def test_1_3_task_discussion_in_goto_valid_states(self):
        """Bug 1.3: task_discussion deve estar em valid_states de cmd_goto."""
        import inspect
        from cli.helpers import cmd_goto

        source = inspect.getsource(cmd_goto)
        assert "task_discussion" in source, (
            "Bug 1.3 não corrigido: task_discussion ausente em cmd_goto"
        )


# ══════════════════════════════════════════════════════════════════
#  FASE 2 — CLI split
# ══════════════════════════════════════════════════════════════════


class TestFase2CliSplit:
    """Fase 2: cli/main.py extraído para cli/commands/."""

    def test_main_py_is_slim(self):
        """main.py deve ter menos de 200 linhas."""
        main_path = Path(__file__).parent.parent / "cli" / "main.py"
        line_count = len(main_path.read_text().splitlines())
        assert line_count < 200, f"main.py tem {line_count} linhas (esperado < 200)"

    def test_commands_package_exists(self):
        """cli/commands/ deve existir como pacote Python."""
        import cli.commands
        assert hasattr(cli.commands, "reload_task_context_from_json")
        assert hasattr(cli.commands, "format_task_story_label")

    def test_all_command_modules_importable(self):
        """Todos os módulos de comando devem importar sem erro."""
        from cli.commands.start import cmd_start, cmd_start_new_task
        from cli.commands.resume import cmd_resume
        from cli.commands.status import cmd_status
        from cli.commands.listing import cmd_list, cmd_list_stories, cmd_list_tasks
        from cli.commands.advance import cmd_next

    def test_dispatch_table_covers_all_commands(self):
        """Dispatch em main() deve cobrir todos os subparsers."""
        import inspect
        from cli.main import main

        source = inspect.getsource(main)
        expected_commands = [
            "start", "resume", "status", "list", "list-stories",
            "list-tasks", "next", "previous", "cancel", "goto",
            "unlock", "validate", "finalize",
        ]
        for cmd in expected_commands:
            assert f'"{cmd}"' in source, f"Comando '{cmd}' não encontrado no dispatch"


# ══════════════════════════════════════════════════════════════════
#  FASE 3 — Código morto removido
# ══════════════════════════════════════════════════════════════════


class TestFase3DeadCodeRemoved:
    """Fase 3: shared/ removido, deps limpas, fixtures órfãs removidas."""

    def test_shared_dir_removed(self):
        """shared/ não deve existir mais."""
        shared_dir = Path(__file__).parent.parent / "shared"
        assert not shared_dir.exists(), "shared/ ainda existe"

    def test_requirements_no_openai(self):
        """openai não deve estar em requirements.txt."""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        content = req_path.read_text()
        assert "openai" not in content, "openai ainda em requirements.txt"

    def test_formatting_tools_in_dev_requirements(self):
        """black e isort devem estar em requirements-dev.txt, não em requirements.txt."""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        req_dev_path = Path(__file__).parent.parent / "requirements-dev.txt"

        prod_content = req_path.read_text()
        dev_content = req_dev_path.read_text()

        assert "black" not in prod_content, "black ainda em requirements.txt"
        assert "isort" not in prod_content, "isort ainda em requirements.txt"
        assert "black" in dev_content, "black não está em requirements-dev.txt"
        assert "isort" in dev_content, "isort não está em requirements-dev.txt"

    def test_dev_requirements_no_httpx_asyncio(self):
        """httpx e pytest-asyncio não devem estar em requirements-dev.txt."""
        req_dev_path = Path(__file__).parent.parent / "requirements-dev.txt"
        content = req_dev_path.read_text()
        assert "httpx" not in content, "httpx ainda em requirements-dev.txt"
        assert "pytest-asyncio" not in content, "pytest-asyncio ainda em requirements-dev.txt"

    def test_conftest_no_orphan_fixtures(self):
        """conftest.py não deve ter fixtures dynamodb_table, mock_jira, aws."""
        conftest_path = Path(__file__).parent / "conftest.py"
        content = conftest_path.read_text()
        assert "dynamodb_table" not in content
        assert "mock_jira" not in content
        assert "def aws" not in content


# ══════════════════════════════════════════════════════════════════
#  FASE 4 — BasePipeline
# ══════════════════════════════════════════════════════════════════


class TestFase4BasePipeline:
    """Fase 4: StoryPipeline e TaskPipeline herdam de BasePipeline."""

    def test_base_pipeline_exists(self):
        """pipelines/base.py deve existir e exportar BasePipeline."""
        from pipelines.base import BasePipeline
        from statemachine import StateMachine
        assert issubclass(BasePipeline, StateMachine)

    def test_story_inherits_base(self):
        """StoryPipeline deve herdar de BasePipeline."""
        from pipelines.base import BasePipeline
        from pipelines.story_pipeline import StoryPipeline
        assert issubclass(StoryPipeline, BasePipeline)

    def test_task_inherits_base(self):
        """TaskPipeline deve herdar de BasePipeline."""
        from pipelines.base import BasePipeline
        from pipelines.task_pipeline import TaskPipeline
        assert issubclass(TaskPipeline, BasePipeline)

    def test_base_has_shared_methods(self):
        """BasePipeline deve ter os métodos compartilhados."""
        from pipelines.base import BasePipeline
        assert hasattr(BasePipeline, "_save_state")
        assert hasattr(BasePipeline, "_set_state")
        assert hasattr(BasePipeline, "_get_current_state_id")
        assert hasattr(BasePipeline, "_extract_project_key")
        assert hasattr(BasePipeline, "_now_iso")
        assert hasattr(BasePipeline, "_current_user")

    def test_story_pipeline_still_works(self, temp_dirs):
        """StoryPipeline cria estado corretamente após refator."""
        state_dir, log_dir = temp_dirs
        from pipelines.story_pipeline import StoryPipeline

        pipeline = StoryPipeline("TEST-100", state_dir, log_dir)
        pipeline.init_new_story()

        state_file = state_dir / "TEST-100-story.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["version"] == "2.0"
        assert data["story_key"] == "TEST-100"
        assert data["current_state"] == "story_analysis"

    def test_task_pipeline_still_works(self, temp_dirs):
        """TaskPipeline cria estado corretamente após refator."""
        state_dir, log_dir = temp_dirs
        from pipelines.task_pipeline import TaskPipeline

        pipeline = TaskPipeline("TEST-101", "TEST-100", state_dir, log_dir)
        with patch.object(pipeline, "start_planning"):
            pipeline.init_new_task("Test task", "Back")

        state_file = state_dir / "TEST-101-task.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["version"] == "2.0"
        assert data["task_key"] == "TEST-101"
        assert data["story_key"] == "TEST-100"
        assert data["current_state"] == "pending"

    def test_persist_key_story(self, temp_dirs):
        """StoryPipeline._persist_key deve ser a story_key."""
        state_dir, log_dir = temp_dirs
        from pipelines.story_pipeline import StoryPipeline

        pipeline = StoryPipeline("HUB-777", state_dir, log_dir)
        assert pipeline._persist_key == "HUB-777"
        assert pipeline._persist_type == "story"

    def test_persist_key_task(self, temp_dirs):
        """TaskPipeline._persist_key deve ser a task_key."""
        state_dir, log_dir = temp_dirs
        from pipelines.task_pipeline import TaskPipeline

        pipeline = TaskPipeline("HUB-778", "HUB-777", state_dir, log_dir)
        assert pipeline._persist_key == "HUB-778"
        assert pipeline._persist_type == "task"


# ══════════════════════════════════════════════════════════════════
#  FASE 5 — Documentação atualizada
# ══════════════════════════════════════════════════════════════════


class TestFase5Documentation:
    """Fase 5: docs atualizadas para refletir realidade."""

    def test_skills_readme_says_12(self):
        """skills/README.md deve mencionar 12 skills."""
        readme = Path(__file__).parent.parent / "skills" / "README.md"
        content = readme.read_text()
        assert "12 skills" in content, "README ainda diz 10 skills"

    def test_skills_readme_lists_all_12(self):
        """skills/README.md deve listar todas 12 pipeline-* skills."""
        readme = Path(__file__).parent.parent / "skills" / "README.md"
        content = readme.read_text()
        expected = [
            "pipeline-story-analyzer",
            "pipeline-story-planner",
            "pipeline-task-breaker",
            "pipeline-task-planner",
            "pipeline-plan-validator",
            "pipeline-task-definer",
            "pipeline-review-backend",
            "pipeline-review-frontend",
            "pipeline-review-documentation",
            "pipeline-pr-responder",
            "pipeline-pr-updater",
            "pipeline-create-technical-docs",
        ]
        for skill in expected:
            assert skill in content, f"Skill '{skill}' não listada no README"

    def test_tests_readme_no_ghost_files(self):
        """tests/README.md não deve referenciar testes que não existem."""
        readme = Path(__file__).parent / "README.md"
        content = readme.read_text()
        ghost_files = [
            "test_dynamodb_client.py",
            "test_state.py",
            "test_markdown.py",
            "test_file_utils.py",
            "test_bug_analysis_workflow.py",
        ]
        for ghost in ghost_files:
            assert ghost not in content, f"README ainda referencia {ghost}"

    def test_constants_docstring_v2(self):
        """PipelineStateEnum docstring deve mencionar fluxos v2.0."""
        from core.constants import PipelineStateEnum
        doc = PipelineStateEnum.__doc__
        assert "story_analysis" in doc
        assert "task_discussion" in doc

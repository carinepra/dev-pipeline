.PHONY: help install install-dev test lint format clean

# Python executable detection
PYTHON := PYTHONPATH=$(CURDIR) $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

# Virtual environment check
define check_venv
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "❌ Error: Virtual environment not activated"; \
		echo ""; \
		echo "💡 To fix this, run:"; \
		echo "   source venv/bin/activate"; \
		echo "   # or"; \
		echo "   source activate.sh"; \
		echo ""; \
		echo "   Then run your command again."; \
		echo ""; \
		exit 1; \
	fi
	@if [ "$$VIRTUAL_ENV" != "$(CURDIR)/venv" ]; then \
		echo "❌ Error: Wrong virtual environment active"; \
		echo ""; \
		echo "Current:  $$VIRTUAL_ENV"; \
		echo "Expected: $(CURDIR)/venv"; \
		echo ""; \
		echo "💡 To fix this, run:"; \
		echo "   deactivate"; \
		echo "   source venv/bin/activate"; \
		echo "   # or"; \
		echo "   source activate.sh"; \
		echo ""; \
		echo "   Then run your command again."; \
		echo ""; \
		exit 1; \
	fi
endef

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements.txt -r requirements-dev.txt

test:  ## Run tests with pytest
	pytest -v

test-cov:  ## Run tests with coverage report
	pytest --cov=. --cov-report=term-missing --cov-report=html

lint:  ## Run linters (mypy, black check, isort check)
	mypy core/ cli/ operations/ pipelines/ utils/ shared/
	black --check .
	isort --check-only .

format:  ## Format code with black and isort
	black .
	isort .

clean:  ## Clean cache files and artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# ─────────────────────────────────────────────────────────────────────────────
dev-pipeline-help:  ## Show quick help for dev-pipeline commands
	@echo "🚀 Dev Pipeline Commands - Quick Reference"
	@echo ""
	@echo "⚠️  Important: Always activate venv first!"
	@echo "   source venv/bin/activate"
	@echo ""
	@echo "📝 Most used commands:"
	@echo ""
	@echo "  Start new pipeline:"
	@echo "    make dev-pipeline STORY=PROJ-542              (story pipeline)"
	@echo "    make dev-pipeline TASK=PROJ-645               (task pipeline)"
	@echo "    make dev-pipeline TASK=NEW                   (create new task)"
	@echo "    make dev-pipeline TASK=NEW STORY=PROJ-542     (new task in story)"
	@echo ""
	@echo "  Resume interrupted pipeline:"
	@echo "    make dev-pipeline-resume STORY=PROJ-542      (or TASK=PROJ-645)"
	@echo ""
	@echo "  Advance to next stage:"
	@echo "    make dev-pipeline-next                       (auto-detect)"
	@echo "    make dev-pipeline-next STORY=PROJ-542         (or TASK=PROJ-645)"
	@echo ""
	@echo "  Go back to previous stage:"
	@echo "    make dev-pipeline-previous                   (auto-detect)"
	@echo "    make dev-pipeline-previous STORY=PROJ-542     (or TASK=PROJ-645)"
	@echo ""
	@echo "  Finalize story (docs + cleanup):"
	@echo "    make dev-pipeline-finalize STORY=PROJ-1234"
	@echo ""
	@echo "  View active work:"
	@echo "    make dev-pipeline-list"
	@echo "    make dev-pipeline-list STORY=PROJ-1234"
	@echo "    make dev-pipeline-list STATE=IMPLEMENTING"
	@echo "    make dev-pipeline-status STORY=PROJ-1234"
	@echo ""
	@echo "⚠️  Remember: Use STORY=<KEY> format (e.g. PROJ-1234, INVEST-100)"
	@echo ""

dev-pipeline:  ## Start pipeline (v2.0). Usage: make dev-pipeline STORY=PROJ-542 or TASK=PROJ-645 or TASK=NEW [DRY_RUN=true]
	@if [ -z "$(STORY)" ] && [ -z "$(TASK)" ]; then \
		echo "❌ Error: STORY or TASK parameter required"; \
		echo ""; \
		echo "📝 Correct usage:"; \
		echo "   make dev-pipeline STORY=PROJ-542              (story pipeline)"; \
		echo "   make dev-pipeline TASK=PROJ-645               (task pipeline)"; \
		echo "   make dev-pipeline TASK=NEW                   (create new task)"; \
		echo "   make dev-pipeline TASK=NEW STORY=PROJ-542     (new task in story)"; \
		echo "   make dev-pipeline STORY=PROJ-542 DRY_RUN=true"; \
		echo ""; \
		exit 1; \
	fi
	$(check_venv)
	$(PYTHON) cli/main.py start $(if $(STORY),--story $(STORY),) $(if $(TASK),--task $(TASK),) $(if $(DRY_RUN),--dry-run,)

dev-pipeline-start:  ## Alias for dev-pipeline (v2.0)
	$(MAKE) dev-pipeline $(if $(STORY),STORY=$(STORY),) $(if $(TASK),TASK=$(TASK),) $(if $(DRY_RUN),DRY_RUN=$(DRY_RUN),)

dev-pipeline-resume:  ## Resume paused pipeline (v2.0). Usage: make dev-pipeline-resume STORY=PROJ-542 or TASK=PROJ-645
	@if [ -z "$(STORY)" ] && [ -z "$(TASK)" ]; then \
		echo "❌ Error: STORY or TASK parameter required"; \
		echo ""; \
		echo "📝 Correct usage:"; \
		echo "   make dev-pipeline-resume STORY=PROJ-542"; \
		echo "   make dev-pipeline-resume TASK=PROJ-645"; \
		echo ""; \
		exit 1; \
	fi
	$(check_venv)
	$(PYTHON) cli/main.py resume $(if $(STORY),--story $(STORY),) $(if $(TASK),--task $(TASK),)

dev-pipeline-status:  ## Show status (v2.0). Usage: make dev-pipeline-status [STORY=PROJ-542] [TASK=PROJ-645]
	$(check_venv)
	$(PYTHON) cli/main.py status $(if $(STORY),--story $(STORY),) $(if $(TASK),--task $(TASK),)

dev-pipeline-list:  ## List all stories and tasks. Usage: make dev-pipeline-list [STORY=PROJ-1234] [STATE=IMPLEMENTING]
	$(check_venv)
	$(PYTHON) cli/main.py list $(if $(STORY),--story $(STORY),) $(if $(STATE),--state $(STATE),)

dev-pipeline-list-stories:  ## List all active stories with summary
	$(check_venv)
	$(PYTHON) cli/main.py list-stories

dev-pipeline-list-tasks:  ## List all tasks across all stories. Usage: make dev-pipeline-list-tasks [STORY=PROJ-1234] [STATE=PENDING]
	$(check_venv)
	$(PYTHON) cli/main.py list-tasks $(if $(STORY),--story $(STORY),) $(if $(STATE),--state $(STATE),)

dev-pipeline-next:  ## Advance to next stage (v2.0). Usage: make dev-pipeline-next [STORY=PROJ-542] [TASK=PROJ-645]
	$(check_venv)
	$(PYTHON) cli/main.py next $(if $(STORY),--story $(STORY),) $(if $(TASK),--task $(TASK),)

dev-pipeline-previous:  ## Go back to previous stage (v2.0). Usage: make dev-pipeline-previous [STORY=PROJ-542] [TASK=PROJ-645]
	$(check_venv)
	$(PYTHON) cli/main.py previous $(if $(STORY),--story $(STORY),) $(if $(TASK),--task $(TASK),)

dev-pipeline-goto:  ## Go to specific stage. Usage: make dev-pipeline-goto STORY=PROJ-1234 STAGE=review_changes (or TASK=)
	@if [ -z "$(STAGE)" ]; then \
		echo "❌ Error: STAGE parameter required"; \
		echo ""; \
		echo "📝 Correct usage:"; \
		echo "   make dev-pipeline-goto STORY=PROJ-1234 STAGE=story_analysis"; \
		echo "   make dev-pipeline-goto TASK=PROJ-645 STAGE=task_planning"; \
		echo ""; \
		exit 1; \
	fi
	$(check_venv)
	@if [ -n "$(STORY)" ]; then \
		$(PYTHON) cli/main.py goto --story $(STORY) --stage $(STAGE); \
	elif [ -n "$(TASK)" ]; then \
		$(PYTHON) cli/main.py goto --task $(TASK) --stage $(STAGE); \
	else \
		echo "❌ Error: STORY or TASK required"; \
		exit 1; \
	fi

dev-pipeline-cancel:  ## Cancel pipeline. Usage: make dev-pipeline-cancel STORY=PROJ-1234 (or TASK=)
	$(check_venv)
	@if [ -n "$(STORY)" ]; then \
		$(PYTHON) cli/main.py cancel --story $(STORY); \
	elif [ -n "$(TASK)" ]; then \
		$(PYTHON) cli/main.py cancel --task $(TASK); \
	else \
		echo "❌ Error: STORY or TASK required"; \
		echo "   make dev-pipeline-cancel STORY=PROJ-1234"; \
		echo "   make dev-pipeline-cancel TASK=PROJ-645"; \
		exit 1; \
	fi

dev-pipeline-delete:  ## Delete local pipeline data for a task (state + context files). Usage: make dev-pipeline-delete TASK=PROJ-645
	@if [ -z "$(TASK)" ]; then \
		echo "❌ Error: TASK parameter required"; \
		echo "   Usage: make dev-pipeline-delete TASK=PROJ-645"; \
		exit 1; \
	fi
	@STATE_FILE=".pipeline-state/$(TASK)-task.json"; \
	BACKUP_FILE=".pipeline-state/$(TASK)-task.backup.json"; \
	CONTEXT_DIR="pipelines/tasks/$(TASK)"; \
	echo ""; \
	echo "🗑️  Task a deletar: $(TASK)"; \
	echo ""; \
	echo "📂 Arquivos locais que serão removidos:"; \
	if [ -f "$$STATE_FILE" ]; then \
		echo "   $$STATE_FILE"; \
	else \
		echo "   $$STATE_FILE (não encontrado)"; \
	fi; \
	if [ -f "$$BACKUP_FILE" ]; then \
		echo "   $$BACKUP_FILE"; \
	fi; \
	if [ -d "$$CONTEXT_DIR" ]; then \
		find "$$CONTEXT_DIR" -type f | sort | sed 's/^/   /'; \
		echo "   $$CONTEXT_DIR/ (diretório)"; \
	else \
		echo "   $$CONTEXT_DIR/ (não encontrado)"; \
	fi; \
	echo ""; \
	echo "⚠️  ATENÇÃO: Esta ação é irreversível."; \
	echo "   A task $(TASK) NÃO será deletada no Jira."; \
	echo "   Apenas os arquivos locais do pipeline serão removidos."; \
	echo "   Para retomar, será necessário iniciar um novo pipeline."; \
	echo ""; \
	printf "❓ Confirma a deleção dos arquivos locais de $(TASK)? [s/N] "; \
	read CONFIRM; \
	if [ "$$CONFIRM" = "s" ] || [ "$$CONFIRM" = "S" ]; then \
		DELETED=0; \
		if [ -f "$$STATE_FILE" ]; then rm "$$STATE_FILE"; DELETED=$$((DELETED+1)); fi; \
		if [ -f "$$BACKUP_FILE" ]; then rm "$$BACKUP_FILE"; DELETED=$$((DELETED+1)); fi; \
		if [ -d "$$CONTEXT_DIR" ]; then rm -rf "$$CONTEXT_DIR"; DELETED=$$((DELETED+1)); fi; \
		echo ""; \
		echo "✅ Deleção concluída ($$DELETED item(s) removido(s))."; \
		echo "   A task $(TASK) permanece inalterada no Jira."; \
	else \
		echo ""; \
		echo "↩️  Operação cancelada. Nenhum arquivo foi removido."; \
	fi

dev-pipeline-unlock:  ## Force unlock. Usage: make dev-pipeline-unlock STORY=PROJ-1234 (or TASK=)
	$(check_venv)
	@if [ -n "$(STORY)" ]; then \
		$(PYTHON) cli/main.py unlock --story $(STORY); \
	elif [ -n "$(TASK)" ]; then \
		$(PYTHON) cli/main.py unlock --task $(TASK); \
	else \
		echo "❌ Error: STORY or TASK required"; \
		echo "   make dev-pipeline-unlock STORY=PROJ-1234"; \
		echo "   make dev-pipeline-unlock TASK=PROJ-645"; \
		exit 1; \
	fi

dev-pipeline-validate:  ## Validate state JSON (v2.0). Usage: make dev-pipeline-validate STORY=PROJ-1234 (or TASK=)
	$(check_venv)
	@if [ -n "$(STORY)" ]; then \
		$(PYTHON) cli/main.py validate --story $(STORY); \
	elif [ -n "$(TASK)" ]; then \
		$(PYTHON) cli/main.py validate --task $(TASK); \
	else \
		echo "❌ Error: STORY or TASK required"; \
		echo "   make dev-pipeline-validate STORY=PROJ-1234"; \
		echo "   make dev-pipeline-validate TASK=PROJ-645"; \
		exit 1; \
	fi

dev-pipeline-finalize:  ## Finalize story: docs + cleanup (v1.6.0). Usage: make dev-pipeline-finalize STORY=PROJ-1234
	@if [ -z "$(STORY)" ]; then \
		echo "❌ Error: STORY parameter required"; \
		echo ""; \
		echo "📝 Correct usage:"; \
		echo "   make dev-pipeline-finalize STORY=PROJ-542"; \
		echo ""; \
		echo "📚 This command will:"; \
		echo "   1. Collect real changes from all merged PRs"; \
		echo "   2. Generate technical documentation for the story"; \
		echo "   3. Review quality automatically"; \
		echo "   4. Open documentation PR"; \
		echo "   5. Cleanup temporary files"; \
		echo ""; \
		exit 1; \
	fi
	$(check_venv)
	@echo "📚 Finalizing story $(STORY)..."
	@echo ""
	$(PYTHON) cli/main.py finalize --story $(STORY)

init:  ## Initialize dev environment (install deps + setup git hooks)
	$(MAKE) install-dev
	@echo "✅ Dev environment initialized"
	@echo "   Next steps:"
	@echo "   1. Copy .env.modelo to .env and fill in credentials"
	@echo "   2. Run 'make dev-pipeline-help' for available commands"
	@echo "   3. Run 'make dev-pipeline TASK=PROJ-XXX' to start a pipeline"

check:  ## Run all checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

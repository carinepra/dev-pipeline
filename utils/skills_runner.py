"""Coordenador de skills Cursor (modo instrucional)."""

from __future__ import annotations

import json
import yaml
from pathlib import Path

from questionary import press_any_key_to_continue
from rich.console import Console
from rich.panel import Panel

from utils.ui import PipelineUI
from utils.validators import PipelineValidators


class SkillsRunner:
    """
    Coordenador de skills Cursor (modo instrucional).

    Mostra instruções para usuário executar skill no Cursor,
    aguarda output, parseia resultado.

    IMPORTANTE: Skills Cursor usam IA do Cursor (já pago).
    Este runner NÃO chama OpenAI/Anthropic.
    """

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.ui = PipelineUI(self.console)
        self.validators = PipelineValidators(self.console)
        self.skills_dir = Path.home() / ".cursor/skills"

    def run_story_planner(self, story_key: str, story_data: dict) -> Path:
        """
        Executar pipeline-story-analyzer.

        Flow:
          1. Mostra comando para Cursor com descrição detalhada
          2. Aguarda usuário executar
          3. Skill gera .story-plan.md com YAML frontmatter
          4. Valida robustamente (7 checks)
          5. Retorna path do plano

        Args:
            story_key: Issue key (ex: PROJ-1234)
            story_data: Dados da história (já fetched)

        Returns:
            Path do .story-plan.md gerado
        """
        from utils.paths import get_story_plan_path
        
        skill_name = "pipeline-story-analyzer"
        expected_output = get_story_plan_path(story_key)

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @{skill_name} analisar {story_key}

📋 [bold]O que a skill fará:[/bold]
   • Buscar design no Figma (se houver link)
   • Buscar regras de negócio nos docs do projeto
   • Explorar codebase (padrões similares)
   • Consolidar contexto completo
   • Executar sanity checks práticos
   • Validar contexto com você
   • Coletar decisões técnicas (2-3 perguntas)
   • Gerar .story-plan.md com YAML frontmatter

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title="🎯 Story Planner",
            border_style="cyan"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline validará se .story-plan.md foi gerado\n"
            "   → Parseará YAML frontmatter\n"
            "   → Verificará checksum e campos obrigatórios\n"
            "   → Se OK, salvará path no estado e avançará\n"
            "   → Se falhar, mostrará erro e aguardará correção\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        # Validação robusta
        plan_data = validate_story_plan(expected_output)

        self.console.print(f"[green]✅ Plano validado:[/green] {expected_output}")
        self.console.print(f"   Contexto: Figma={'✅' if plan_data['context']['figma']['has_figma'] else '❌'}, "
                          f"Docs={'✅' if plan_data['context']['docs']['has_docs'] else '❌'}, "
                          f"Validado={'✅' if plan_data['validated'] else '❌'}")

        return expected_output

    def run_jira_task_creator(self, story_key: str) -> dict:
        """
        Instrui usuário a executar pipeline-task-breaker no Cursor.

        Flow:
          1. Mostra comando para Cursor
          2. Aguarda usuário executar
          3. Skill gera JSON em pipelines/stories/{story_key}/.tasks-proposed.json
          4. Lê JSON e retorna

        Args:
            story_key: Issue key (ex: PROJ-1234)

        Returns:
            {"tasks": [{"summary": "...", "type": "backend", "estimate": "3h"}, ...]}
        """
        from utils.paths import get_story_tasks_proposed_path, get_story_plan_path
        
        expected_output = get_story_tasks_proposed_path(story_key)
        
        # Verificar se plano existe
        plan_path = get_story_plan_path(story_key)
        has_plan = plan_path.exists()

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-task-breaker quebrar {story_key}

📝 [bold]O que a skill fará:[/bold]
   {"• Ler contexto consolidado de .story-plan.md" if has_plan else "• Análise básica (modo standalone)"}
   • Propor quebra de subtasks (B1, F1, F2...)
   • Incluir: descrição, arquivos, dependências
   • Usar contexto de design, regras e código
   • Refinar proposta se necessário
   • Gerar formato JSON estruturado

[{"green" if has_plan else "yellow"}]Contexto:[/{"green" if has_plan else "yellow"}] {"✅ Story plan: " + str(plan_path) if has_plan else "⚠️ Sem story plan (modo standalone)"}

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title="📋 Task Creator",
            border_style="green"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline validará se .tasks-proposed.json foi gerado\n"
            "   → Direcionará para discussão das tasks no chat\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        # Ler output do skill
        output_path = self.validators.ask_skill_output_path(str(expected_output))

        # Validar arquivo existe e é JSON válido (primeira vez)
        try:
            with open(output_path, encoding="utf-8") as f:
                tasks_data = json.load(f)
            
            if "tasks" not in tasks_data:
                raise ValueError("JSON sem campo 'tasks'")
            
            tasks_count = len(tasks_data["tasks"])
            
            # NOVO: Direcionar para discussão no chat do Cursor
            self.console.print("\n")
            self.console.print(Panel(
                f"[bold cyan]💬 DISCUSSÃO E REFINAMENTO NO CHAT[/bold cyan]\n\n"
                f"[yellow]📋 Tasks propostas:[/yellow] {tasks_count} task(s) em [bold]{output_path}[/bold]\n\n"
                f"[green]🎯 Próximos passos:[/green]\n"
                f"   1. Abra o [bold]chat do Cursor[/bold] (Cmd/Ctrl+L)\n"
                f"   2. Mencione: [bold cyan]@{output_path}[/bold cyan]\n"
                f"   3. Discuta e refine com a IA:\n"
                f"      • Validar escopo de cada task\n"
                f"      • Adicionar/remover tasks se necessário\n"
                f"      • Ajustar descrições e dependências\n"
                f"      • Verificar se não há 'delírio' ou escopo excessivo\n"
                f"      • Confirmar alinhamento com ACs e Figma\n"
                f"   4. Peça para a IA [bold]atualizar o JSON[/bold] quando concluir\n"
                f"   5. Volte aqui e pressione ENTER para criar no Jira\n\n"
                f"[dim]💡 Discussão no chat permite validação mais rica que terminal[/dim]",
                title="💬 Refinar Tasks no Chat do Cursor",
                border_style="cyan"
            ))
            
            press_any_key_to_continue(
                "\n[bold yellow]⏸ Pipeline pausada para discussão[/bold yellow] - "
                "[bold]Pressione ENTER após refinar tasks no chat[/bold]"
            ).ask()
            
            # Recarregar JSON (pode ter sido modificado no chat)
            self.console.print("\n[cyan]⏳ Recarregando tasks (verificando modificações do chat)...[/cyan]")
            with open(output_path, encoding="utf-8") as f:
                tasks_data = json.load(f)
            
            if "tasks" not in tasks_data:
                raise ValueError("JSON sem campo 'tasks'")
            
            new_tasks_count = len(tasks_data["tasks"])
            
            if new_tasks_count != tasks_count:
                self.console.print(
                    f"[yellow]📝 Tasks modificadas:[/yellow] "
                    f"{tasks_count} → {new_tasks_count} task(s)"
                )
            
            self.console.print(f"[green]✅ Tasks finais:[/green] {new_tasks_count} task(s)")
            
            return tasks_data
            
        except FileNotFoundError:
            self.console.print(f"[red]❌ Arquivo não encontrado: {output_path}[/red]")
            raise
        except json.JSONDecodeError as e:
            self.console.print(f"[red]❌ JSON inválido em {output_path}: {e}[/red]")
            raise

    def run_task_planner(self, task_key: str, story_key: str) -> str:
        """
        Instrui usuário a executar pipeline-task-planner.

        Args:
            task_key: Task key (ex: PROJ-1235)
            story_key: Parent story key (ex: PROJ-1234)

        Returns:
            Path do .plan.md gerado
        """
        from utils.paths import get_task_plan_path
        
        expected_output = str(get_task_plan_path(task_key))

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-task-planner planejar {task_key}

📋 [bold]O que a skill fará:[/bold]
   • Ler task do Jira (summary, description, ACs)
   • Explorar codebase (arquivos relacionados)
   • Identificar padrões similares
   • Propor abordagem de implementação
   • Definir estrutura de arquivos
   • Listar testes necessários
   • Gerar plano detalhado em Markdown

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title="📝 Task Planner",
            border_style="blue"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline verificará se .plan.md foi gerado\n"
            "   → [bold cyan]Executará automaticamente[/bold cyan] pipeline-plan-validator (3 rounds)\n"
            "   → Abrirá arquivo melhorado para revisão final\n"
            "   → Se aprovado, avançará para implementação\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        return self.validators.ask_skill_output_path(expected_output)
    
    def run_task_planner_with_improvement(self, task_key: str, story_key: str) -> str:
        """
        Instrui usuário a executar task-planner (que chama pipeline-plan-validator automaticamente).

        Workflow otimizado:
        1. Skill pipeline-task-planner cria plano (Step 5)
        2. Skill automaticamente invoca pipeline-plan-validator (Step 6)
        3. Retorna: plano já melhorado

        Args:
            task_key: Key da task (ex: "PROJ-1236")
            story_key: Key da história pai

        Returns:
            Path do arquivo .plan.md melhorado
        """
        from utils.paths import get_task_plan_path
        
        expected_output = str(get_task_plan_path(task_key))

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan]

[bold yellow]@pipeline-task-planner planejar {task_key}[/bold yellow]

📋 [bold]Fluxo completo (automático):[/bold]

   [yellow]Step 1-4:[/yellow] Análise de contexto
   • Ler task do Jira (summary, description, ACs)
   • Explorar codebase (arquivos relacionados)
   • Identificar padrões similares
   • Consultar docs (se necessário)

   [cyan]Step 5:[/cyan] Criar plano inicial
   • Propor abordagem de implementação
   • Definir estrutura de arquivos
   • Listar testes necessários

   [magenta]Step 6:[/magenta] Melhorar plano (automático)
   • [bold cyan]Invoca @pipeline-plan-validator automaticamente[/bold cyan]
   • Round 1: Completude (missing context)
   • Round 2: Riscos e edge cases
   • Round 3: Padrões do projeto

[green]✅ Output final esperado:[/green] {expected_output} (já melhorado)

[dim]💡 Você só precisa executar 1 comando! A skill cuida de tudo.[/dim]
            """,
            title="📝 Task Planner (com Plan Improvement automático)",
            border_style="cyan"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline verificará se .plan.md foi gerado e melhorado\n"
            "   → Abrirá arquivo para revisão final\n"
            "   → Perguntará se aprova (prosseguir) ou rejeita (pausar)\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir (ambos steps)] [/bold]").ask()

        return self.validators.ask_skill_output_path(expected_output)

    def run_task_planner_for_new_task(
        self,
        task_key: str,
        story_key: str | None,
        context_file: Path
    ) -> str:
        """
        Instrui usuário a executar task-planner após criação da task no Jira.
        
        Args:
            task_key: Jira key da task (ex: PROJ-XXX) - já renomeado após create_issue
            story_key: Parent story (opcional)
            context_file: Path do arquivo com contexto coletado
        
        Returns:
            Path do .plan.md gerado
        """
        from utils.paths import get_task_plan_path
        
        expected_output = str(get_task_plan_path(task_key))
        
        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan]

[bold yellow]@pipeline-task-planner {context_file}[/bold yellow]

📋 [bold]Contexto disponível:[/bold]
   • Arquivo: {context_file}
   • Contém: título, descrição, ACs, links

[yellow]A skill deve:[/yellow]
   1. Ler contexto de {context_file}
   2. Explorar codebase (arquivos relacionados)
   3. Identificar padrões similares
   4. Propor implementação detalhada
   5. Gerar .plan.md com todos os steps

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title="📝 Task Planner",
            border_style="cyan"
        ))
        
        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()
        
        return self.validators.ask_skill_output_path(expected_output)
    
    def run_plan_improvement(self, plan_file: str, auto_mode: bool = False) -> None:
        """
        Instrui usuário a executar pipeline-plan-validator.

        Melhora plano in-place (modifica arquivo).

        Args:
            plan_file: Path do .plan.md
            auto_mode: Se True, executa sem pausa extra (já instruído no step anterior)
        """
        if not auto_mode:
            self.console.print(Panel.fit(
                f"""[cyan]Execute no Cursor:[/cyan] @pipeline-plan-validator melhorar {plan_file}

🔍 [bold]O que a skill fará:[/bold]
   • Ler plano atual
   • Round 1: Análise de completude (missing context)
   • Round 2: Análise de riscos e edge cases
   • Round 3: Análise de padrões do projeto
   • Aplicar melhorias no arquivo (in-place)
   • Mostrar diff das mudanças

[green]✅ Output:[/green] {plan_file} (modificado)
                """,
                title="🔄 Plan Improvement",
                border_style="magenta"
            ))

            self.console.print(
                "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
                "   → Pipeline assumirá que plano foi melhorado\n"
                "   → Continuará para próximo passo (implementação)\n"
            )

            press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()
        else:
            # Auto mode: usuário já foi instruído no step anterior
            self.console.print(
                f"\n[cyan]🔄 Executando automaticamente:[/cyan] "
                f"[bold cyan]@pipeline-plan-validator melhorar {plan_file}[/bold cyan]\n"
            )

    def run_review_changes(self, review_data_file: str, repo_type: str, story_key: str, task_key: str) -> str:
        """
        Instrui usuário a executar pipeline skill de review (front ou back).

        Args:
            review_data_file: Path do .review-data.json
            repo_type: "backend" ou "frontend"
            story_key: Parent story key
            task_key: Current task key

        Returns:
            Path do .review-report.md gerado
        """
        skill_by_repo = {
            "backend": "pipeline-review-backend",
            "frontend": "pipeline-review-frontend",
        }
        from utils.paths import get_task_review_report_path
        
        skill_name = skill_by_repo.get(repo_type, "pipeline-review-backend")
        expected_output = str(get_task_review_report_path(task_key))

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @{skill_name} analisar {review_data_file}

🤖 [bold]Pipeline já executou (automático):[/bold]
   • ✅ Git diff coletado
   • ✅ Linters executados (resultados salvos acima)
   • ✅ Dados consolidados em {review_data_file}

👤 [bold]Agora a skill (você) fará:[/bold]
   • Ler resultados dos linters (interpretação com IA)
   • Agrupar arquivos por domínio/contexto
   • Aplicar checks layer-específicos ({repo_type})
   • Verificar padrões do projeto
   • Identificar code smells e melhorias
   • Gerar relatório estruturado em Markdown

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title=f"🔍 Review ({repo_type.capitalize()})",
            border_style="yellow"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline verificará se .review-report.md foi gerado\n"
            "   → Abrirá relatório para revisão\n"
            "   → Perguntará se quer corrigir issues encontradas\n"
            "   → Se sim, volta para implementação\n"
            "   → Se não, avança para git publish\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        return self.validators.ask_skill_output_path(expected_output)

    @staticmethod
    def _review_data_file_path(story_key: str | None, task_key: str) -> str:
        """Path do `.review-data.json` consolidado pelo orquestrador antes do REVIEW_CHANGES."""
        from utils.paths import get_task_review_data_path
        
        return str(get_task_review_data_path(task_key))

    def _generate_review_data(self, task_key: str, repo_type: str) -> str:
        """
        Coleta git diff e roda linters, salvando resultado em .review-data.json.

        Returns:
            Path do arquivo gerado.
        """
        import json
        from operations.review_runner import (
            get_git_diff,
            run_linters,
            resolve_review_cwd,
        )
        from utils.paths import get_task_review_data_path

        cwd = resolve_review_cwd(repo_type)

        self.console.print(f"[dim]🔍 Coletando git diff em {cwd}...[/dim]")
        diff_data = get_git_diff(cwd)

        self.console.print(f"[dim]🔍 Executando linters ({repo_type})...[/dim]")
        linter_data = run_linters(repo_type=repo_type, cwd=cwd)

        review_data = {
            "repo": repo_type,
            "task_key": task_key,
            "diff": diff_data,
            "linters": linter_data["linters"],
            "summary": linter_data["summary"],
        }

        output_path = get_task_review_data_path(task_key)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(review_data, indent=2, ensure_ascii=False))

        self.console.print(f"[green]✅ Review data gerado: {output_path}[/green]")
        return str(output_path)

    def run_front_review_changes(self, task_key: str, story_key: str | None) -> str:
        """Gera .review-data.json e instrui usuário a executar pipeline-review-frontend."""
        self._generate_review_data(task_key, "frontend")
        review_data = self._review_data_file_path(story_key, task_key)
        sk = story_key or "_standalone"
        return self.run_review_changes(review_data, "frontend", sk, task_key)

    def run_back_review_changes(self, task_key: str, story_key: str | None) -> str:
        """Gera .review-data.json e instrui usuário a executar pipeline-review-backend."""
        self._generate_review_data(task_key, "backend")
        review_data = self._review_data_file_path(story_key, task_key)
        sk = story_key or "_standalone"
        return self.run_review_changes(review_data, "backend", sk, task_key)

    def run_git_publish(self, task_key: str, story_key: str | None) -> str:
        """
        Instrui usuário a executar pipeline-pr-updater (commit, push, criar PR).

        Args:
            task_key: Current task key
            story_key: Parent story key (opcional)

        Returns:
            URL do PR criado
        """
        import subprocess
        import json
        
        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-pr-updater publicar {task_key}

📤 [bold]O que a skill fará:[/bold]
   • Filtrar arquivos modificados (excluir .review-*, etc)
   • Confirmar arquivos a commitar
   • Criar commit com mensagem estruturada
   • Push para branch remota
   • Criar/atualizar PR no GitHub
   • Gerar descrição estruturada do PR

[green]✅ Output esperado:[/green] URL do PR no GitHub
            """,
            title="📤 Git Publish (Commit + Push + PR)",
            border_style="green"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline tentará detectar PR automaticamente\n"
            "   → Se não encontrar, pedirá URL manualmente\n"
            "   → Salvará PR URL no estado\n"
            "   → Avançará para aguardando_merge\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        # Tentar detectar PR automaticamente
        pr_url = None

        # 0. Verificar se PR URL já está no state (evita re-detecção)
        try:
            from utils.paths import get_task_state_path
            task_state_path = get_task_state_path(task_key)
            if task_state_path.exists():
                cached = json.loads(task_state_path.read_text())
                cached_pr_url = cached.get("pr_url")
                if cached_pr_url:
                    self.console.print(f"[green]✅ PR já registrado no state:[/green] {cached_pr_url}\n")
                    return cached_pr_url
        except Exception:
            pass

        # 1. Tentar descobrir qual repositório baseado no component
        try:
            from pathlib import Path as PathLib
            from utils.paths import get_task_state_path

            task_state_path = get_task_state_path(task_key)
            if task_state_path.exists():
                task_state = json.loads(task_state_path.read_text())
                # Usar component de task_data; fallback para collected_context
                component = task_state.get("task_data", {}).get("component")
                if not component:
                    component = task_state.get("collected_context", {}).get("component")
                task_project_key = task_state.get("project_key")
                
                from utils.repo_detector import get_repo_info_from_component
                repo_info = get_repo_info_from_component(component, project_key=task_project_key)
                repo_name = repo_info.get("local_path", "")
                
                cwd = PathLib.cwd()
                is_pipeline_repo = (cwd / ".pipeline-config.json").exists() or (cwd / "features" / "dev_pipeline").exists()
                workspace_root = cwd.parent if is_pipeline_repo else cwd
                repo_dir = workspace_root / repo_name
                
                self.console.print(f"[dim]🔍 Detectando PR no repo: {repo_name} (component: {component})[/dim]")
                self.console.print(f"[dim]   Path: {repo_dir}[/dim]")
                
                # Verificar se o diretório existe
                if not repo_dir.exists():
                    raise FileNotFoundError(f"Repositório não encontrado: {repo_dir}")
                
                # 2. Tentar buscar PR via gh CLI no repo correto
                result = subprocess.run(
                    ["gh", "pr", "view", "--json", "url,number,title"],
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    pr_data = json.loads(result.stdout)
                    pr_url = pr_data.get("url")
                    pr_number = pr_data.get("number")
                    pr_title = pr_data.get("title", "")[:50]
                    
                    self.console.print(f"[green]✅ PR detectado automaticamente:[/green]")
                    self.console.print(f"   [cyan]#{pr_number}[/cyan]: {pr_title}")
                    self.console.print(f"   {pr_url}\n")
                else:
                    # gh pr view falhou - tentar buscar PR pela task key
                    self.console.print(f"[dim]   Nenhum PR na branch atual, buscando por task key...[/dim]")
                    
                    search_result = subprocess.run(
                        ["gh", "pr", "list", "--search", task_key, "--json", "url,number,title", "--limit", "5"],
                        cwd=str(repo_dir),
                        capture_output=True,
                        text=True
                    )
                    
                    if search_result.returncode == 0 and search_result.stdout.strip():
                        pr_list = json.loads(search_result.stdout)
                        if pr_list:
                            # Pegar o primeiro PR da lista
                            pr_data = pr_list[0]
                            pr_url = pr_data.get("url")
                            pr_number = pr_data.get("number")
                            pr_title = pr_data.get("title", "")[:50]
                            
                            self.console.print(f"[green]✅ PR encontrado por busca:[/green]")
                            self.console.print(f"   [cyan]#{pr_number}[/cyan]: {pr_title}")
                            self.console.print(f"   {pr_url}\n")
                        else:
                            self.console.print(f"[yellow]⚠️ Nenhum PR encontrado com '{task_key}' no título[/yellow]")
                    else:
                        self.console.print(f"[yellow]⚠️ Não foi possível buscar PRs[/yellow]")
                
        except Exception as e:
            self.console.print(f"[yellow]⚠️ Não foi possível detectar PR automaticamente: {e}[/yellow]")
        
        # 3. Se não detectou, pedir manualmente
        if not pr_url:
            self.console.print("[yellow]📝 Por favor, informe a URL do PR:[/yellow]")
            pr_url = self.validators.ask_pr_url()
        
        return pr_url

    def run_address_pr_reviews(self, pr_comments_file: str, story_key: str, task_key: str) -> str:
        """
        Instrui usuário a executar pipeline-pr-responder.

        Args:
            pr_comments_file: Path do .pr-comments.json
            story_key: Parent story key
            task_key: Current task key

        Returns:
            Path do .pr-response-plan.md gerado
        """
        from utils.paths import get_task_pr_response_path
        
        expected_output = str(get_task_pr_response_path(task_key))

        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-pr-responder analisar {pr_comments_file}

💬 [bold]O que a skill fará:[/bold]
   • Ler comentários do PR de {pr_comments_file}
   • Categorizar por tipo (bug, style, question, suggestion)
   • Identificar bloqueadores vs não-bloqueadores
   • Propor plano de resposta para cada comentário
   • Sugerir mudanças de código (se aplicável)
   • Gerar plano estruturado em Markdown

[green]✅ Output esperado:[/green] {expected_output}
            """,
            title="💬 Address PR Reviews",
            border_style="cyan"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline verificará se .pr-response-plan.md foi gerado\n"
            "   → Abrirá plano para revisão\n"
            "   → Aguardará você implementar as correções\n"
            "   → Voltará para review-changes ou continuará ciclo PR\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        return self.validators.ask_skill_output_path(expected_output)

    def run_create_technical_docs(self, files_changed: list[str]) -> str:
        """
        Instrui usuário a executar skill-create-technical-docs.
        
        NOTA: Esta skill NÃO foi adaptada para pipeline (usa skill original).
        Create-technical-docs já funciona bem standalone.

        Args:
            files_changed: Lista de arquivos modificados

        Returns:
            Path do doc gerado
        """
        files_list = ", ".join(files_changed[:5])
        expected_output = "docs/feature-documentation.md"

        self.ui.show_skill_instruction(
            skill_name="create-technical-docs",
            command=f"@skill-create-technical-docs documentar arquivos: {files_list}",
            expected_output=expected_output,
        )

        press_any_key_to_continue("Pressione qualquer tecla quando skill concluir...").ask()

        return self.validators.ask_skill_output_path(expected_output)
    
    def run_create_docs(
        self,
        story_key: str,
        files_changed: list[str],
        critical_diffs: dict[str, str],
        db_changes: list[dict],
        pr_descriptions: list[dict],
        story_data: dict,
        tasks: list[dict],
    ) -> str:
        """
        Gera documentação técnica da HISTÓRIA completa.
        Prioriza alterações reais sobre descrição Jira.
        
        Args:
            story_key: Story key (ex: PROJ-542)
            files_changed: Lista completa de arquivos modificados em TODAS PRs
            critical_diffs: Dict file_path -> diff content (apenas arquivos críticos)
            db_changes: Lista de alterações de BD detectadas
            pr_descriptions: Lista de descrições das PRs mergeadas
            story_data: Dados da história do Jira
            tasks: Lista de tasks da história
        
        Returns:
            Path do documento gerado
        """
        from utils.paths import get_story_dir
        
        story_dir = get_story_dir(story_key)
        
        # Criar arquivo com dados consolidados para a skill
        doc_data = {
            "story_key": story_key,
            "files_changed": files_changed,
            "critical_diffs": critical_diffs,
            "db_changes": db_changes,
            "pr_descriptions": pr_descriptions,
            "story_data": story_data,
            "tasks": tasks,
            "generated_at": json.dumps({"$date": None}),
        }
        
        # Salvar input para skill
        data_path = story_dir / ".doc-gen-data.json"
        data_path.write_text(json.dumps(doc_data, indent=2), encoding="utf-8")
        
        # Expected output no docs repo
        expected_output = f"docs/{story_key}-technical-documentation.md"
        
        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-create-technical-docs analisar {data_path}

📋 [bold]O que a skill fará:[/bold]
   • Ler alterações REAIS de {len(files_changed)} arquivos
   • Analisar {len(critical_diffs)} diffs críticos
   • Documentar {len(db_changes)} alteração(ões) de BD
   • Consolidar {len(pr_descriptions)} PR(s) mergeada(s)
   • Gerar documentação completa da história

[yellow]📊 Dados de entrada:[/yellow]
   • Arquivo: {data_path}
   • Files: {len(files_changed)} arquivo(s)
   • Diffs críticos: {len(critical_diffs)} arquivo(s)
   • DB changes: {len(db_changes)} alteração(ões)
   • Tasks: {len(tasks)} task(s)

[green]✅ Output esperado:[/green] {expected_output}

[dim]💡 IMPORTANTE: Documentar o que FOI FEITO (não o que foi planejado)[/dim]
            """,
            title="📚 Documentation Generator",
            border_style="cyan"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline verificará se documentação foi gerada\n"
            "   → Avançará para review automático\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        # Validar output
        doc_path = self.validators.ask_skill_output_path(expected_output)
        
        return doc_path
    
    def run_review_documentation(
        self,
        doc_path: str,
        story_key: str,
        context: dict,
    ) -> dict:
        """
        Revisa qualidade da documentação técnica.
        Retorna checklist, score, e sugestões.
        
        Args:
            doc_path: Path do documento gerado
            story_key: Story key
            context: Contexto da documentação (files_count, has_db_changes, etc)
        
        Returns:
            Dict com score, checklist, suggestions, report_path
        """
        from utils.paths import get_story_dir
        
        story_dir = get_story_dir(story_key)
        
        # Criar arquivo com dados para review
        review_data = {
            "doc_path": doc_path,
            "story_key": story_key,
            "context": context,
        }
        
        # Salvar input para skill
        data_path = story_dir / ".doc-review-data.json"
        data_path.write_text(json.dumps(review_data, indent=2), encoding="utf-8")
        
        # Expected outputs
        report_path = story_dir / ".doc-review-report.md"
        report_json_path = story_dir / ".doc-review-report.json"
        
        self.console.print(Panel.fit(
            f"""[cyan]Execute no Cursor:[/cyan] @pipeline-review-documentation analisar {data_path}

🔍 [bold]O que a skill fará:[/bold]
   • Ler documentação gerada ({doc_path})
   • Verificar completude (cobre todas alterações?)
   • Verificar precisão (reflete alterações reais?)
   • Verificar qualidade (clareza, exemplos, diagramas)
   • Verificar links (Jira, PRs, arquivos)
   • Gerar checklist estruturado
   • Calcular score 0-10
   • Sugerir melhorias

[yellow]📊 Contexto:[/yellow]
   • Arquivos: {context['files_count']}
   • Tasks: {context['tasks_count']}
   • DB changes: {'Sim' if context['has_db_changes'] else 'Não'}
   • API changes: {'Sim' if context['has_api_changes'] else 'Não'}
   • UI changes: {'Sim' if context['has_ui_changes'] else 'Não'}

[green]✅ Outputs esperados:[/green]
   • {report_path}
   • {report_json_path}
            """,
            title="🔍 Documentation Review",
            border_style="yellow"
        ))

        self.console.print(
            "\n[yellow]💡 Ao pressionar ENTER:[/yellow]\n"
            "   → Pipeline lerá .doc-review-report.json\n"
            "   → Mostrará checklist e score\n"
            "   → Perguntará se quer aprovar ou revisar\n"
        )

        press_any_key_to_continue("[bold][Pressione ENTER quando skill concluir] [/bold]").ask()

        # Validar que report JSON foi gerado
        if not report_json_path.exists():
            raise FileNotFoundError(f"Skill não gerou {report_json_path}")
        
        # Ler resultado
        try:
            report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
            
            # Adicionar path do report
            report_data["report_path"] = str(report_path)
            
            return report_data
        
        except json.JSONDecodeError as e:
            self.console.print(f"[red]❌ JSON inválido em {report_json_path}: {e}[/red]")
            raise


def validate_story_plan(path: Path) -> dict:
    """
    Valida .story-plan.md robustamente (7 checks).

    Args:
        path: Path do .story-plan.md

    Returns:
        dict com dados do YAML frontmatter

    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se validação falhar
    """
    console = Console()

    # 1. Arquivo existe?
    if not path.exists():
        raise FileNotFoundError(f"Plano não encontrado: {path}")

    # 2. Não está vazio?
    content = path.read_text(encoding='utf-8')
    if len(content) < 100:
        raise ValueError(f"Plano muito curto ({len(content)} chars < 100)")

    # 3. Tem frontmatter YAML?
    if not content.startswith('---'):
        raise ValueError("Plano sem frontmatter YAML (deve começar com '---')")

    # 4. Parsear YAML
    try:
        parts = content.split('---', 2)
        if len(parts) < 3:
            raise ValueError("Frontmatter YAML incompleto (faltam delimitadores '---')")
        
        _, frontmatter, markdown = parts
        plan_data = yaml.safe_load(frontmatter)
        
    except Exception as e:
        raise ValueError(f"Erro ao parsear YAML: {e}")

    # 5. Campos obrigatórios
    required_fields = [
        "story_key",
        "generated_at",
        "validated",
        "scope",
        "context",
        "decisions"
    ]

    for field in required_fields:
        if field not in plan_data:
            raise ValueError(f"Campo obrigatório faltando no YAML: {field}")

    # 6. Validado pelo usuário?
    if not plan_data["validated"]:
        raise ValueError("Plano não foi validado pelo usuário (validated: false)")

    # 7. Contexto tem estrutura correta?
    if "figma" not in plan_data["context"]:
        raise ValueError("Contexto sem seção 'figma'")
    if "docs" not in plan_data["context"]:
        raise ValueError("Contexto sem seção 'docs'")
    if "codebase" not in plan_data["context"]:
        raise ValueError("Contexto sem seção 'codebase'")

    console.print("[green]✅ Validação: Todos os 7 checks passaram[/green]")

    return plan_data

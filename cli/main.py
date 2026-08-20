#!/usr/bin/env python3
"""CLI para Dev Pipeline Orchestrator (v1.8.0)."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.console import Console

from core.constants import DEFAULT_LOG_DIR, DEFAULT_STATE_DIR
from core.persistence import PipelineState
from cli.helpers import (
    cmd_cancel,
    cmd_finalize,
    cmd_goto,
    cmd_previous,
    cmd_unlock,
    cmd_validate,
)
from cli.commands.start import cmd_start
from cli.commands.resume import cmd_resume
from cli.commands.status import cmd_status
from cli.commands.listing import cmd_list, cmd_list_stories, cmd_list_tasks
from cli.commands.advance import cmd_next


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Dev Pipeline Orchestrator v1.8.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # start
    p = sub.add_parser("start", help="Start a story or task pipeline")
    p.add_argument("--story", help="Story key to start (ex: PROJ-1234)")
    p.add_argument("--task", help="Task key to start (ex: PROJ-1235) or 'NEW'")

    # resume
    p = sub.add_parser("resume", help="Resume paused pipeline")
    p.add_argument("--story", help="Story key to resume")
    p.add_argument("--task", help="Task key to resume")

    # status
    p = sub.add_parser("status", help="Show status of active pipelines")
    p.add_argument("--story", help="Story key for detailed view")
    p.add_argument("--task", help="Task key for detailed view")

    # list
    p = sub.add_parser("list", help="List all stories and tasks in progress")
    p.add_argument("--story", help="Filter by story key")
    p.add_argument("--state", help="Filter tasks by state")

    # list-stories (legacy)
    sub.add_parser("list-stories", help="List all active stories (legacy)")

    # list-tasks (legacy)
    p = sub.add_parser("list-tasks", help="List tasks (legacy)")
    p.add_argument("--story", help="Filter by story")
    p.add_argument("--state", help="Filter by state")

    # next
    p = sub.add_parser("next", help="Advance to next stage")
    p.add_argument("--story", help="Story key")
    p.add_argument("--task", help="Task key")

    # previous
    p = sub.add_parser("previous", help="Go back to previous stage")
    p.add_argument("--story", help="Story key")
    p.add_argument("--task", help="Task key")

    # cancel
    p = sub.add_parser("cancel", help="Cancel pipeline")
    p.add_argument("--story", help="Story key to cancel")
    p.add_argument("--task", help="Task key to cancel")

    # goto
    p = sub.add_parser("goto", help="Jump to specific stage")
    p.add_argument("stage", help="Target stage")
    p.add_argument("--story", help="Story key")
    p.add_argument("--task", help="Task key")

    # unlock
    p = sub.add_parser("unlock", help="Force unlock pipeline")
    p.add_argument("--story", help="Story key to unlock")
    p.add_argument("--task", help="Task key to unlock")

    # validate
    p = sub.add_parser("validate", help="Validate state file")
    p.add_argument("--story", help="Story key to validate")
    p.add_argument("--task", help="Task key to validate")

    # finalize
    p = sub.add_parser("finalize", help="Finalize story (docs + cleanup)")
    p.add_argument("--story", required=True, help="Story key to finalize")

    return parser.parse_args()


def main():
    """Main CLI entry point."""
    load_dotenv()
    args = parse_args()

    if not args.command:
        print("Error: No command specified. Use --help to see available commands.")
        return 1

    detected_width = Console().width or 80
    console = Console(width=max(110, detected_width))
    state_dir = Path(DEFAULT_STATE_DIR)
    log_dir = Path(DEFAULT_LOG_DIR)
    persistence = PipelineState(state_dir=state_dir)

    story = getattr(args, "story", None)
    task = getattr(args, "task", None)

    dispatch = {
        "start":        lambda: cmd_start(story, task, state_dir, log_dir, console),
        "resume":       lambda: cmd_resume(story, task, state_dir, log_dir, console, persistence),
        "status":       lambda: cmd_status(story, task, state_dir, log_dir, console, persistence),
        "list":         lambda: cmd_list(persistence, console, story, getattr(args, "state", None)),
        "list-stories": lambda: cmd_list_stories(persistence, console),
        "list-tasks":   lambda: cmd_list_tasks(persistence, console, story, getattr(args, "state", None)),
        "next":         lambda: cmd_next(story, task, state_dir, log_dir, console, persistence),
        "previous":     lambda: cmd_previous(story, task, persistence, console),
        "cancel":       lambda: cmd_cancel(story, task, persistence, console),
        "goto":         lambda: cmd_goto(story, task, args.stage, state_dir, log_dir, persistence, console),
        "unlock":       lambda: cmd_unlock(story, task, persistence, console),
        "validate":     lambda: cmd_validate(story, task, persistence, console),
        "finalize":     lambda: cmd_finalize(args.story, state_dir, log_dir, persistence, console),
    }

    handler = dispatch.get(args.command)
    if handler:
        return handler()

    console.print(f"[red]Unknown command: {args.command}[/red]")
    return 1


if __name__ == "__main__":
    sys.exit(main())

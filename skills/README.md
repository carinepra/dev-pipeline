# Pipeline Skills

This directory contains the **12 skills** that power the ai-dev-pipeline orchestrator. Each skill is responsible for one step of the delivery lifecycle and is designed to run inside Cursor Agent.

---

## Skills Overview

| # | Skill | Purpose | Reads from | Writes to |
|---|-------|---------|-----------|----------|
| 1 | `pipeline-story-analyzer` | Full story analysis + strategic planning + decisions | Figma, Docs, Codebase | `.story-plan.md` |
| 2 | `pipeline-story-planner` | Strategic planning orchestration for the story flow | Figma, Docs, Codebase | Story plan output |
| 3 | `pipeline-task-breaker` | Proposes task breakdown from story plan | `.story-plan.md` | `.tasks-proposed.json` |
| 4 | `pipeline-task-planner` | Implementation plan for a task (steps, risks, validations) | Pipeline state | `.plan.md` |
| 5 | `pipeline-plan-validator` | Validates and improves plans in 3 analysis rounds | `.plan.md` | Updated `.plan.md` |
| 6 | `pipeline-task-definer` | Defines/refines a new task when `TASK=NEW` | User input + Codebase | Task definition output |
| 7 | `pipeline-review-backend` | Backend code review (checklist + suggestions) | Diff + pipeline state | `.review-report.md` |
| 8 | `pipeline-review-frontend` | Frontend code review (checklist + suggestions) | Diff + pipeline state | `.review-report.md` |
| 9 | `pipeline-review-documentation` | Technical documentation review | Docs + pipeline state | Review report |
| 10 | `pipeline-pr-responder` | Processes review comments and generates a response plan | `.pr-comments.json` | `.pr-response-plan.md` |
| 11 | `pipeline-pr-updater` | Applies changes (commit/push) and updates PR | `.pr-response-plan.md` | Commit + PR update |
| 12 | `pipeline-create-technical-docs` | Consolidates and generates final technical documentation | Docs + pipeline state | Final docs |

---

## Installation

> **Prerequisite:** Cursor IDE with Agent mode enabled. Skills are installed globally for your Cursor installation, not per-project.

### Automatic (recommended)

Run the sync script after cloning the repo:

```bash
./scripts/sync-skills.sh
```

This will:
1. Copy all `pipeline-*` skills to `~/.cursor/skills/`
2. Detect changes — only updates skills that differ from the repo
3. Show a sync summary

**Dry run** (preview changes without applying):

```bash
./scripts/sync-skills.sh --dry-run
```

### Manual

```bash
cp -r skills/pipeline-* ~/.cursor/skills/
```

### Verify installation

```bash
ls -la ~/.cursor/skills/pipeline-*
```

You should see 12 directories:

```
pipeline-story-analyzer/
pipeline-story-planner/
pipeline-task-breaker/
pipeline-task-planner/
pipeline-plan-validator/
pipeline-task-definer/
pipeline-review-backend/
pipeline-review-frontend/
pipeline-review-documentation/
pipeline-pr-responder/
pipeline-pr-updater/
pipeline-create-technical-docs/
```

---

## Why Separate Pipeline Skills?

The original `@skill-*` skills were designed for standalone use in Cursor. The pipeline requires specific guarantees that standalone skills don't provide:

| Aspect | Original skill | Pipeline skill |
|--------|---------------|----------------|
| **Output** | Optional / flexible | Always writes a file |
| **File path** | User-defined | Fixed by convention |
| **Linters** | Runs linters | Reads results (orchestrator already ran them) |
| **Jira** | Creates issues | Only proposes (orchestrator creates) |
| **Scope** | Always asks | Reads from state (avoids duplication) |
| **Analysis** | Integrated | Separated (`pipeline-story-analyzer` owns it) |
| **Integration** | Standalone | Optimized for pipeline flow |

### Key dependencies between skills

Not all skills are independent — some depend on the output of a previous skill:

```
pipeline-story-analyzer       → writes .story-plan.md
        ↓
pipeline-task-breaker         → reads .story-plan.md, writes .tasks-proposed.json
        ↓
pipeline-task-planner         → reads pipeline state, writes .plan.md
        ↓
pipeline-plan-validator       → reads .plan.md, improves in 3 rounds
        ↓
(Cursor Agent implements the task — not a pipeline skill)
        ↓
pipeline-review-backend /
pipeline-review-frontend      → reads diff + state, writes .review-report.md
        ↓
pipeline-pr-responder         → reads .pr-comments.json, writes .pr-response-plan.md
        ↓
pipeline-pr-updater           → reads .pr-response-plan.md, commits + updates PR
        ↓
pipeline-create-technical-docs → reads docs + state, writes final documentation
```

---

## Skill Structure

Each `SKILL.md` is the instruction file Cursor Agent reads when you invoke `@pipeline-*`. It defines what the skill expects as input, what it must produce as output, and how to handle edge cases. Every skill follows the same structure:

```
pipeline-*/
└── SKILL.md
    ├── Description
    ├── Expected input (from orchestrator)
    ├── Workflow (step by step)
    ├── Required output (fixed path)
    ├── Differences from original skill
    ├── Validations
    ├── Troubleshooting
    └── Examples
```

---

## Usage During the Pipeline

The orchestrator provides clear instructions at each step:

```
Run in Cursor:
  @pipeline-task-breaker break <PROJECT>-XXX

Output will be written to:
  pipelines/stories/<PROJECT>-XXX/.tasks-proposed.json
```

> ⚠️ Always use `@pipeline-*` skills during the pipeline flow. The original `@skill-*` skills do not follow the orchestrator's output conventions and will break state.

---

## Output Path Conventions

All skills write to standardized paths under `pipelines/`:

```
pipelines/
├── stories/{story_key}/
│   ├── .story-plan.md                # pipeline-story-analyzer
│   └── .tasks-proposed.json          # pipeline-task-breaker
└── tasks/{task_key}/
    ├── .plan.md                      # pipeline-task-planner
    ├── .review-report.md             # pipeline-review-backend / pipeline-review-frontend
    └── .pr-response-plan.md          # pipeline-pr-responder
```

---

## Keeping Skills Up to Date

When skills are updated in the repo:

```bash
git pull
./scripts/sync-skills.sh
```

The script only updates skills that differ from the repo — no unnecessary overwrites.

---

## Extending: Adding a New Skill

1. Create `skills/pipeline-{name}/SKILL.md` following the existing structure
2. In your `SKILL.md`, instruct the agent to always write its output file and confirm:
   ```
   Write(path=expected_output, contents=result)
   ✅ File created: {expected_output}
   ```
3. Add the corresponding method in `utils/skills_runner.py`
4. Integrate the step into `dev_pipeline.py`
5. Document inputs, outputs, and file paths in this README
6. Commit — other developers run `./scripts/sync-skills.sh` to get the update

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Skill 'pipeline-*' not found` in Cursor | Skill not installed | Run `./scripts/sync-skills.sh` |
| `FileNotFoundError: pipelines/...` | Skill didn't complete or didn't write output | Check Cursor chat for "✅ File created:" — re-run skill if missing |
| Wrong output path (e.g. `<KEY>.plan.md` instead of `pipelines/tasks/<KEY>/.plan.md`) | Used `@skill-*` instead of `@pipeline-*` | Always use `@pipeline-*` skills |
| Skill exists but is outdated | Local version differs from repo | Run `git pull && ./scripts/sync-skills.sh` |

---

## Related Documentation

<!-- PROMPT FOR AGENT: Verify these paths exist before publishing. Add or remove links accordingly. -->
- **Pipeline guide:** [`docs/dev-pipeline-guide.md`](../docs/dev-pipeline-guide.md)
- **Skills integration guide:** [`docs/pipeline-skills-integration.md`](../docs/pipeline-skills-integration.md)
- **Main README:** [`README.md`](../README.md)

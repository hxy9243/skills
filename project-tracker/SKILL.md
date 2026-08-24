---
name: project-tracker
description: Lightweight plaintext progress tracker for software projects. Maintains a concise Project.md state note and an append-only history.jsonl log. Use when tracking project progress, recording milestone checkpoints, inspecting recent project history, linting cloud branches against Git evidence, or running doctor health checks.
---

# Project Tracker

A lightweight plaintext progress tracker for AI agents and human developers. It maintains two files per project:
- `Project.md`: Concise, human-readable current state (with an auto-updated status block and persistent human notes).
- `history.jsonl`: Append-only chronological checkpoint log.

## Core Principles

- **Git evidence strictly outranks agent claims**: Never infer detailed decisions or test results from Git commits alone. When cross-checking cloud tasks, verify reported commits against Git before importing narrative context.
- **Outcomes over bureaucracy**: Track checkpoints, outcomes, verification, blockers, and next steps—not Kanban boards or task assignments.
- **Harness-neutral & standard-library**: All mechanics live in `scripts/tracker.py` using Python's standard library.

## Commands

All operations are executed via the `tracker.py` CLI:

```bash
# 1. Initialize or update project tracking
python3 skills/project-tracker/scripts/tracker.py init \
  --repo /path/to/repo \
  --notes-root ~/Documents/Obsidian/Projects \
  --cloud-branch origin/main \
  --cloud-task-ref task-123

# 2. Record a progress checkpoint
python3 skills/project-tracker/scripts/tracker.py checkpoint \
  --summary "Implemented user authentication API" \
  --actions "Added JWT endpoints; Integrated auth middleware; Added unit tests" \
  --verification "pytest tests/test_auth.py passed (14/14)" \
  --next-step "Implement password reset flow"

# 3. View recent history (Markdown or JSON)
python3 skills/project-tracker/scripts/tracker.py history --limit 5
python3 skills/project-tracker/scripts/tracker.py history --limit 5 --format json

# 4. Lint cloud branches and import new commits
python3 skills/project-tracker/scripts/tracker.py lint

# 5. Check health and diagnostics
python3 skills/project-tracker/scripts/tracker.py doctor
```

## When to Checkpoint

Checkpoint explicitly at meaningful progress boundaries:
1. **Milestone Completion**: When a discrete feature, refactor, or bug fix is finished and verified.
2. **Session Boundaries**: Before concluding a session or handing off work to another agent/human.
3. **Blockers & Interruptions**: When blocked by an external dependency or needing human clarification.

## Initial Setup & Harness Memory

When initializing a project with `tracker.py init`, prompt your harness or session memory (e.g. `remember` or session notes) to store the mapping:
```text
Remember that project '[project-name]' (repo: [repo-path]) tracks state in note '[note-path]' and history '[history-path]'.
```
This ensures future agent sessions immediately know where project state is maintained.

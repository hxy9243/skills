#!/usr/bin/env python3
"""
Lightweight Project Tracker CLI
A harness-neutral, plaintext progress tracker for AI agents and human developers.
"""

import argparse
import dataclasses
import datetime
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

START_DELIMITER = "<!-- PROJECT-TRACKER:START -->"
END_DELIMITER = "<!-- PROJECT-TRACKER:END -->"

DEFAULT_REGISTRY_PATH = os.path.expanduser("~/.config/project-tracker/registry.json")
FALLBACK_REGISTRY_PATH = os.path.expanduser("~/.project-tracker/registry.json")


def get_registry_path() -> Path:
    env_path = os.environ.get("PROJECT_TRACKER_REGISTRY")
    if env_path:
        return Path(env_path).resolve()
    primary = Path(DEFAULT_REGISTRY_PATH)
    fallback = Path(FALLBACK_REGISTRY_PATH)
    if fallback.exists() and not primary.exists():
        return fallback.resolve()
    return primary.resolve()


def load_registry() -> Dict[str, Any]:
    path = get_registry_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_registry(registry: Dict[str, Any]) -> None:
    path = get_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp." + uuid.uuid4().hex[:8])
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, path)


def get_git_repo_root(cwd: Optional[Path] = None) -> Optional[Path]:
    target_dir = cwd or Path.cwd()
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(target_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return Path(res.stdout.strip()).resolve()
    except Exception:
        pass
    # Fallback to traversing upwards looking for .git
    curr = target_dir.resolve()
    while curr != curr.parent:
        if (curr / ".git").exists():
            return curr
        curr = curr.parent
    return None


def get_git_branch(repo_path: Optional[Path] = None) -> Optional[str]:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_path or Path.cwd()),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            branch = res.stdout.strip()
            return branch if branch != "HEAD" else None
    except Exception:
        pass
    return None


def get_git_head_commit(repo_path: Optional[Path] = None, short: bool = True) -> Optional[str]:
    try:
        cmd = ["git", "rev-parse", "--short", "HEAD"] if short else ["git", "rev-parse", "HEAD"]
        res = subprocess.run(
            cmd,
            cwd=str(repo_path or Path.cwd()),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return None


class FileLock:
    """Bounded file lock using fcntl.flock."""

    def __init__(self, lock_file: Path, timeout: float = 5.0, poll_interval: float = 0.05):
        self.lock_file = lock_file
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fd: Optional[int] = None

    def __enter__(self):
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR, 0o644)
        start_time = time.time()
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (BlockingIOError, OSError):
                if time.time() - start_time >= self.timeout:
                    os.close(self._fd)
                    self._fd = None
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file} within {self.timeout}s")
                time.sleep(self.poll_interval)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                os.close(self._fd)
                self._fd = None


@dataclasses.dataclass
class CheckpointEvent:
    id: str
    timestamp: str
    revision: int
    summary: str
    harness: str = "unknown"
    actions: List[str] = dataclasses.field(default_factory=list)
    branch: Optional[str] = None
    commit_range: Optional[str] = None
    verification: Optional[str] = None
    blockers: Optional[str] = None
    next_step: Optional[str] = None
    source: str = "local"  # 'local', 'cloud', 'git-evidence'
    task_ref: Optional[str] = None
    missing_narrative_context: bool = False
    snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CheckpointEvent":
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            timestamp=d.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            revision=int(d.get("revision", 1)),
            summary=d.get("summary", ""),
            harness=d.get("harness", "unknown"),
            actions=d.get("actions", []) or [],
            branch=d.get("branch"),
            commit_range=d.get("commit_range"),
            verification=d.get("verification"),
            blockers=d.get("blockers"),
            next_step=d.get("next_step"),
            source=d.get("source", "local"),
            task_ref=d.get("task_ref"),
            missing_narrative_context=bool(d.get("missing_narrative_context", False)),
            snapshot=d.get("snapshot"),
        )


def read_history_events(history_path: Path) -> List[CheckpointEvent]:
    if not history_path.exists():
        return []
    events: List[CheckpointEvent] = []
    with open(history_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                events.append(CheckpointEvent.from_dict(data))
            except Exception:
                continue
    return events


def read_recent_events(history_path: Path, limit: int) -> List[CheckpointEvent]:
    """Efficiently read up to `limit` recent events from history.jsonl."""
    if not history_path.exists():
        return []
    events = read_history_events(history_path)
    if limit <= 0:
        return events
    return events[-limit:]


def append_history_event(history_path: Path, event: CheckpointEvent) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def format_generated_markdown(project_name: str, event: CheckpointEvent) -> str:
    lines = [
        START_DELIMITER,
        "## Current Status",
        "",
        f"- **Latest Update**: {event.timestamp}",
        f"- **Revision**: #{event.revision} (`{event.id[:8]}`)",
        f"- **Harness**: {event.harness} (Source: `{event.source}`)",
    ]
    if event.branch:
        lines.append(f"- **Git Branch**: `{event.branch}`")
    if event.commit_range:
        lines.append(f"- **Commit / Range**: `{event.commit_range}`")
    if event.task_ref:
        lines.append(f"- **Cloud Task**: `{event.task_ref}`")
    if event.missing_narrative_context:
        lines.append("- ⚠️ *Missing narrative context: created from Git evidence only.*")

    lines.append("")
    lines.append(f"### Summary\n{event.summary}")

    if event.actions:
        lines.append("")
        lines.append("### Recent Actions")
        for i, act in enumerate(event.actions, 1):
            lines.append(f"{i}. {act}")

    if event.verification:
        lines.append("")
        lines.append(f"### Verification\n{event.verification}")

    if event.blockers:
        lines.append("")
        lines.append(f"### Blockers\n{event.blockers}")

    if event.next_step:
        lines.append("")
        lines.append(f"### Next Step\n{event.next_step}")

    lines.append("")
    lines.append(END_DELIMITER)
    return "\n".join(lines)


def update_markdown_note(note_path: Path, project_name: str, event: CheckpointEvent) -> None:
    note_path.parent.mkdir(parents=True, exist_ok=True)
    generated_block = format_generated_markdown(project_name, event)

    if not note_path.exists():
        initial_content = f"# {project_name}\n\n{generated_block}\n\n## Project Notes\n\n- Add persistent human notes, decisions, and context here.\n"
        temp_path = note_path.with_suffix(".tmp." + uuid.uuid4().hex[:8])
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(initial_content)
        os.replace(temp_path, note_path)
        return

    content = note_path.read_text(encoding="utf-8")

    pattern = re.compile(
        re.escape(START_DELIMITER) + r".*?" + re.escape(END_DELIMITER),
        re.DOTALL,
    )

    if pattern.search(content):
        new_content = pattern.sub(generated_block, content, count=1)
    else:
        # If delimiter not found, prepend after the top heading or at top
        lines = content.splitlines(keepends=True)
        if lines and lines[0].startswith("# "):
            title_line = lines[0]
            rest = "".join(lines[1:]).lstrip()
            new_content = f"{title_line}\n{generated_block}\n\n{rest}"
        else:
            new_content = f"{generated_block}\n\n{content}"

    temp_path = note_path.with_suffix(".tmp." + uuid.uuid4().hex[:8])
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(temp_path, note_path)


def get_default_notes_root(repo_path: Optional[Path] = None) -> Path:
    env_root = os.environ.get("PROJECT_TRACKER_NOTES_ROOT")
    if env_root:
        return Path(env_root).resolve()
    obsidian_root = Path.home() / "Documents" / "kevinhusnotes" / "10_Projects"
    if obsidian_root.exists():
        return obsidian_root.resolve()
    if repo_path:
        return (repo_path / ".tracker").resolve()
    return (Path.cwd() / ".tracker").resolve()


def resolve_project_config(
    repo_override: Optional[str] = None,
    note_override: Optional[str] = None,
    history_override: Optional[str] = None,
) -> Tuple[str, Path, Path, Path, Dict[str, Any]]:
    """Resolves project name, repo root, note file path, history file path, and registry config."""
    repo_path = Path(repo_override).resolve() if repo_override else get_git_repo_root()
    if not repo_path:
        repo_path = Path.cwd().resolve()

    registry = load_registry()
    repo_key = str(repo_path)
    config = registry.get(repo_key, {})

    project_name = config.get("name") or repo_path.name

    if note_override:
        note_path = Path(note_override).resolve()
    elif config.get("note_file"):
        note_path = Path(config["note_file"]).resolve()
    else:
        notes_root = Path(config.get("notes_root", get_default_notes_root(repo_path))).resolve()
        note_path = (notes_root / project_name / "Project.md").resolve()

    if history_override:
        history_path = Path(history_override).resolve()
    elif config.get("history_file"):
        history_path = Path(config["history_file"]).resolve()
    else:
        history_path = note_path.parent / "history.jsonl"

    return project_name, repo_path, note_path, history_path, config


# -----------------------------------------------------------------------------
# COMMAND: init
# -----------------------------------------------------------------------------
def cmd_init(args: argparse.Namespace) -> int:
    repo_path = Path(args.repo).resolve() if args.repo else get_git_repo_root() or Path.cwd().resolve()
    project_name = args.name or repo_path.name

    if args.notes_root:
        notes_root = Path(args.notes_root).resolve()
    else:
        notes_root = get_default_notes_root(repo_path)

    if args.note_file:
        note_path = Path(args.note_file).resolve()
    else:
        note_path = (notes_root / project_name / "Project.md").resolve()

    if args.history_file:
        history_path = Path(args.history_file).resolve()
    else:
        history_path = (note_path.parent / "history.jsonl").resolve()

    note_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize empty history if not exists
    if not history_path.exists():
        history_path.touch()

    # Initialize note if not exists
    if not note_path.exists():
        initial_event = CheckpointEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            revision=1,
            summary="Initialized project tracker",
            harness=args.harness or "init",
            actions=["Initialized project tracking note and history log"],
            branch=get_git_branch(repo_path),
            commit_range=get_git_head_commit(repo_path),
            source="local",
        )
        append_history_event(history_path, initial_event)
        update_markdown_note(note_path, project_name, initial_event)

    # Update Registry
    registry = load_registry()
    repo_key = str(repo_path)
    entry = registry.get(repo_key, {})
    entry.update({
        "name": project_name,
        "repo_path": str(repo_path),
        "notes_root": str(notes_root),
        "note_file": str(note_path),
        "history_file": str(history_path),
        "cloud_branch": args.cloud_branch or entry.get("cloud_branch"),
        "cloud_task_ref": args.cloud_task_ref or entry.get("cloud_task_ref"),
        "cloud_messenger_cmd": args.cloud_messenger_cmd or entry.get("cloud_messenger_cmd"),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    registry[repo_key] = entry
    save_registry(registry)

    memory_prompt = (
        f"Remember that project '{project_name}' (repo: {repo_path}) "
        f"tracks state in note '{note_path}' and history '{history_path}'."
    )

    if args.json:
        print(json.dumps({
            "status": "ok",
            "project_name": project_name,
            "repo_path": str(repo_path),
            "note_file": str(note_path),
            "history_file": str(history_path),
            "registry_path": str(get_registry_path()),
            "harness_memory_hint": memory_prompt,
        }, indent=2))
    else:
        print(f"Initialized project tracker for '{project_name}'")
        print(f"  Repository:   {repo_path}")
        print(f"  Note file:    {note_path}")
        print(f"  History log:  {history_path}")
        print(f"  Registry:     {get_registry_path()}")
        print("\n--- Harness Memory Recommendation ---")
        print(f"Prompt the harness/session memory:")
        print(f"  \"{memory_prompt}\"")

    return 0


# -----------------------------------------------------------------------------
# COMMAND: checkpoint
# -----------------------------------------------------------------------------
def cmd_checkpoint(args: argparse.Namespace) -> int:
    project_name, repo_path, note_path, history_path, config = resolve_project_config(
        repo_override=args.repo,
        note_override=args.note_file,
        history_override=args.history_file,
    )

    lock_file = history_path.parent / (history_path.name + ".lock")
    harness = args.harness or os.environ.get("TRACKER_HARNESS", "local-agent")
    branch = args.branch or get_git_branch(repo_path)
    commit = args.commit or args.commit_range or get_git_head_commit(repo_path)

    actions: List[str] = []
    if args.action:
        actions.extend([a.strip() for a in args.action if a.strip()])
    elif args.actions:
        # Prefer semicolon splitting, fallback to comma if no semicolon
        if ";" in args.actions:
            actions.extend([a.strip() for a in args.actions.split(";") if a.strip()])
        else:
            actions.extend([a.strip() for a in args.actions.split(",") if a.strip()])

    max_attempts = 2
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            with FileLock(lock_file, timeout=args.lock_timeout):
                events = read_history_events(history_path)
                last_revision = events[-1].revision if events else 0
                
                if args.expected_revision is not None and args.expected_revision != last_revision:
                    if attempt < max_attempts:
                        # Reread and retry once
                        time.sleep(0.1)
                        continue
                    else:
                        print(
                            f"Error: Stale revision detected. Expected revision #{args.expected_revision}, "
                            f"but history is at revision #{last_revision}.",
                            file=sys.stderr,
                        )
                        return 1

                new_revision = last_revision + 1
                event = CheckpointEvent(
                    id=args.id or str(uuid.uuid4()),
                    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    revision=new_revision,
                    summary=args.summary,
                    harness=harness,
                    actions=actions,
                    branch=branch,
                    commit_range=commit,
                    verification=args.verification,
                    blockers=args.blockers,
                    next_step=args.next_step,
                    source=args.source or "local",
                    task_ref=args.task_ref or config.get("cloud_task_ref"),
                    missing_narrative_context=args.missing_narrative_context,
                )

                append_history_event(history_path, event)
                update_markdown_note(note_path, project_name, event)

                if args.json:
                    print(json.dumps(event.to_dict(), indent=2))
                else:
                    print(f"Checkpoint #{event.revision} recorded for '{project_name}' (`{event.id[:8]}`).")
                return 0

        except TimeoutError as te:
            print(f"Error: Lock acquisition timed out: {te}", file=sys.stderr)
            return 1
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(0.1)
                continue
            print(f"Error executing checkpoint: {e}", file=sys.stderr)
            return 1

    return 1


# -----------------------------------------------------------------------------
# COMMAND: history
# -----------------------------------------------------------------------------
def cmd_history(args: argparse.Namespace) -> int:
    project_name, repo_path, note_path, history_path, config = resolve_project_config(
        repo_override=args.repo,
        note_override=args.note_file,
        history_override=args.history_file,
    )

    limit = args.limit if args.limit is not None else 10
    events = read_recent_events(history_path, limit)

    if not args.chronological:
        events = list(reversed(events))

    if args.format == "json":
        print(json.dumps([e.to_dict() for e in events], indent=2))
        return 0

    # Markdown format
    if not events:
        print(f"No history recorded for project '{project_name}'.")
        return 0

    print(f"### History for {project_name} (Showing {len(events)} checkpoints)\n")
    for ev in events:
        time_str = ev.timestamp
        br_cm = []
        if ev.branch:
            br_cm.append(f"branch: `{ev.branch}`")
        if ev.commit_range:
            br_cm.append(f"commit: `{ev.commit_range}`")
        git_info = f" ({', '.join(br_cm)})" if br_cm else ""
        source_info = f" [{ev.source}]" if ev.source != "local" else ""
        print(f"- **#{ev.revision}** (`{ev.id[:8]}`) at {time_str}{source_info}{git_info}")
        print(f"  **Summary**: {ev.summary}")
        if ev.actions:
            print(f"  **Actions**: {'; '.join(ev.actions)}")
        if ev.verification:
            print(f"  **Verification**: {ev.verification}")
        if ev.blockers:
            print(f"  **Blockers**: {ev.blockers}")
        if ev.next_step:
            print(f"  **Next**: {ev.next_step}")
        print()

    return 0


# -----------------------------------------------------------------------------
# COMMAND: lint
# -----------------------------------------------------------------------------
def cmd_lint(args: argparse.Namespace) -> int:
    project_name, repo_path, note_path, history_path, config = resolve_project_config(
        repo_override=args.repo,
        note_override=args.note_file,
        history_override=args.history_file,
    )

    cloud_branch = args.cloud_branch or config.get("cloud_branch")
    cloud_task_ref = args.cloud_task_ref or config.get("cloud_task_ref")
    messenger_cmd = args.cloud_messenger_cmd or config.get("cloud_messenger_cmd")

    if not cloud_branch:
        curr_branch = get_git_branch(repo_path)
        cloud_branch = f"origin/{curr_branch}" if curr_branch else "origin/main"

    if args.fetch:
        try:
            subprocess.run(
                ["git", "fetch", "--quiet"],
                cwd=str(repo_path),
                capture_output=True,
                check=False,
            )
        except Exception:
            pass

    events = read_history_events(history_path)
    represented_commits = set()
    for ev in events:
        if ev.commit_range:
            for part in re.split(r"[\s\.,]+", ev.commit_range):
                if part.strip():
                    represented_commits.add(part.strip())

    try:
        git_cmd = ["git", "log", "--oneline", "-n", str(args.max_commits or 30), cloud_branch]
        res = subprocess.run(
            git_cmd,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            git_cmd = ["git", "log", "--oneline", "-n", str(args.max_commits or 30), "HEAD"]
            res = subprocess.run(
                git_cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                print(f"Lint: Unable to inspect git log on {repo_path}: {res.stderr.strip()}", file=sys.stderr)
                return 1
    except Exception as e:
        print(f"Lint error running git log: {e}", file=sys.stderr)
        return 1

    commit_lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    untracked_commits = []
    for line in commit_lines:
        commit_hash = line.split()[0]
        if commit_hash not in represented_commits and not any(commit_hash.startswith(rc) or rc.startswith(commit_hash) for rc in represented_commits):
            untracked_commits.append(line)

    if not untracked_commits:
        if args.json:
            print(json.dumps({"status": "ok", "untracked_commits": 0, "message": "All commits tracked."}))
        else:
            print("Lint: All recent Git commits are represented in the tracker.")
        return 0

    print(f"Lint: Found {len(untracked_commits)} untracked commit(s) on {cloud_branch}.")

    cloud_report: Optional[Dict[str, Any]] = None
    if messenger_cmd and cloud_task_ref:
        try:
            cmd = messenger_cmd.replace("{task_ref}", cloud_task_ref).replace("{branch}", cloud_branch)
            m_res = subprocess.run(
                cmd,
                shell=True,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if m_res.returncode == 0 and m_res.stdout.strip():
                try:
                    cloud_report = json.loads(m_res.stdout)
                except Exception:
                    cloud_report = {"summary": m_res.stdout.strip()}
        except Exception:
            cloud_report = None

    commit_range_str = f"{untracked_commits[-1].split()[0]}..{untracked_commits[0].split()[0]}" if len(untracked_commits) > 1 else untracked_commits[0].split()[0]

    if cloud_report and isinstance(cloud_report, dict) and cloud_report.get("summary"):
        summary = cloud_report["summary"]
        actions = cloud_report.get("actions", [])
        verification = cloud_report.get("verification")
        source = "cloud"
        missing_context = False
    else:
        commit_subjects = "; ".join([c.split(" ", 1)[1] for c in untracked_commits[:5]])
        summary = f"Git commits on {cloud_branch}: {commit_subjects}"
        actions = [f"Commit {c}" for c in untracked_commits[:5]]
        verification = None
        source = "git-evidence"
        missing_context = True

    if args.dry_run:
        print(f"[Dry Run] Would import checkpoint for {commit_range_str} (source: {source}, missing_narrative_context: {missing_context})")
        return 0

    lock_file = history_path.parent / (history_path.name + ".lock")
    with FileLock(lock_file, timeout=5.0):
        events = read_history_events(history_path)
        last_rev = events[-1].revision if events else 0
        event = CheckpointEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            revision=last_rev + 1,
            summary=summary,
            harness="cloud-lint",
            actions=actions,
            branch=cloud_branch,
            commit_range=commit_range_str,
            verification=verification,
            source=source,
            task_ref=cloud_task_ref,
            missing_narrative_context=missing_context,
        )
        append_history_event(history_path, event)
        update_markdown_note(note_path, project_name, event)

    print(f"Lint: Imported checkpoint #{event.revision} ({source}) for range {commit_range_str}.")
    return 0


# -----------------------------------------------------------------------------
# COMMAND: doctor
# -----------------------------------------------------------------------------
def cmd_doctor(args: argparse.Namespace) -> int:
    project_name, repo_path, note_path, history_path, config = resolve_project_config(
        repo_override=args.repo,
        note_override=args.note_file,
        history_override=args.history_file,
    )

    issues: List[Dict[str, str]] = []
    checks: List[Dict[str, Any]] = []

    def check(name: str, passed: bool, message: str, repair: Optional[str] = None):
        status = "PASS" if passed else "FAIL"
        checks.append({"name": name, "status": status, "message": message, "repair": repair})
        if not passed:
            issues.append({"check": name, "message": message, "repair": repair or "No automated repair available."})

    registry = load_registry()
    repo_key = str(repo_path)
    is_registered = repo_key in registry
    check(
        "Registry Resolution",
        is_registered,
        f"Repo '{repo_path}' is registered in {get_registry_path()}" if is_registered else f"Repo '{repo_path}' not found in registry",
        f"Run 'tracker.py init --repo {repo_path}' to register." if not is_registered else None,
    )

    history_exists = history_path.exists()
    history_writable = os.access(history_path, os.W_OK) if history_exists else os.access(history_path.parent, os.W_OK)
    check(
        "History File Accessibility",
        history_exists and history_writable,
        f"History log {history_path} exists and is writable" if history_exists and history_writable else f"History file {history_path} missing or not writable",
        f"Create or fix permissions for {history_path}",
    )

    note_exists = note_path.exists()
    note_writable = os.access(note_path, os.W_OK) if note_exists else os.access(note_path.parent, os.W_OK)
    check(
        "Note File Accessibility",
        note_exists and note_writable,
        f"Note file {note_path} exists and is writable" if note_exists and note_writable else f"Note file {note_path} missing or not writable",
        f"Create or fix permissions for {note_path}",
    )

    lock_file = history_path.parent / (history_path.name + ".lock")
    lock_passed = True
    lock_msg = "Lock mechanism functional"
    try:
        with FileLock(lock_file, timeout=1.0):
            pass
    except Exception as e:
        lock_passed = False
        lock_msg = f"Lock test failed: {e}"
    check(
        "Locking Mechanism",
        lock_passed,
        lock_msg,
        f"Inspect and remove stale lockfile if orphaned: {lock_file}" if not lock_passed else None,
    )

    jsonl_valid = True
    duplicate_ids = False
    events: List[CheckpointEvent] = []
    seen_ids = set()
    dup_id_list = []
    if history_exists:
        with open(history_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    d = json.loads(raw)
                    if "id" not in d or "revision" not in d or "summary" not in d:
                        jsonl_valid = False
                        break
                    eid = d["id"]
                    if eid in seen_ids:
                        duplicate_ids = True
                        dup_id_list.append(eid)
                    seen_ids.add(eid)
                    events.append(CheckpointEvent.from_dict(d))
                except Exception:
                    jsonl_valid = False
                    break

    check(
        "JSONL Validity",
        jsonl_valid,
        f"All lines in {history_path.name} are valid JSON matching schema" if jsonl_valid else f"Malformed line detected in {history_path}",
        f"Inspect {history_path} manually. Never delete history lines blindly; repair broken JSON syntax.",
    )

    check(
        "Unique Event IDs",
        not duplicate_ids,
        "All event IDs are unique" if not duplicate_ids else f"Duplicate event IDs found: {', '.join(dup_id_list[:3])}",
        f"Check history.jsonl for duplicate checkpoint records.",
    )

    revision_consistent = True
    rev_msg = "Note file revision matches history"
    if events and note_exists:
        latest_event = events[-1]
        note_content = note_path.read_text(encoding="utf-8")
        if f"Revision**: #{latest_event.revision}" not in note_content and f"#{latest_event.revision}" not in note_content:
            revision_consistent = False
            rev_msg = f"Note file generated block does not reference latest event revision #{latest_event.revision}"

    check(
        "Summary Revision Consistency",
        revision_consistent,
        rev_msg,
        f"Run 'tracker.py checkpoint --summary \"resync\"' or execute a new checkpoint to refresh the Markdown summary note.",
    )

    in_git = (repo_path / ".git").exists() or get_git_repo_root(repo_path) is not None
    check(
        "Git Repository Configuration",
        in_git,
        f"Repository at {repo_path} has valid Git context" if in_git else f"No Git repository found at {repo_path}",
        "Run 'git init' in the repository or configure a non-git directory.",
    )

    if args.json:
        print(json.dumps({
            "project_name": project_name,
            "status": "healthy" if not issues else "issues_found",
            "checks": checks,
            "issues": issues,
        }, indent=2))
    else:
        print(f"Doctor Health Report for '{project_name}':\n")
        for c in checks:
            badge = "[PASS]" if c["status"] == "PASS" else "[FAIL]"
            print(f"  {badge:<6} {c['name']}: {c['message']}")
        print()
        if issues:
            print(f"⚠️ Found {len(issues)} issue(s). Recommended repairs (non-destructive):\n")
            for i, iss in enumerate(issues, 1):
                print(f"  {i}. {iss['check']}: {iss['message']}")
                print(f"     Repair: {iss['repair']}\n")
            return 1
        else:
            print("✅ All project tracker diagnostics passed. System healthy.")
            return 0

    return 1 if issues else 0


# -----------------------------------------------------------------------------
# Main Entrypoint
# -----------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tracker",
        description="Lightweight Project Tracker - Plaintext progress tracker for AI agents & developers",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_paths(p):
        p.add_argument("--repo", help="Path to repository root")
        p.add_argument("--note-file", help="Path to markdown note file")
        p.add_argument("--history-file", help="Path to history.jsonl")
        p.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    # init
    p_init = subparsers.add_parser("init", help="Initialize or update tracker for a repository")
    p_init.add_argument("--repo", help="Path to repository root")
    p_init.add_argument("--name", help="Project name")
    p_init.add_argument("--notes-root", help="Base notes directory (e.g. Obsidian vault)")
    p_init.add_argument("--note-file", help="Path to markdown note file")
    p_init.add_argument("--history-file", help="Path to history.jsonl")
    p_init.add_argument("--cloud-branch", help="Cloud branch to track for linting")
    p_init.add_argument("--cloud-task-ref", help="Cloud task reference ID")
    p_init.add_argument("--cloud-messenger-cmd", help="Command to query cloud task")
    p_init.add_argument("--harness", help="Harness identifier")
    p_init.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    p_init.set_defaults(func=cmd_init)

    # checkpoint
    p_chk = subparsers.add_parser("checkpoint", help="Record a new progress checkpoint")
    add_common_paths(p_chk)
    p_chk.add_argument("--summary", required=True, help="Concise summary of progress")
    p_chk.add_argument("--action", action="append", help="Individual action item (can repeat)")
    p_chk.add_argument("--actions", help="Comma-delimited or semicolon-delimited action list")
    p_chk.add_argument("--harness", help="Agent harness identifier")
    p_chk.add_argument("--branch", help="Git branch")
    p_chk.add_argument("--commit", help="Git commit hash")
    p_chk.add_argument("--commit-range", help="Git commit range")
    p_chk.add_argument("--verification", help="Verification command / test results")
    p_chk.add_argument("--blockers", help="Current blockers if any")
    p_chk.add_argument("--next-step", help="Immediate next step")
    p_chk.add_argument("--source", choices=["local", "cloud", "git-evidence"], default="local", help="Origin of checkpoint")
    p_chk.add_argument("--task-ref", help="Cloud task ref")
    p_chk.add_argument("--id", help="Explicit event ID (optional)")
    p_chk.add_argument("--expected-revision", type=int, help="Revision number expected before write")
    p_chk.add_argument("--lock-timeout", type=float, default=5.0, help="Lock timeout in seconds")
    p_chk.add_argument("--missing-narrative-context", action="store_true", help="Flag as git-evidence without agent narrative")
    p_chk.set_defaults(func=cmd_checkpoint)

    # history
    p_hist = subparsers.add_parser("history", help="Show recent checkpoints")
    add_common_paths(p_hist)
    p_hist.add_argument("--limit", "-n", type=int, default=10, help="Number of records to return")
    p_hist.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format")
    p_hist.add_argument("--chronological", action="store_true", help="Order oldest first instead of newest first")
    p_hist.set_defaults(func=cmd_history)

    # lint
    p_lint = subparsers.add_parser("lint", help="Lint cloud branches against Git commits and tracker history")
    add_common_paths(p_lint)
    p_lint.add_argument("--cloud-branch", help="Remote cloud branch override")
    p_lint.add_argument("--cloud-task-ref", help="Cloud task ref override")
    p_lint.add_argument("--cloud-messenger-cmd", help="Command to query cloud task")
    p_lint.add_argument("--no-fetch", dest="fetch", action="store_false", help="Skip git fetch")
    p_lint.add_argument("--max-commits", type=int, default=30, help="Max commits to inspect")
    p_lint.add_argument("--dry-run", action="store_true", help="Show changes without writing checkpoints")
    p_lint.set_defaults(func=cmd_lint, fetch=True)

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run diagnostic health checks")
    add_common_paths(p_doc)
    p_doc.set_defaults(func=cmd_doctor)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        ret = args.func(args)
        sys.exit(ret)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

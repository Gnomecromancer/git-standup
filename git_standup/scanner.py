"""Scan directories for git repos and collect recent commits."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Commit:
    hash: str
    author: str
    email: str
    date: datetime
    subject: str
    repo: Path

    @property
    def repo_name(self) -> str:
        return self.repo.name


def _git(*args, cwd: Path) -> str | None:
    """Run a git command and return stdout, or None on error."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def find_repos(root: Path, max_depth: int = 3) -> list[Path]:
    """Find all git repositories under root up to max_depth levels deep."""
    repos: list[Path] = []
    skip = {".venv", "venv", "node_modules", "__pycache__", ".git"}

    def _walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        if (path / ".git").is_dir():
            repos.append(path)
            return  # Don't recurse into nested git repos
        try:
            for child in path.iterdir():
                try:
                    is_dir = child.is_dir()
                except OSError:
                    continue  # socket files, inaccessible paths (e.g. Docker engine.sock)
                if is_dir and child.name not in skip:
                    _walk(child, depth + 1)
        except (PermissionError, OSError):
            pass

    _walk(root, 0)
    return repos


def get_commits(
    repo: Path,
    since: str,
    until: str | None = None,
    author: str | None = None,
    all_branches: bool = False,
) -> list[Commit]:
    """Fetch commits in a repo matching the given filters.

    Args:
        repo: Path to the repository root.
        since: Git date string, e.g. "1 day ago", "2024-01-01".
        until: Git date string for upper bound (default: now).
        author: Filter by author name or email pattern.
        all_branches: If True, include all branches (not just current).
    """
    sep = "\x1f"  # ASCII unit separator — safe in subprocess args on all platforms
    fmt = f"%H{sep}%an{sep}%ae{sep}%aI{sep}%s"

    args = ["log", f"--format={fmt}", f"--since={since}"]
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")
    if all_branches:
        args.append("--all")

    output = _git(*args, cwd=repo)
    if not output:
        return []

    commits: list[Commit] = []
    for line in output.splitlines():
        parts = line.split(sep)
        if len(parts) != 5:
            continue
        hash_, an, ae, date_str, subject = parts
        try:
            date = datetime.fromisoformat(date_str)
        except ValueError:
            continue
        commits.append(
            Commit(
                hash=hash_[:8],
                author=an,
                email=ae,
                date=date,
                subject=subject,
                repo=repo,
            )
        )

    return commits


def get_repo_current_branch(repo: Path) -> str | None:
    return _git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo)


def guess_author(repo: Path | None = None) -> tuple[str | None, str | None]:
    """Return (name, email) from git config."""
    cwd = repo or Path.cwd()
    name = _git("config", "user.name", cwd=cwd)
    email = _git("config", "user.email", cwd=cwd)
    return name, email

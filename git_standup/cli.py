"""CLI for git-standup."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from .scanner import find_repos, get_commits, get_repo_current_branch, guess_author


# ── ANSI helpers ─────────────────────────────────────────────────────────────

def _bold(s: str) -> str:
    return f"\033[1m{s}\033[0m"


def _cyan(s: str) -> str:
    return f"\033[36m{s}\033[0m"


def _yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _dim(s: str) -> str:
    return f"\033[2m{s}\033[0m"


def _strip_color(s: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", s)


# ── Date helpers ──────────────────────────────────────────────────────────────

_DAYS = {
    "today": 0,
    "yesterday": 1,
    "week": 6,
    "2days": 2,
    "3days": 3,
}


def _since_string(days: int) -> str:
    """Return a git-compatible 'since' string for N days ago."""
    if days == 0:
        # Midnight today in local time
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.strftime("%Y-%m-%d %H:%M:%S")
    return f"{days} days ago"


def _format_date(dt: datetime) -> str:
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    required=False,
)
@click.option(
    "--days", "-d",
    default=1,
    show_default=True,
    help="Number of days to look back.",
)
@click.option(
    "--since",
    default=None,
    metavar="DATE",
    help="Custom 'since' date (overrides --days). Any git date format.",
)
@click.option(
    "--author", "-a",
    default=None,
    metavar="NAME_OR_EMAIL",
    help="Filter by author. Defaults to current git user.",
)
@click.option(
    "--all-authors", is_flag=True, default=False,
    help="Show commits from all authors.",
)
@click.option(
    "--all-branches", is_flag=True, default=False,
    help="Include commits from all branches (default: current branch only).",
)
@click.option(
    "--depth", default=3, show_default=True,
    help="Max directory depth to scan for repos.",
)
@click.option(
    "--no-color", is_flag=True, default=False,
    help="Disable ANSI color output.",
)
@click.option(
    "--compact", "-c", is_flag=True, default=False,
    help="Compact output — one line per commit, no repo headers.",
)
@click.version_option(package_name="git-standup")
def main(
    directory: Path,
    days: int,
    since: str | None,
    author: str | None,
    all_authors: bool,
    all_branches: bool,
    depth: int,
    no_color: bool,
    compact: bool,
) -> None:
    """Show your git commits across multiple repos for a daily standup.

    \b
    Examples:
      git standup                     # today's commits by you
      git standup --days 3            # last 3 days
      git standup ~/projects          # scan a specific directory
      git standup --all-authors       # everyone's commits
      git standup --since "last week" # custom date range
    """
    if no_color:
        global _bold, _cyan, _yellow, _green, _dim
        _bold = _cyan = _yellow = _green = _dim = lambda s: s  # noqa: E731

    # Resolve author filter
    effective_author: str | None
    if all_authors:
        effective_author = None
    elif author:
        effective_author = author
    else:
        name, email = guess_author(directory)
        if not name and not email:
            click.echo(
                "Could not determine git user. Use --author or --all-authors.",
                err=True,
            )
            sys.exit(1)
        effective_author = email or name

    # Resolve since
    since_str = since if since else _since_string(days)

    # Discover repos
    repos = find_repos(directory, max_depth=depth)
    if not repos:
        click.echo(f"No git repositories found under {directory}", err=True)
        sys.exit(1)

    # Collect commits grouped by repo
    total = 0
    output_lines: list[str] = []

    for repo in sorted(repos, key=lambda p: p.name.lower()):
        commits = get_commits(
            repo,
            since=since_str,
            author=effective_author,
            all_branches=all_branches,
        )
        if not commits:
            continue

        total += len(commits)

        if compact:
            for c in commits:
                line = (
                    f"{_dim(c.hash)}  "
                    f"{_cyan(c.repo_name):<20}  "
                    f"{_dim(_format_date(c.date))}  "
                    f"{c.subject}"
                )
                output_lines.append(line)
        else:
            branch = get_repo_current_branch(repo) or "HEAD"
            header = (
                f"{_bold(_cyan(repo.name))}  "
                f"{_dim(f'({branch})')}  "
                f"{_dim(str(repo))}"
            )
            output_lines.append(header)
            for c in commits:
                output_lines.append(
                    f"  {_dim(c.hash)}  "
                    f"{_yellow(_format_date(c.date))}  "
                    f"{c.subject}"
                    + (f"  {_dim(c.author)}" if all_authors else "")
                )
            output_lines.append("")

    if not output_lines:
        click.echo(_dim("No commits found."))
        return

    # Summary header
    period = f"last {days} day{'s' if days != 1 else ''}" if not since else f"since {since}"
    who = "all authors" if all_authors else (author or effective_author or "you")
    click.echo(
        _bold(f"Standup — {period} — {who}") + "\n" + "─" * 60
    )

    for line in output_lines:
        click.echo(line)

    click.echo(f"\n{_green(str(total))} commit{'s' if total != 1 else ''} across {len(repos)} repo{'s' if len(repos) != 1 else ''} scanned.")

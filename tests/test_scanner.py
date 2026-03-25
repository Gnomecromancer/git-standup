"""Tests for git_standup.scanner."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from git_standup.scanner import (
    find_repos,
    get_commits,
    get_repo_current_branch,
    guess_author,
    Commit,
)


# ── find_repos ────────────────────────────────────────────────────────────────

def test_find_repos_single(tmp_path):
    (tmp_path / ".git").mkdir()
    repos = find_repos(tmp_path)
    assert tmp_path in repos


def test_find_repos_nested(tmp_path):
    repo_a = tmp_path / "a"
    repo_a.mkdir()
    (repo_a / ".git").mkdir()
    repo_b = tmp_path / "sub" / "b"
    repo_b.mkdir(parents=True)
    (repo_b / ".git").mkdir()

    repos = find_repos(tmp_path)
    assert repo_a in repos
    assert repo_b in repos


def test_find_repos_skips_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / ".git").mkdir()
    repos = find_repos(tmp_path)
    assert venv not in repos


def test_find_repos_does_not_recurse_into_nested_git(tmp_path):
    """A git repo inside another git repo should not both be returned — just the outer."""
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / ".git").mkdir()
    inner = outer / "inner"
    inner.mkdir()
    (inner / ".git").mkdir()

    repos = find_repos(tmp_path)
    # outer found, inner not found (we stop descending once we hit a .git)
    assert outer in repos
    assert inner not in repos


def test_find_repos_respects_depth(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / ".git").mkdir()
    repos = find_repos(tmp_path, max_depth=2)
    assert deep not in repos

    repos = find_repos(tmp_path, max_depth=5)
    assert deep in repos


# ── get_commits ───────────────────────────────────────────────────────────────

_SEP = "\x1f"
_SAMPLE_LOG = (
    f"abc12345{_SEP}Alice{_SEP}alice@example.com{_SEP}2024-01-15T10:30:00+00:00{_SEP}Add feature X\n"
    f"def67890{_SEP}Alice{_SEP}alice@example.com{_SEP}2024-01-15T09:00:00+00:00{_SEP}Fix bug Y"
)


def test_get_commits_parses_output(tmp_path):
    with patch("git_standup.scanner._git", return_value=_SAMPLE_LOG):
        commits = get_commits(tmp_path, since="1 day ago")

    assert len(commits) == 2
    assert commits[0].hash == "abc12345"
    assert commits[0].author == "Alice"
    assert commits[0].email == "alice@example.com"
    assert commits[0].subject == "Add feature X"
    assert commits[0].repo == tmp_path


def test_get_commits_empty_output(tmp_path):
    with patch("git_standup.scanner._git", return_value=None):
        commits = get_commits(tmp_path, since="1 day ago")
    assert commits == []


def test_get_commits_passes_author_flag(tmp_path):
    with patch("git_standup.scanner._git", return_value=None) as mock_git:
        get_commits(tmp_path, since="1 day ago", author="alice@example.com")
    call_args = mock_git.call_args[0]
    assert any("--author=alice@example.com" in a for a in call_args)


def test_get_commits_passes_all_branches_flag(tmp_path):
    with patch("git_standup.scanner._git", return_value=None) as mock_git:
        get_commits(tmp_path, since="1 day ago", all_branches=True)
    call_args = mock_git.call_args[0]
    assert "--all" in call_args


def test_get_commits_repo_name(tmp_path):
    named = tmp_path / "my-project"
    named.mkdir()
    with patch("git_standup.scanner._git", return_value=_SAMPLE_LOG):
        commits = get_commits(named, since="1 day ago")
    assert commits[0].repo_name == "my-project"


def test_get_commits_skips_malformed_lines(tmp_path):
    bad_output = "not\x00enough\x00parts"
    with patch("git_standup.scanner._git", return_value=bad_output):
        commits = get_commits(tmp_path, since="1 day ago")
    assert commits == []


# ── get_repo_current_branch ───────────────────────────────────────────────────

def test_get_repo_current_branch(tmp_path):
    with patch("git_standup.scanner._git", return_value="main"):
        branch = get_repo_current_branch(tmp_path)
    assert branch == "main"


# ── guess_author ──────────────────────────────────────────────────────────────

def test_guess_author(tmp_path):
    with patch("git_standup.scanner._git", side_effect=["Alice Smith", "alice@example.com"]):
        name, email = guess_author(tmp_path)
    assert name == "Alice Smith"
    assert email == "alice@example.com"

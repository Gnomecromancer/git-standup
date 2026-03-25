"""Tests for git_standup CLI."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from git_standup.cli import main
from git_standup.scanner import Commit


def _commit(subject="Add feature", repo_name="myrepo", author="Alice", email="alice@example.com"):
    repo = Path(f"/tmp/{repo_name}")
    return Commit(
        hash="abc12345",
        author=author,
        email=email,
        date=datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc),
        subject=subject,
        repo=repo,
    )


def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.2.1" in result.output


def test_no_repos_found(tmp_path):
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=[]):
        result = runner.invoke(main, [str(tmp_path)])
    assert result.exit_code == 1


def test_no_commits_found(tmp_path):
    runner = CliRunner()
    repos = [tmp_path / "repo1"]
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.get_commits", return_value=[]), \
         patch("git_standup.cli.guess_author", return_value=("Alice", "alice@example.com")):
        result = runner.invoke(main, [str(tmp_path), "--no-color"])
    assert result.exit_code == 0
    assert "No commits found" in result.output


def test_shows_commits(tmp_path):
    commits = [_commit("Fix the bug")]
    repos = [tmp_path / "myrepo"]
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.get_commits", return_value=commits), \
         patch("git_standup.cli.get_repo_current_branch", return_value="main"), \
         patch("git_standup.cli.guess_author", return_value=("Alice", "alice@example.com")):
        result = runner.invoke(main, [str(tmp_path), "--no-color"])
    assert result.exit_code == 0
    assert "Fix the bug" in result.output
    assert "1 commit" in result.output


def test_compact_output(tmp_path):
    commits = [_commit("Fix the bug")]
    repos = [tmp_path / "myrepo"]
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.get_commits", return_value=commits), \
         patch("git_standup.cli.guess_author", return_value=("Alice", "alice@example.com")):
        result = runner.invoke(main, [str(tmp_path), "--compact", "--no-color"])
    assert "Fix the bug" in result.output
    # In compact mode there should be no repo header lines
    assert "main" not in result.output


def test_all_authors_removes_filter(tmp_path):
    repos = [tmp_path / "repo1"]
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.get_commits", return_value=[]) as mock_commits, \
         patch("git_standup.cli.guess_author", return_value=("Alice", "alice@example.com")):
        result = runner.invoke(main, [str(tmp_path), "--all-authors", "--no-color"])
    # author= should be None
    call_kwargs = mock_commits.call_args
    assert call_kwargs.kwargs.get("author") is None


def test_since_overrides_days(tmp_path):
    repos = [tmp_path / "repo1"]
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.get_commits", return_value=[]) as mock_commits, \
         patch("git_standup.cli.guess_author", return_value=("Alice", "alice@example.com")):
        runner.invoke(main, [str(tmp_path), "--since", "last week", "--no-color"])
    call_kwargs = mock_commits.call_args
    assert call_kwargs.kwargs.get("since") == "last week"


def test_no_git_user_exits_nonzero(tmp_path):
    repos = [tmp_path / "repo1"]
    runner = CliRunner()
    with patch("git_standup.cli.find_repos", return_value=repos), \
         patch("git_standup.cli.guess_author", return_value=(None, None)):
        result = runner.invoke(main, [str(tmp_path), "--no-color"])
    assert result.exit_code == 1

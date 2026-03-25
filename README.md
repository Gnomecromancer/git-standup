# git-standup

Show what you (or your team) committed across all git repos in a directory — perfect for daily standups.

## Install

```bash
pip install git-standup
```

## Usage

```bash
# Show today's commits by you (scans current directory)
git-standup

# Show the last 3 days
git-standup --days 3

# Scan a specific directory
git-standup ~/projects

# Show commits from everyone
git-standup --all-authors

# Custom date range
git-standup --since "last monday"

# Compact one-line-per-commit output
git-standup --compact

# Filter by a specific author
git-standup --author "alice@example.com"
```

## Example output

```
Standup — last 1 day — alice@example.com
────────────────────────────────────────────────────────────
api-server  (main)  /home/alice/projects/api-server
  a1b2c3d4  2024-01-15 10:30  Add rate limiting to auth endpoints
  e5f6a7b8  2024-01-15 09:15  Fix token expiry bug

frontend  (feature/auth)  /home/alice/projects/frontend
  c9d0e1f2  2024-01-15 11:45  Update login form validation

3 commits across 12 repos scanned.
```

## Options

| Option | Description |
|--------|-------------|
| `--days N` | Look back N days (default: 1) |
| `--since DATE` | Custom git date string (e.g. `"last week"`, `"2024-01-01"`) |
| `--author NAME` | Filter by author name or email |
| `--all-authors` | Show commits from all authors |
| `--all-branches` | Include commits from all branches |
| `--depth N` | Max directory depth to scan (default: 3) |
| `--compact` | One line per commit, no repo headers |
| `--no-color` | Disable ANSI color output |

Exit code is `0` when commits are found, same when none are found. The tool never exits non-zero on "no commits" — only on configuration errors.

## License

MIT

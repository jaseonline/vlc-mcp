# Stack: Python with uv

| File | Merge into |
| --- | --- |
| `gitignore` | Append to `.gitignore` |
| `CLAUDE.commands.md` | The Commands section of `CLAUDE.md` |
| `settings.hooks.json` | Add the `PostToolUse` block to `hooks` in `.claude/settings.json` |
| `dependabot.yml` | Append under `updates:` in `.github/dependabot.yml` |
| `pyproject.toml` | Copy to the repo root; replace placeholders |

Layout: `src/<package_name>/` (src layout) and `tests/`. For single-file tools use PEP 723 inline deps and `uv run script.py` instead of a `pyproject.toml`, and say so in CLAUDE.md.

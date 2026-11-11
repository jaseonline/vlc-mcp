# Using this template

Delete this file and `stacks/` once the steps below are done.

## New repo

1. **Create:** `gh repo create jaseonline/<name> --template jaseonline/repo-template --public --clone` (or `--private`).
2. **Replace placeholders** everywhere: `{{PROJECT_NAME}}`, `{{DESCRIPTION}}`, `{{YEAR}}`. Find them with `git grep -n '{{'`.
3. **Merge one stack** from `stacks/` (each has a `README.md` listing its pieces):
   - append its `gitignore` to `.gitignore`
   - merge its `CLAUDE.commands.md` into the Commands section of `CLAUDE.md`
   - merge its `settings.hooks.json` into `.claude/settings.json`
   - append its `dependabot.yml` entry to `.github/dependabot.yml`
   - copy any stub files it lists
4. **Fill in CLAUDE.md** (architecture rules, gotchas, versioning) and the SECURITY.md controls, or delete sections that don't apply.
5. **Claude GitHub App:** standard on every repo. Install it once for all repositories at <https://github.com/apps/claude/installations/new> (or add this repo if it's limited to selected ones). The Claude workflows use its token, so commits and branches Claude pushes trigger CI, which `GITHUB_TOKEN` pushes don't.
6. **Add repo secrets** for the workflows you keep:

   | Workflow | Secrets |
   | --- | --- |
   | `claude.yml`, `claude-code-review.yml` | `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`, or `/install-github-app` in Claude Code) |
   | `backup.yml` | `CF_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` |
   | `super-linter.yml` | none (`GITHUB_TOKEN` is automatic) |

7. **Delete what doesn't apply:** empty `src/` or `tests/`, unused workflows, issue templates on a private repo.
8. Delete `stacks/` and this file, then commit.

## Existing repo

An existing repo doesn't have the skill yet, so install it once at user level:

```sh
cp -r .claude/skills/standardise-repo ~/.claude/skills/
```

Then open Claude Code in the existing repo and run `/standardise-repo`. It compares the repo with this template, reports the gaps, and changes nothing until you approve.

## Template conventions

- **Licence:** MIT, `Copyright (c) {{YEAR}} jaseonline`. Forks keep their upstream licence.
- **Action pinning:** every `uses:` is pinned to a full commit SHA with the version as a trailing comment (`actions/checkout@<sha> # v7.0.1`). Tags can be moved, SHAs can't, and super-linter's zizmor check fails on unpinned actions. Dependabot updates the SHA and the comment together.
- **`.claude/`:** `settings.json`, `hooks/`, `skills/`, `agents/` and `commands/` are tracked; `settings.local.json` and other local state are ignored.
- **Line endings:** LF everywhere except `*.ps1`, `*.cmd` and `*.bat` (CRLF), so hooks run under Git Bash on Windows and on CI runners.

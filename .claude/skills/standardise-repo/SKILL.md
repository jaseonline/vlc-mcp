---
name: standardise-repo
description: Compare an existing repository with the jaseonline/repo-template standard (docs, licence, dotfiles, .claude config, CLAUDE.md shape, GitHub workflows) and produce a gap report, then apply only the changes the user approves. Use when asked to standardise, align, tidy up or bring a repo in line with the template.
disable-model-invocation: true
---

# Standardise repo

Align the current repo (or the path in `$ARGUMENTS`) with `jaseonline/repo-template`. **Report first, change nothing until approved.**

## 1. Get the reference

Use a local checkout if one exists (`D:\Projects\active\repo-template`), otherwise `gh repo clone jaseonline/repo-template "$TMP/repo-template" -- --depth 1`. Note its HEAD commit in the report.

## 2. Profile the target

- `git remote -v`: if the owner is not `jaseonline`, it's a fork or third-party clone. **Stop and say so**: forks keep upstream conventions; offer only `.claude/` and `CLAUDE.md` changes.
- Visibility: `gh repo view --json visibility`. Private repos use the **private profile** below.
- Deploys on push? Check CLAUDE.md, README and the Workers Builds / release workflows. If a push to `main` deploys, say so at the top of the report, because it shapes how changes are committed (see step 5).
- Stack: `pyproject.toml`/`uv.lock` → python-uv; `package.json` → node-ts; `wrangler.jsonc`/`wrangler.toml` → cf-worker (can combine with node-ts).
- Baseline: run the repo's own lint and tests **before** proposing anything, and note pre-existing failures. Super-linter v9 will surface them on the first push.
- Read the existing `CLAUDE.md`, `.claude/settings.json`, `.gitignore`, `.github/` and licence before judging them.

## 3. Check each item

| Area | Standard | Check |
| --- | --- | --- |
| README.md | Present; title, description, quick start, configuration, licence | Missing sections |
| LICENSE | MIT, `jaseonline`, current year | Missing / different. **Never change an existing licence**: flag it only |
| SECURITY.md | Template shape; advisory link points at this repo | Missing, or link points elsewhere |
| CONTRIBUTING.md, CHANGELOG.md | Present; CHANGELOG has `## Unreleased` | Missing |
| CLAUDE.md | Standard header line; Commands / Architecture rules / Gotchas / Versioning / Git sections | Missing sections, stale commands (verify they exist), pasted placeholders |
| .gitignore | Template base + stack fragment; `.claude/*` with `!` re-includes; `.remember/`; `.env*` with `!.env.example` | Stock templates for the wrong language; tracked files that should be ignored (`git ls-files -ci --exclude-standard`) |
| .gitattributes, .editorconfig | Present; LF default, CRLF for `*.ps1` | Missing, or `.sh` files with CRLF |
| .claude/settings.json | Deny rules for secrets + force-push; push-guard hook; stack hook | Missing hooks; secrets readable |
| .claude/hooks/push-guard.sh | Present; `DEPLOY_PATHS` set if the repo deploys on push | Missing, or no path filter on a deploy-on-push repo |
| .claude/skills/ | `release` present if the repo is versioned | Missing; check skill frontmatter is valid |
| .github/workflows | claude.yml, claude-code-review.yml, super-linter.yml, backup.yml | Missing; actions not SHA-pinned (`@<sha> # vX.Y.Z`) or behind the template's versions: copy the SHAs from the template's workflows |
| Claude GitHub App | Installed; Claude workflows use `claude_code_oauth_token`, not `anthropic_api_key` + `github_token` | Workflows using the API-key route. The App can't be checked from the CLI: ask the user to confirm it's installed |
| .github/dependabot.yml | `github-actions` + stack ecosystem with `cooldown: default-days: 7`; valid config | Missing, empty `package-ecosystem`, or pointed at `.venv`/`node_modules` |
| Issue / PR templates | YAML issue forms + PR template (public repos only) | Missing on public repo |
| Folder layout | `src/`, `tests/`, `docs/`, `scripts/` where they make sense | Report only. **Never move source files**: imports, build paths and deploy config depend on them |

### Private profile

Apply the full template to private repos too: Jason wants LICENSE (MIT) and SECURITY.md everywhere, so they're always in scope. Differences:

| Item | Private repo |
| --- | --- |
| SECURITY.md | GitHub private vulnerability reporting doesn't work on private repos. Keep the advisory link but add "while it's private, contact @jaseonline directly" |
| Issue forms, PR template, CONTRIBUTING.md | Optional: offer them, but mark them **Needs a decision**, not Missing |
| `claude.yml` | The OWNER-only check still applies (collaborators can comment) |

### Super-linter v9 checks that catch repos out

Check these up front so the first CI run is green:

- Hook scripts need the git exec bit (`git ls-files -s .claude/hooks/` shows `100755`; fix with `git update-index --chmod=+x`). Otherwise BASH_EXEC fails.
- Trivy ignores `FILTER_REGEX_EXCLUDE`. Public-by-design tokens (e.g. DID JWTs in `.well-known/`) need `.github/linters/trivy.yaml` with `scan.skip-dirs`; the template ships one.
- Biome scans the whole workspace, not just changed files, so pre-existing format/lint debt (SVGs without `<title>`, missing final newlines) fails the run.
- Working-copy CRLF (from `core.autocrlf`) can make local Biome fail even when the index is LF. Re-checkout the file after adding `.gitattributes`.

Also flag committed secrets or local state you notice (`.env`, `*.har`, `*.log`, `.wrangler/`), but don't rewrite history.

## 4. Report

One table: **Item | Status (OK / Missing / Drift / Conflict) | Proposed change | Risk**. Then group the proposals into:

- **Safe adds**: new files that don't exist yet.
- **Merges**: edits to existing files (show the diff you'd apply).
- **Needs a decision**: licence, folder moves, workflows that need new secrets, anything that changes deploy behaviour.

Wait for the user to pick which groups or items to apply.

## 5. Apply

- Merge, don't overwrite: keep repo-specific content in CLAUDE.md, .gitignore and settings.json; add the missing template parts around it.
- Fill placeholders from the repo (name from the remote, description from the existing README, year from the first commit).
- New workflows needing secrets: list the secrets and check with `gh secret list`.
  - Values come from Keeper record `9LXoL-ZWhZDI-V53hRZ3KQ` (`keeper get <uid> --format json`). Pipe each value into `gh secret set` with `jq -j` and never print it.
  - `CF_ACCOUNT_ID` isn't a field: derive it from the record's `host` (`https://<account>.r2.cloudflarestorage.com`).
  - Never ask the user to type a secret into the chat or at a `!` prompt.
- Run the repo's tests and lint after changes. Run `bash -n` on hook scripts and validate JSON/YAML.
- Stage and show `git diff --cached --stat`. Propose the subject `Align with repo-template` and wait for approval. Never push without approval.
- **Deploy-on-push repos:** batch the approved groups into as few local commits as possible, then push once. Each push is a production deploy. After it, run the repo's smoke-test skill (e.g. `/verify-live`) if it has one.
- After pushing, watch the Lint run (`gh run watch <id> --exit-status`) and fix findings before calling the repo aligned.

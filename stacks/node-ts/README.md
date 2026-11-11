# Stack: Node / TypeScript

| File | Merge into |
| --- | --- |
| `gitignore` | Append to `.gitignore` |
| `CLAUDE.commands.md` | The Commands section of `CLAUDE.md` |
| `settings.hooks.json` | Add the `PostToolUse` block to `hooks` in `.claude/settings.json` |
| `dependabot.yml` | Append under `updates:` in `.github/dependabot.yml` |
| `package.json` | Copy to the repo root; replace placeholders |

Biome is configured by the template's root `biome.json`, which super-linter also uses, so there's nothing extra to copy.

Add a `.nvmrc` with the Node major you target. Linting and formatting use Biome. If the repo already uses ESLint/Prettier, keep it and change the hook command to match.

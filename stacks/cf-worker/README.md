# Stack: Cloudflare Worker

Use with `node-ts` if the Worker has dependencies or a build step. A plain-JS Worker with no `package.json` needs only this stack.

| File | Merge into |
| --- | --- |
| `gitignore` | Append to `.gitignore` |
| `CLAUDE.gotchas.md` | The Gotchas section of `CLAUDE.md` |
| `wrangler.jsonc` | Copy to the repo root; replace placeholders |
| Push-guard | Set `DEPLOY_PATHS` in `.claude/hooks/push-guard.sh` (below) |

Workers Builds deploys on push to `main`, so push-guard is what stops an unreviewed production deploy. Check the build trigger in the Cloudflare dashboard (Worker → Settings → Build → Build watch paths):

- **Watch paths set** (only some paths deploy): set the filter to match them, so pushes of docs or scripts go through without asking. For example:

  ```sh
  DEPLOY_PATHS='^(worker/|src/|wrangler\.jsonc$)'
  ```

- **No watch paths** (every push deploys, as with a static site whose `src/` is the content): leave `DEPLOY_PATHS=''`, so every push to `main` asks. Batch commits locally and push once, since each push is a deploy.

Either way, say which one applies in CLAUDE.md's Gotchas.

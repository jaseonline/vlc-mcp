---
name: release
description: Cut a new version — bump the version everywhere it lives, move CHANGELOG Unreleased entries under it, run tests and the build, stage the changes and propose a commit. Never pushes or tags without approval.
disable-model-invocation: true
---

# Release

Release a new version. `$ARGUMENTS` is the new version (e.g. `1.4.0`) or `patch` / `minor` / `major`.

1. Read the **Versioning** section of `CLAUDE.md` to find every file that holds the version (e.g. `pyproject.toml`, `package.json`, `__init__.py`, a manifest). If the section is missing or still a placeholder, stop and ask where the version lives.
2. Read the current version from each file. If they differ, report it and ask which is the base.
3. Work out the new version (semver) and set it in **every** file from step 1.
4. In `CHANGELOG.md`, move the `## Unreleased` entries under `## <version> - <YYYY-MM-DD>` and leave an empty `## Unreleased` above it. If Unreleased is empty, stop and ask whether to release anyway.
5. Run the test and build commands from the **Commands** section of `CLAUDE.md`. Stop on any failure and report it; don't fix and retry silently.
6. Regenerate anything CLAUDE.md says must be regenerated with the version (lockfiles, manifests), using the documented command.
7. Stage the changed files and show `git diff --cached --stat` plus the CHANGELOG diff.
8. Propose the commit subject `Release <version>: <one-line summary>` and **wait for approval** before committing.
9. After the commit, offer (don't run) `git tag v<version>` and the push. The push-guard hook will still ask.

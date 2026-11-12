# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest release | ✅ Current |

Only the latest release receives security fixes. Update to the latest version before reporting issues found in older releases.

## Controls

| Layer | Control |
| --- | --- |
| Secrets | `VLC_HTTP_PASSWORD` is read from the environment and never committed. `.env*` is gitignored |
| Transport | Runs locally over stdio only; it opens no network port of its own |
| Access | Talks only to the VLC HTTP interface at `VLC_HTTP_HOST:VLC_HTTP_PORT` (default `localhost:8080`) |
| Logging | Logs go to stderr. Request URLs and parameters are logged; the password is not |

Residual risks:

- VLC's HTTP interface uses HTTP Basic auth over plain HTTP. Keep it bound to `localhost`.
- File paths are not confined to `ROOT_VIDEO_FOLDER`: absolute paths pass through, so a client can ask VLC to open any file the user can read.
- The `vlm` tool passes commands to VLC's VideoLAN Manager unfiltered.
- `show_video` runs the `mediainfo` executable found on `PATH`.

## Reporting a vulnerability

Please do **not** open public issues for security problems. Report privately instead:

- **GitHub Security Advisory**: <https://github.com/jaseonline/vlc-mcp/security/advisories/new>

### What to include

- Vulnerability type and severity
- Steps to reproduce
- Potential impact
- Proof of concept (if available)

### Response commitments

| Phase | Timeline |
| --- | --- |
| Initial response | Within 14 days |
| Triage | Within 21 days |
| Disclosure | Coordinated, within 90 days |

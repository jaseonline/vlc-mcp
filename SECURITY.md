# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest release | ✅ Current |

Only the latest release receives security fixes. Update to the latest version before reporting issues found in older releases.

## Controls

<!-- Replace with this project's real controls, or delete the section if there are none worth stating. -->

| Layer | Control |
| --- | --- |
| Secrets | Read from environment variables or the OS credential store; never committed. `.env*` is gitignored |
| Access | … |
| Logging | … (never logs secrets or content) |

Residual risks:

- …

## Reporting a vulnerability

Please do **not** open public issues for security problems. Report privately instead:

- **GitHub Security Advisory**: <https://github.com/jaseonline/{{PROJECT_NAME}}/security/advisories/new>

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

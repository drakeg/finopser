# Finopser agent and contributor operating standards

Follow [Mad Mallard repository standards](https://github.com/drakeg/madmallard-repository-standards) where compatible with this project's architecture, security boundaries, and existing documentation. This repository is independent: do not inspect or modify unrelated application repositories.

1. Read README.md, SPRINTS.md, BACKLOG.md, CONTRIBUTING.md, RELEASES.md, and the relevant docs/agile sprint before changing code.
2. Work in small, reviewable branches and PRs. Continue the highest-priority ready backlog task after merging; prioritize broken CI and security regressions.
3. Build → deploy locally → test → fix → retest. Report actual results, not assumed success. Do not provision paid cloud infrastructure or enable live Azure inventory/cost calls without authorization.
4. Maintain tenant isolation, least privilege, safe errors, and the existing fail-closed Azure provider defaults. Never store Azure tokens, client secrets, or credentials in account metadata.
5. Update implementation, regression tests, documentation, sprint/backlog state, and release impact together.
6. Preserve README badges immediately below the title. Only claim technologies verified from manifests and workflow files. Use dynamic GitHub Actions/status/release/issue/PR badges; never hardcode passing CI or invent a license. Revalidate badges whenever dependencies, workflows, or deployment options change.
7. Respect branch protection and human review. Record the PR URL, tested commands, CI status, security impact, and rollback in PR descriptions.
8. Keep Docker Compose working with configurable ports, persistent database volumes, and documented LAN settings. Never destroy persistent volumes during routine development.
9. Favor SMB value: reduce cloud waste and manual governance work, prioritize a demonstrable customer workflow, and distinguish pricing hypotheses from validated demand.

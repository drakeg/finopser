# Finopser release policy

Use semantic versioning: **PATCH** for backward-compatible bug/security fixes, **MINOR** for backward-compatible features, **MAJOR** for incompatible public behavior, schema, or API changes. During 0.x development, document breaking changes explicitly.

A release is warranted when a tested, user-visible increment is ready for an SMB pilot or production consumer; routine documentation or dependency PR merges do not automatically require a release. Release candidates require green backend, frontend, CLI and Docker CI; migration and rollback notes; verified security boundaries; and an updated changelog or release notes.

Tag releases only after required reviews and validation. Publish GitHub releases from actual tags; never invent release numbers or claim a release exists because a badge can display one. No automatic production deployment or paid hosting is implied.

For a breaking migration, document backup, upgrade, downgrade limitations and recovery steps before tagging. Keep `SPRINTS.md`, `BACKLOG.md`, and user-facing README current.

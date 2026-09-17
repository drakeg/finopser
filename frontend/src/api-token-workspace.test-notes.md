# Automation identity workspace acceptance

The Administration integration workspace must preserve these UI invariants:

- service-principal create/list/disable/enable controls are manager-only because all backing endpoints enforce manager RBAC;
- only active service principals appear as selectable identities for new credentials;
- human-owned credential issuance remains selectable for backward compatibility;
- plaintext credentials appear only in the transient copy-once panel after issue or rotation;
- disabled service-principal credentials display a blocked state and cannot be rotated;
- no token digest or previously issued plaintext secret is requested or rendered by the workspace.

Backend lifecycle and end-to-end tests are the authoritative security acceptance coverage for these behaviors.

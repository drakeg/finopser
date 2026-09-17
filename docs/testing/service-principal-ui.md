# Service-principal UI invariants

The Administration integration workspace preserves these UI constraints:

- service-principal create/list/disable/enable controls use manager-protected endpoints;
- only active service principals are selectable for new credentials;
- human-owned credential issuance remains available for backward compatibility;
- plaintext credentials appear only in the transient copy-once panel after issue or rotation;
- credentials bound to disabled principals show a blocked state and cannot be rotated;
- the workspace never requests or renders a token digest or previously issued plaintext secret.

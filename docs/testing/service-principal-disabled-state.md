# Disabled-principal semantics

Disabling a service principal preserves its credentials for history but causes authentication to fail immediately. Rotation is blocked while disabled. Re-enabling the principal restores credentials only when they are otherwise active, unexpired, and correctly scoped.

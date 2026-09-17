# Service-principal RBAC acceptance

Service-principal lifecycle and credential-management endpoints require workspace manager roles. Principal lookups are filtered by the caller's organization and return not found for another tenant. Bearer authentication derives tenant scope from the service principal itself rather than from the human creator.

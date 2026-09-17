# Service-principal audit evidence

Lifecycle audit events record the service principal object and human actor. Credential create, rotate, and revoke events include `service_principal_id` when bound to a principal plus non-secret metadata such as token prefix and scopes. Plaintext credentials are excluded from audit metadata.

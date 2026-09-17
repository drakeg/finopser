# Service-principal acceptance matrix

Sprint 23 validates service-principal automation without live cloud provisioning.

| Scenario | Expected result |
| --- | --- |
| Manager creates principal | Principal is tenant-bound and audited |
| Non-manager manages principals | Request is denied |
| Other tenant addresses principal | Resource is not disclosed |
| Manager issues bound read-only token | Secret is returned once; digest remains private |
| Bound token calls `/api/v1/` | Principal organization and scope govern access |
| Principal is disabled | Existing bound token fails immediately |
| Principal is re-enabled | Otherwise-valid bound token works again |
| Credential is rotated | Old secret fails; replacement works and is shown once |
| Credential is revoked | Replacement secret fails immediately |
| Audit evidence is inspected | Principal identity/prefix metadata exists; plaintext secret does not |
| Human-owned token is issued | Existing workflow remains compatible |

These scenarios are covered by `test_service_principal_lifecycle.py` and `test_service_principal_acceptance.py` and run against the local test database in CI.

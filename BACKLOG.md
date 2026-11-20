# Finopser prioritized backlog

This is the actionable summary. Full epics and longer-term scope: [docs/agile/product-backlog.md](docs/agile/product-backlog.md). Confirm current issue and PR status before implementation.

| Priority | Work | Acceptance criteria |
|---|---|---|
| P0 | Repair failing CI/builds/security regressions | Reproduce from logs, fix, rerun affected checks, no regressions |
| P0 | Sprint 32: safely connect Azure authenticated subscription lookup to tenant-scoped onboarding | Enforce organization authorization, tenant/subscription match, safe audit, no stored tokens, explicit fail-closed tests |
| P0 | Keep AWS onboarding and Docker Compose healthy | Existing AWS tests and Compose smoke checks remain green; configurable ports and documented LAN access |
| P1 | Finish Azure validation UX and operator guidance | Actionable non-secret setup instructions and accurate connection states |
| P1 | SMB pilot workflow for actionable cloud waste | Demo from onboarding to an evidence-backed savings recommendation; measure time saved and value |
| P1 | Customer discovery and pricing hypothesis | Record prospect interviews and willingness-to-pay evidence; do not invent validation |
| P2 | Azure inventory and cost ingestion | Only after authorized validation, security review, permissions and tests |
| P2 | CI badge/documentation consistency check | Detect missing README badge markers and required project docs without needing external network access |

No paid deployment or live cloud mutation is authorized by this backlog.

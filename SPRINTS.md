# Finopser sprint roadmap

Detailed numbered sprint history and acceptance criteria live in [docs/agile/](docs/agile/). This index does not restart completed work.

| Sprint | Focus | Status |
|---|---|---|
| 1–30 | Application, AWS governance, cost workflows, reporting | Historical work; see numbered sprint records |
| 31 | Pre-multicloud hardening | Refer to sprint history |
| 32 | Multi-cloud provider foundation, Azure registration and secretless identity | In progress — see [Sprint 32](docs/agile/sprint-32.md) |
| 33 (proposed) | Authorized Azure onboarding validation and operational safeguards | Planned, contingent on Sprint 32 acceptance |
| 34 (proposed) | SMB pilot usability, measurable cost-saving workflow and demo | Backlog candidate, subject to reprioritization |

## Current Sprint 32 acceptance gate

- Provider-neutral contract and AWS regression safety preserved.
- Azure subscription registration remains credential-free and tenant-scoped.
- Azure runtime identity, subscription lookup and tenant proof have deterministic tests.
- Production Azure validation, inventory and cost synchronization remain disabled until securely wired, authorized and tested.
- CI and Docker Compose checks pass on the integration branch before declaring completion.

Work from [BACKLOG.md](BACKLOG.md) and [product backlog](docs/agile/product-backlog.md). A merged PR does not by itself close a sprint.

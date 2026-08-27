# Architecture Decision Records

Architecture Decision Records (ADRs) document significant technical and product-architecture decisions and the rationale behind them.

## Status Values

- **Proposed** — under review; implementation should not assume acceptance.
- **Accepted** — current project decision.
- **Superseded** — replaced by a later ADR.
- **Deprecated** — retained for history but no longer recommended.

## Initial Register

| ADR | Decision | Status |
|---|---|---|
| ADR-0001 | Docker-first, AWS-ready application architecture | Accepted |
| ADR-0002 | Provider abstraction with AWS as first implementation | Accepted |
| ADR-0003 | AWS access through STS AssumeRole rather than stored IAM user keys | Accepted |
| ADR-0004 | Observe → Recommend → Enforce safety model | Accepted |
| ADR-0005 | PostgreSQL as the primary relational database | Accepted |
| ADR-0006 | Recursive organizational hierarchy and scoped inheritance | Accepted |
| ADR-0007 | Backend framework selection | Proposed |
| ADR-0008 | Frontend architecture selection | Proposed |
| ADR-0009 | Background task architecture | Proposed |
| ADR-0010 | API-first application architecture details | Proposed |
| ADR-0011 | Audit-event storage and retention architecture | Proposed |
| ADR-0012 | Production secrets integration | Proposed |

Accepted ADRs may later be superseded, but implementation changes that contradict an accepted ADR require a new/superseding ADR or explicit amendment.

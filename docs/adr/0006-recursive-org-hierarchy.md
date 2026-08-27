# ADR-0006 — Recursive organizational hierarchy and scoped inheritance

**Status:** Accepted

## Context

Cloud governance must reflect real organizational structures that may contain multiple nested business, technical, and project levels. Policies, budgets, controls, and access rules often need to inherit through those levels.

## Decision

The organizational model will support recursive organizational nodes rather than a fixed number of hierarchy levels. Governance objects may be assigned by scope and inherited by descendants. Direct assignments, inherited assignments, and approved exceptions must remain distinguishable.

## Consequences

- Hierarchy depth is flexible without schema redesign.
- Effective configuration requires deterministic inheritance and conflict rules.
- Policy/budget/access evaluation must expose assignment provenance.
- Detailed override/conflict precedence will be documented before implementation of inherited governance behavior.

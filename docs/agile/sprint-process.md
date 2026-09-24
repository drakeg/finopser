# Sprint Process

Finopser uses small implementation slices within numbered sprints.

## 1. Select and define

- Choose the highest-value unfinished backlog gap based on the current repository state.
- Create a parent sprint issue with goal, planned slices, acceptance gate, and safety/cost boundary.
- Create one implementation issue per slice with testable acceptance criteria.
- Do not duplicate a capability merely because the current UI or documentation has regressed; inspect prior sprint documentation and existing APIs first.

## 2. Implement a slice

- Branch from current `main`.
- Keep the slice narrowly scoped.
- Update implementation, tests, migrations, and documentation together.
- Prefer local/Docker and GitHub CI verification.
- External/cloud integrations use deterministic fakes unless live activation is explicitly authorized.

## 3. Verify

Before declaring a slice merge-ready:

- inspect the complete changed surface for security/tenant-boundary regressions;
- run/observe required CI;
- investigate the exact failed job and log if CI fails;
- confirm Docker/local verification remains viable;
- confirm documentation matches actual behavior;
- confirm no unauthorized paid/live/production behavior was introduced.

## 4. Merge and continue

After a slice is merged:

- verify the PR is actually merged and its issue is closed;
- continue directly to the next planned slice;
- close the parent sprint only after its acceptance gate is satisfied;
- then re-plan from the current backlog/repository state.

## Definition of sprint complete

A sprint is complete when all planned acceptance criteria are represented in merged code/tests/docs, required CI is green, safety/cost boundaries are preserved, and the parent issue is closed as completed.

## Regression handling

If current code contradicts a previously completed sprint:

1. treat the discrepancy as a regression;
2. use prior sprint documentation/tests as design evidence;
3. restore/harden the intended capability rather than inventing a parallel implementation;
4. add regression coverage where practical.

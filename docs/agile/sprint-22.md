# Sprint 22 — Packaged CLI and Stable Read-Only API Consumer

## Sprint goal

Turn the Sprint 20–21 public API authentication foundation into a practical, low-dependency CLI for operators and automation without widening the read-only machine boundary.

## Issue

- #82 — Sprint 22: Packaged CLI and stable read-only API consumer

## Slice 1 — CLI foundation

The repository now includes a standalone Python package under `cli/` with a `finopser` console entry point. The package has no runtime third-party dependencies and does not import Django application internals.

Configuration is provided at runtime:

- `FINOPSER_URL` or `--url` — Finopser base URL.
- `FINOPSER_TOKEN` or `--token` — one-time-issued Bearer credential.

Using `FINOPSER_TOKEN` is preferred for interactive use because it avoids placing the token directly in shell history. The CLI does not persist the URL or token.

Supported commands map only to the approved Sprint 20–21 read-only API surfaces:

- `finopser dashboard`
- `finopser accounts`
- `finopser resources`
- `finopser costs`
- `finopser compliance`
- `finopser policy-violations`
- `finopser recommendations`
- `finopser reports`

Output is indented, deterministic JSON by default. `--compact` emits compact sorted JSON for scripts.

HTTP and network errors are normalized to concise stderr messages with non-zero exit status. Token values are never included in generated error messages.

## Slice 2 — Human-readable table output

Interactive users can request `--format table` without installing any additional runtime dependency. JSON remains the default automation contract.

The renderer is deliberately generic across the approved read-only surfaces:

- lists of objects use deterministic alphabetic columns;
- paginated payloads render the `results` collection;
- object summaries render `field | value` rows;
- nested lists/objects are encoded as compact deterministic JSON inside a table cell;
- empty lists report `No results.`;
- `--compact` remains JSON-only and is rejected when combined with table output.

This slice changes presentation only. It does not add endpoints, scopes, persistence, mutation commands, or broader machine permissions.

## Local use

From the repository root:

```bash
python -m pip install -e ./cli
export FINOPSER_URL=http://127.0.0.1:8000
export FINOPSER_TOKEN='<copy-once-token>'
finopser accounts
finopser --format table accounts
```

A credential must include the scope required by the requested endpoint. For example, `finopser accounts` requires `accounts:read`, while `finopser resources` requires `resources:read`.

## Validation

The CLI has network-free unit coverage for Bearer request construction, URL/token validation, HTTP/network error normalization, command-to-endpoint mapping, deterministic compact output, human-readable table formatting, paginated table rendering, nested-cell formatting, format conflict handling, and non-zero failure behavior.

CI runs the CLI suite in a separate lightweight Python job without installing backend or frontend dependencies, preserving fast validation.

## Safety / cost gate

The CLI contains no mutation/remediation commands, credential persistence, paid gateway integration, hosted integration service, production public exposure, recurring spend, or live cloud provisioning.

## Next slices

- Add pagination/query options where the API surfaces expose stable parameters.
- Define/version the public API contract and compatibility policy.
- Add service-principal semantics after the CLI contract is stable.

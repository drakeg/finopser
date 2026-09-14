# Finopser CLI

The Finopser CLI is a standalone, read-only client for the approved public API surfaces.

## Install for development

```bash
python -m pip install -e ./cli
```

## Configure

Prefer environment variables so API tokens are not placed directly in shell history:

```bash
export FINOPSER_URL=http://127.0.0.1:8000
export FINOPSER_TOKEN='<copy-once-token>'
```

The equivalent `--url` and `--token` options are available when needed. The CLI does not persist either value.

## Commands

```text
finopser dashboard
finopser accounts
finopser resources
finopser costs
finopser compliance
finopser policy-violations
finopser recommendations
finopser reports
```

Each command requires the matching read scope on the token. All commands use HTTP GET and the CLI intentionally exposes no mutation or remediation operations.

## Output formats

JSON remains the default and automation contract. It is pretty-printed unless `--compact` is supplied:

```bash
finopser accounts
finopser --compact accounts
```

For interactive terminal use, request the dependency-free table renderer:

```bash
finopser --format table accounts
finopser --format table resources
```

List responses are rendered with stable alphabetic columns. Paginated responses render their `results` list. Object responses such as dashboard summaries render as `field | value` rows. Nested objects and lists are represented as compact deterministic JSON within a cell.

`--compact` applies only to JSON output and cannot be combined with `--format table`.

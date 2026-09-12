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

JSON is pretty-printed by default. Add `--compact` before the command for deterministic compact JSON suitable for scripts:

```bash
finopser --compact accounts
```

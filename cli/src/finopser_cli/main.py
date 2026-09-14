import argparse
import json
import os
import sys

from .client import FinopserClient, FinopserClientError


COMMAND_PATHS = {
    "dashboard": "/api/dashboard/",
    "accounts": "/api/cloud-accounts/",
    "resources": "/api/resources/",
    "costs": "/api/costs/",
    "compliance": "/api/compliance/findings/",
    "policy-violations": "/api/policy-violations/",
    "recommendations": "/api/recommendations/",
    "reports": "/api/reports/",
}


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)


def _grid(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def line(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)).rstrip()

    separator = "-+-".join("-" * width for width in widths)
    return "\n".join([line(headers), separator, *(line(row) for row in rows)])


def render_table(payload) -> str:
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        payload = payload["results"]

    if isinstance(payload, list):
        if not payload:
            return "No results."
        if all(isinstance(item, dict) for item in payload):
            headers = sorted({key for item in payload for key in item})
            rows = [[_cell(item.get(header)) for header in headers] for item in payload]
            return _grid(headers, rows)
        return _grid(["value"], [[_cell(item)] for item in payload])

    if isinstance(payload, dict):
        rows = [[str(key), _cell(value)] for key, value in sorted(payload.items())]
        return _grid(["field", "value"], rows)

    return _grid(["value"], [[_cell(payload)]])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="finopser", description="Read-only Finopser CLI")
    parser.add_argument(
        "--url",
        default=os.environ.get("FINOPSER_URL"),
        help="Finopser base URL (or FINOPSER_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("FINOPSER_TOKEN"),
        help="API token (or FINOPSER_TOKEN)",
    )
    parser.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format; JSON remains the automation-safe default",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Emit compact JSON for scripts instead of indented JSON",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in COMMAND_PATHS:
        subparsers.add_parser(command, help=f"Read {command.replace('-', ' ')} data")
    return parser


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.url:
        parser.error("--url or FINOPSER_URL is required")
    if not args.token:
        parser.error("--token or FINOPSER_TOKEN is required")
    if args.format == "table" and args.compact:
        print("finopser: --compact can only be used with --format json", file=sys.stderr)
        return 2

    try:
        client = FinopserClient(args.url, args.token)
        payload = client.get(COMMAND_PATHS[args.command])
    except (ValueError, FinopserClientError) as exc:
        print(f"finopser: {exc}", file=sys.stderr)
        return 1

    if args.format == "table":
        print(render_table(payload))
    elif args.compact:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

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

    try:
        client = FinopserClient(args.url, args.token)
        payload = client.get(COMMAND_PATHS[args.command])
    except (ValueError, FinopserClientError) as exc:
        print(f"finopser: {exc}", file=sys.stderr)
        return 1

    if args.compact:
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

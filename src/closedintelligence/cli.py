"""Command-line interface for ClosedIntelligence."""

from __future__ import annotations

import argparse
import json
import sys

from .core import Lens, answer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="closedintelligence",
        description="Logic-only multi-agent chat over open webs, fields, and lenses.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    answer_cmd = sub.add_parser("answer", help="answer a question from a field snapshot")
    answer_cmd.add_argument("question", help="question to answer")
    answer_cmd.add_argument("--field", required=True, help="JSON field/web snapshot")
    answer_cmd.add_argument("--pretty", action="store_true", help="pretty-print JSON")

    inspect_cmd = sub.add_parser("inspect", help="inspect top Lens candidates")
    inspect_cmd.add_argument("question", help="query text")
    inspect_cmd.add_argument("--field", required=True, help="JSON field/web snapshot")
    inspect_cmd.add_argument("--limit", type=int, default=6, help="candidate limit")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        lens = Lens.from_json_file(args.field)
        if args.cmd == "answer":
            packet = answer(args.question, lens)
            print(json.dumps(packet.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
            return 0
        if args.cmd == "inspect":
            candidates = lens.query(args.question, limit=args.limit)
            print(json.dumps([
                {
                    "id": item.record.id,
                    "title": item.record.title,
                    "score": item.score,
                    "matched_terms": list(item.matched_terms),
                }
                for item in candidates
            ], indent=2, sort_keys=True))
            return 0
    except Exception as exc:
        print(f"closedintelligence: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

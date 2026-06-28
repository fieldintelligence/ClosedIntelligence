"""Command-line interface for ClosedIntelligence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .core import Lens, answer
from .dapp import CompanyField, EmployeeIdentity, SignedEvent, bundle_path, load_bundle, save_bundle
from .webapp import serve


DEFAULT_STATE = ".closedintelligence/company-field.json"
SENSITIVE_KEY_FRAGMENTS = ("signature", "mesh_key", "secret", "private", "password", "token")


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

    dapp = sub.add_parser("dapp", help="run the internal P2P employee dapp")
    dapp_sub = dapp.add_subparsers(dest="dapp_cmd", required=True)

    def add_state_flags(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument("--state", default=DEFAULT_STATE, help="company field state file")
        cmd.add_argument("--company", default="FieldIntelligence", help="company/field name")
        cmd.add_argument("--mesh-key", default=os.environ.get("CLOSEDINTELLIGENCE_MESH_KEY"), help="permissioned mesh key")

    init_cmd = dapp_sub.add_parser("init", help="initialize a local company field")
    add_state_flags(init_cmd)

    serve_cmd = dapp_sub.add_parser("serve", help="serve the browser dapp")
    add_state_flags(serve_cmd)
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8787)
    serve_cmd.add_argument("--quiet", action="store_true")

    state_cmd = dapp_sub.add_parser("state", help="print the current field snapshot")
    add_state_flags(state_cmd)

    join_cmd = dapp_sub.add_parser("join", help="join an employee identity to the field")
    add_state_flags(join_cmd)
    join_cmd.add_argument("handle")
    join_cmd.add_argument("display_name")
    join_cmd.add_argument("--department", default="general")

    post_cmd = dapp_sub.add_parser("post", help="post a knowledge record")
    add_state_flags(post_cmd)
    post_cmd.add_argument("author")
    post_cmd.add_argument("title")
    post_cmd.add_argument("body")
    post_cmd.add_argument("--tag", action="append", default=[])

    proposal_cmd = dapp_sub.add_parser("proposal", help="open a proposal")
    add_state_flags(proposal_cmd)
    proposal_cmd.add_argument("author")
    proposal_cmd.add_argument("title")
    proposal_cmd.add_argument("body")
    proposal_cmd.add_argument("--option", action="append", default=None)

    vote_cmd = dapp_sub.add_parser("vote", help="vote on a proposal")
    add_state_flags(vote_cmd)
    vote_cmd.add_argument("author")
    vote_cmd.add_argument("proposal_id")
    vote_cmd.add_argument("option")
    vote_cmd.add_argument("--reason", default="")

    task_cmd = dapp_sub.add_parser("task", help="assign a task")
    add_state_flags(task_cmd)
    task_cmd.add_argument("author")
    task_cmd.add_argument("assignee")
    task_cmd.add_argument("title")
    task_cmd.add_argument("body")
    task_cmd.add_argument("--due", default="")

    decision_cmd = dapp_sub.add_parser("decision", help="record a decision")
    add_state_flags(decision_cmd)
    decision_cmd.add_argument("author")
    decision_cmd.add_argument("title")
    decision_cmd.add_argument("body")
    decision_cmd.add_argument("--proposal-id", default="")

    export_cmd = dapp_sub.add_parser("export", help="export a signed P2P bundle")
    add_state_flags(export_cmd)
    export_cmd.add_argument("out")

    import_cmd = dapp_sub.add_parser("import", help="merge a signed P2P bundle")
    add_state_flags(import_cmd)
    import_cmd.add_argument("bundle")

    ask_cmd = dapp_sub.add_parser("answer", help="answer over the current company field")
    add_state_flags(ask_cmd)
    ask_cmd.add_argument("question")
    ask_cmd.add_argument("--pretty", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.cmd == "answer":
            lens = Lens.from_json_file(args.field)
            packet = answer(args.question, lens)
            print(json.dumps(packet.to_dict(), indent=2 if args.pretty else None, sort_keys=True))
            return 0
        if args.cmd == "inspect":
            lens = Lens.from_json_file(args.field)
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
        if args.cmd == "dapp":
            return run_dapp(args)
    except Exception as exc:
        print(f"closedintelligence: {exc}", file=sys.stderr)
        return 2

    parser.error(f"unknown command: {args.cmd}")
    return 2


def load_field(args: argparse.Namespace) -> CompanyField:
    return CompanyField.load(args.state, company=args.company, mesh_key=args.mesh_key)


def save_field(args: argparse.Namespace, field: CompanyField) -> None:
    field.save(args.state)


def terminal_safe(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(fragment in key_text.lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
                safe[key_text] = "<redacted>"
            else:
                safe[key_text] = terminal_safe(item)
        return safe
    if isinstance(value, list):
        return [terminal_safe(item) for item in value]
    if isinstance(value, tuple):
        return [terminal_safe(item) for item in value]
    return value


def print_json(value: Any, *, pretty: bool = True) -> None:
    safe_value = terminal_safe(value)
    sys.stdout.write(json.dumps(safe_value, indent=2 if pretty else None, sort_keys=True))
    sys.stdout.write("\n")


def event_receipt(event: SignedEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "kind": event.kind,
        "author": event.author,
        "timestamp_ms": event.timestamp_ms,
        "prev": event.prev,
        "payload": dict(event.payload),
    }


def run_dapp(args: argparse.Namespace) -> int:
    if args.dapp_cmd == "init":
        field = load_field(args)
        save_field(args, field)
        print_json({"state": args.state, "company": field.company, "head": field.head})
        return 0

    if args.dapp_cmd == "serve":
        server = serve(args.host, args.port, args.state, company=args.company, mesh_key=args.mesh_key, quiet=args.quiet)
        print(f"ClosedIntelligence DApp listening on http://{args.host}:{args.port}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        finally:
            server.server_close()
        return 0

    field = load_field(args)
    if args.dapp_cmd == "state":
        print_json(field.snapshot().to_dict())
        return 0
    if args.dapp_cmd == "join":
        employee = EmployeeIdentity.create(args.handle, args.display_name, args.department)
        event = field.join_employee(employee)
        save_field(args, field)
        print_json({"employee": employee.to_dict(), "event": event_receipt(event)})
        return 0
    if args.dapp_cmd == "post":
        event = field.post_knowledge(args.author, args.title, args.body, args.tag)
        save_field(args, field)
        print_json(event_receipt(event))
        return 0
    if args.dapp_cmd == "proposal":
        event = field.open_proposal(args.author, args.title, args.body, args.option or ["yes", "no"])
        save_field(args, field)
        print_json(event_receipt(event))
        return 0
    if args.dapp_cmd == "vote":
        event = field.vote(args.author, args.proposal_id, args.option, args.reason)
        save_field(args, field)
        print_json(event_receipt(event))
        return 0
    if args.dapp_cmd == "task":
        event = field.assign_task(args.author, args.assignee, args.title, args.body, args.due)
        save_field(args, field)
        print_json(event_receipt(event))
        return 0
    if args.dapp_cmd == "decision":
        event = field.record_decision(args.author, args.title, args.body, args.proposal_id)
        save_field(args, field)
        print_json(event_receipt(event))
        return 0
    if args.dapp_cmd == "export":
        save_bundle(args.out, field.export_bundle())
        print_json({"out": str(bundle_path(args.out)), "events": len(field.events), "head": field.head})
        return 0
    if args.dapp_cmd == "import":
        report = field.merge_bundle(load_bundle(args.bundle))
        save_field(args, field)
        print_json(report.to_dict())
        return 0
    if args.dapp_cmd == "answer":
        lens = Lens.from_mapping(field.to_lens_records(), source=str(Path(args.state)))
        packet = answer(args.question, lens)
        print_json(packet.to_dict(), pretty=args.pretty)
        return 0

    raise ValueError(f"unknown dapp command: {args.dapp_cmd}")


if __name__ == "__main__":
    raise SystemExit(main())

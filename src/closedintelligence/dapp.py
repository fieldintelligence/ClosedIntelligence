"""Enterprise dapp primitives for internal P2P intelligence fields.

The runtime is intentionally dependency-free. It gives companies a local,
append-only event log that can be shared between opted-in employees by exchanging
bundles over an internal channel. The default signer is an HMAC mesh key for a
permissioned company field; production deployments can replace it with a public
key adapter without changing the event shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import time
from typing import Any, Iterable, Literal, Mapping

EventKind = Literal[
    "employee.joined",
    "knowledge.posted",
    "proposal.opened",
    "proposal.voted",
    "task.assigned",
    "decision.recorded",
    "peer.trusted",
]


def now_ms() -> int:
    return int(time.time() * 1000)


def stable_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class EmployeeIdentity:
    """One local employee identity in a permissioned company field."""

    handle: str
    display_name: str
    department: str = "general"
    public_id: str = ""

    @classmethod
    def create(cls, handle: str, display_name: str, department: str = "general") -> "EmployeeIdentity":
        base = f"{handle}:{display_name}:{department}:{secrets.token_hex(8)}"
        return cls(handle=handle, display_name=display_name, department=department, public_id=sha256_hex(base)[:24])

    def to_dict(self) -> dict[str, str]:
        return {
            "handle": self.handle,
            "display_name": self.display_name,
            "department": self.department,
            "public_id": self.public_id,
        }


@dataclass(frozen=True)
class SignedEvent:
    """Append-only dapp event shared across internal peers."""

    id: str
    kind: EventKind
    author: str
    timestamp_ms: int
    payload: Mapping[str, Any]
    prev: str | None
    signature: str

    def unsigned_body(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "author": self.author,
            "timestamp_ms": self.timestamp_ms,
            "payload": dict(self.payload),
            "prev": self.prev,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            **self.unsigned_body(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SignedEvent":
        return cls(
            id=str(data["id"]),
            kind=data["kind"],
            author=str(data["author"]),
            timestamp_ms=int(data["timestamp_ms"]),
            payload=dict(data.get("payload", {})),
            prev=str(data["prev"]) if data.get("prev") is not None else None,
            signature=str(data["signature"]),
        )


@dataclass(frozen=True)
class MergeReport:
    imported: int
    skipped: int
    rejected: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"imported": self.imported, "skipped": self.skipped, "rejected": list(self.rejected)}


@dataclass
class FieldSnapshot:
    company: str
    event_count: int
    employees: dict[str, dict[str, Any]] = field(default_factory=dict)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    proposals: dict[str, dict[str, Any]] = field(default_factory=dict)
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    trusted_peers: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "event_count": self.event_count,
            "employees": self.employees,
            "knowledge": self.knowledge,
            "proposals": self.proposals,
            "tasks": self.tasks,
            "decisions": self.decisions,
            "trusted_peers": self.trusted_peers,
        }


class CompanyField:
    """Internal company dapp field backed by a signed append-only event log."""

    def __init__(self, company: str, mesh_key: str, events: Iterable[SignedEvent] = ()):
        if not company:
            raise ValueError("company is required")
        if not mesh_key:
            raise ValueError("mesh_key is required")
        self.company = company
        self.mesh_key = mesh_key
        self._events: list[SignedEvent] = []
        self._ids: set[str] = set()
        for event in events:
            self._append_existing(event)

    @classmethod
    def load(cls, path: str | Path, *, company: str = "FieldIntelligence", mesh_key: str | None = None) -> "CompanyField":
        state_path = Path(path)
        if not state_path.exists():
            return cls(company=company, mesh_key=mesh_key or secrets.token_hex(32))
        data = json.loads(state_path.read_text(encoding="utf-8"))
        events = [SignedEvent.from_dict(item) for item in data.get("events", [])]
        return cls(
            company=str(data.get("company") or company),
            mesh_key=str(data.get("mesh_key") or mesh_key or secrets.token_hex(32)),
            events=events,
        )

    def save(self, path: str | Path) -> None:
        state_path = Path(path)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "company": self.company,
            "mesh_key": self.mesh_key,
            "events": [event.to_dict() for event in self._events],
        }
        state_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @property
    def events(self) -> tuple[SignedEvent, ...]:
        return tuple(self._events)

    @property
    def head(self) -> str | None:
        return self._events[-1].id if self._events else None

    def append(self, kind: EventKind, author: str, payload: Mapping[str, Any], *, timestamp_ms: int | None = None) -> SignedEvent:
        unsigned = {
            "kind": kind,
            "author": author,
            "timestamp_ms": timestamp_ms or now_ms(),
            "payload": dict(payload),
            "prev": self.head,
        }
        signature = self._sign(unsigned)
        event_id = sha256_hex(stable_json({**unsigned, "signature": signature}))
        event = SignedEvent(
            id=event_id,
            kind=kind,
            author=author,
            timestamp_ms=int(unsigned["timestamp_ms"]),
            payload=dict(payload),
            prev=self.head,
            signature=signature,
        )
        self._append_existing(event)
        return event

    def join_employee(self, employee: EmployeeIdentity) -> SignedEvent:
        return self.append("employee.joined", employee.public_id, employee.to_dict())

    def post_knowledge(self, author: str, title: str, body: str, tags: Iterable[str] = ()) -> SignedEvent:
        return self.append(
            "knowledge.posted",
            author,
            {"title": title, "body": body, "tags": sorted({str(tag).lower() for tag in tags})},
        )

    def open_proposal(self, author: str, title: str, body: str, options: Iterable[str] = ("yes", "no")) -> SignedEvent:
        proposal_id = f"proposal:{sha256_hex(title + body)[:16]}"
        return self.append(
            "proposal.opened",
            author,
            {"proposal_id": proposal_id, "title": title, "body": body, "options": list(options)},
        )

    def vote(self, author: str, proposal_id: str, option: str, reason: str = "") -> SignedEvent:
        return self.append(
            "proposal.voted",
            author,
            {"proposal_id": proposal_id, "option": option, "reason": reason},
        )

    def assign_task(self, author: str, assignee: str, title: str, body: str, due: str = "") -> SignedEvent:
        task_id = f"task:{sha256_hex(assignee + title + body)[:16]}"
        return self.append(
            "task.assigned",
            author,
            {"task_id": task_id, "assignee": assignee, "title": title, "body": body, "due": due, "status": "open"},
        )

    def record_decision(self, author: str, title: str, body: str, proposal_id: str = "") -> SignedEvent:
        return self.append(
            "decision.recorded",
            author,
            {"title": title, "body": body, "proposal_id": proposal_id},
        )

    def trust_peer(self, author: str, peer_url: str, label: str, public_id: str = "") -> SignedEvent:
        return self.append(
            "peer.trusted",
            author,
            {"peer_url": peer_url, "label": label, "public_id": public_id},
        )

    def export_bundle(self, *, since: str | None = None) -> dict[str, Any]:
        events = self._events
        if since:
            seen = False
            filtered: list[SignedEvent] = []
            for event in events:
                if seen:
                    filtered.append(event)
                if event.id == since:
                    seen = True
            events = filtered
        return {
            "format": "closedintelligence.bundle.v1",
            "company": self.company,
            "head": self.head,
            "events": [event.to_dict() for event in events],
        }

    def merge_bundle(self, bundle: Mapping[str, Any]) -> MergeReport:
        if bundle.get("format") != "closedintelligence.bundle.v1":
            raise ValueError("unsupported bundle format")
        imported = 0
        skipped = 0
        rejected: list[str] = []
        for raw in bundle.get("events", []):
            event = SignedEvent.from_dict(raw)
            if event.id in self._ids:
                skipped += 1
                continue
            if not self.verify_event(event):
                rejected.append(event.id)
                continue
            self._append_existing(event)
            imported += 1
        return MergeReport(imported=imported, skipped=skipped, rejected=tuple(rejected))

    def verify_event(self, event: SignedEvent) -> bool:
        expected_sig = self._sign(event.unsigned_body())
        expected_id = sha256_hex(stable_json({**event.unsigned_body(), "signature": expected_sig}))
        return hmac.compare_digest(expected_sig, event.signature) and hmac.compare_digest(expected_id, event.id)

    def verify_chain(self) -> tuple[bool, tuple[str, ...]]:
        errors: list[str] = []
        ids = {event.id for event in self._events}
        for event in self._events:
            if event.prev is not None and event.prev not in ids:
                errors.append(f"{event.id}: missing prev {event.prev}")
            if not self.verify_event(event):
                errors.append(f"{event.id}: signature mismatch")
        return (not errors, tuple(errors))

    def snapshot(self) -> FieldSnapshot:
        employees: dict[str, dict[str, Any]] = {}
        knowledge: list[dict[str, Any]] = []
        proposals: dict[str, dict[str, Any]] = {}
        tasks: dict[str, dict[str, Any]] = {}
        decisions: list[dict[str, Any]] = []
        trusted_peers: dict[str, dict[str, Any]] = {}

        for event in self._events:
            payload = dict(event.payload)
            if event.kind == "employee.joined":
                employees[event.author] = payload
            elif event.kind == "knowledge.posted":
                knowledge.append({"event_id": event.id, "author": event.author, **payload})
            elif event.kind == "proposal.opened":
                proposal_id = str(payload["proposal_id"])
                proposals[proposal_id] = {"event_id": event.id, "author": event.author, "votes": {}, **payload}
            elif event.kind == "proposal.voted":
                proposal_id = str(payload["proposal_id"])
                proposal = proposals.setdefault(proposal_id, {"proposal_id": proposal_id, "votes": {}})
                votes = proposal.setdefault("votes", {})
                votes[event.author] = {"option": payload.get("option"), "reason": payload.get("reason", "")}
            elif event.kind == "task.assigned":
                tasks[str(payload["task_id"])] = {"event_id": event.id, "author": event.author, **payload}
            elif event.kind == "decision.recorded":
                decisions.append({"event_id": event.id, "author": event.author, **payload})
            elif event.kind == "peer.trusted":
                trusted_peers[str(payload["peer_url"])] = {"event_id": event.id, "author": event.author, **payload}

        return FieldSnapshot(
            company=self.company,
            event_count=len(self._events),
            employees=employees,
            knowledge=knowledge,
            proposals=proposals,
            tasks=tasks,
            decisions=decisions,
            trusted_peers=trusted_peers,
        )

    def to_lens_records(self) -> dict[str, Any]:
        snapshot = self.snapshot()
        records: list[dict[str, Any]] = []
        for item in snapshot.knowledge:
            records.append({
                "id": str(item["event_id"]),
                "title": str(item.get("title") or "Knowledge"),
                "body": str(item.get("body") or ""),
                "tags": list(item.get("tags") or []),
                "author": item.get("author"),
            })
        for proposal_id, proposal in snapshot.proposals.items():
            records.append({
                "id": proposal_id,
                "title": str(proposal.get("title") or proposal_id),
                "body": str(proposal.get("body") or ""),
                "tags": ["proposal"],
                "votes": proposal.get("votes", {}),
            })
        for decision in snapshot.decisions:
            records.append({
                "id": str(decision["event_id"]),
                "title": str(decision.get("title") or "Decision"),
                "body": str(decision.get("body") or ""),
                "tags": ["decision"],
                "author": decision.get("author"),
            })
        return {"records": records}

    def _append_existing(self, event: SignedEvent) -> None:
        if event.id in self._ids:
            return
        self._events.append(event)
        self._ids.add(event.id)

    def _sign(self, unsigned: Mapping[str, Any]) -> str:
        return hmac.new(self.mesh_key.encode("utf-8"), stable_json(unsigned).encode("utf-8"), hashlib.sha256).hexdigest()


def load_bundle(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_bundle(path: str | Path, bundle: Mapping[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")

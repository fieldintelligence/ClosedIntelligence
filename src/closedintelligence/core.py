"""Logic-only multi-agent reasoning over open fields and web snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-./]*", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in TOKEN_RE.finditer(text)}


@dataclass(frozen=True)
class FieldRecord:
    """One retrieved item from an open web or field snapshot."""

    id: str
    title: str
    body: str
    tags: tuple[str, ...] = ()
    source: str = "field"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        return " ".join([self.id, self.title, self.body, " ".join(self.tags)])


@dataclass(frozen=True)
class Candidate:
    record: FieldRecord
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class AgentNote:
    agent: str
    role: str
    note: str
    record_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnswerPacket:
    question: str
    answer: str
    confidence: float
    cited_record_ids: tuple[str, ...]
    notes: tuple[AgentNote, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "confidence": self.confidence,
            "cited_record_ids": list(self.cited_record_ids),
            "notes": [
                {
                    "agent": note.agent,
                    "role": note.role,
                    "note": note.note,
                    "record_ids": list(note.record_ids),
                }
                for note in self.notes
            ],
        }


class Lens:
    """Read-only retrieval lens over open FieldIntelligence/Knitweb-style snapshots."""

    def __init__(self, records: Iterable[FieldRecord]):
        ordered = sorted(records, key=lambda r: r.id)
        self._records = tuple(ordered)

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Lens":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_mapping(data, source=str(path))

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], *, source: str = "field") -> "Lens":
        if "records" in data:
            records = [_record_from_record_shape(item, source) for item in _require_list(data["records"], "records")]
            return cls(records)
        if "nodes" in data:
            nodes = data["nodes"]
            if not isinstance(nodes, Mapping):
                raise TypeError("nodes must be a mapping")
            records = [_record_from_node_shape(cid, value, source) for cid, value in nodes.items()]
            return cls(records)
        raise ValueError("field snapshot must contain records[] or nodes{}")

    def query(self, question: str, *, limit: int = 6) -> tuple[Candidate, ...]:
        q_terms = _tokens(question)
        if not q_terms:
            raise ValueError("question must contain searchable terms")

        candidates: list[Candidate] = []
        for record in self._records:
            r_terms = _tokens(record.searchable_text)
            matched = tuple(sorted(q_terms & r_terms))
            if not matched:
                continue
            density = len(matched) / max(1, math.sqrt(len(r_terms)))
            title_boost = 0.35 if q_terms & _tokens(record.title) else 0.0
            tag_boost = 0.2 if q_terms & set(record.tags) else 0.0
            score = density + title_boost + tag_boost
            candidates.append(Candidate(record, round(score, 6), matched))
        return tuple(sorted(candidates, key=lambda c: (-c.score, c.record.id))[:limit])


class ClaudeClaw:
    """Small deterministic multi-agent loop inspired by ClaudeClaw-style delegation."""

    def run(self, question: str, lens: Lens) -> AnswerPacket:
        candidates = lens.query(question)
        notes: list[AgentNote] = []

        if not candidates:
            notes.append(AgentNote("scout", "retrieval", "No matching field records were found."))
            return AnswerPacket(
                question=question,
                answer="I do not have enough field evidence to answer from the loaded webs.",
                confidence=0.0,
                cited_record_ids=(),
                notes=tuple(notes),
            )

        cited = tuple(candidate.record.id for candidate in candidates[:4])
        top_terms = _top_terms(candidates)
        notes.append(
            AgentNote(
                "scout",
                "retrieval",
                f"Selected {len(candidates)} records with shared terms: {', '.join(top_terms) or 'none'}.",
                cited,
            )
        )
        notes.append(
            AgentNote(
                "weaver",
                "synthesis",
                _weave_note(candidates),
                cited,
            )
        )
        notes.append(
            AgentNote(
                "skeptic",
                "critique",
                _skeptic_note(question, candidates),
                cited,
            )
        )
        notes.append(
            AgentNote(
                "steward",
                "field-boundary",
                "Used read-only field records; no private field export or hidden model call was performed.",
                cited,
            )
        )

        confidence = _confidence(candidates)
        answer_text = _final_answer(question, candidates, confidence)
        notes.append(AgentNote("speaker", "answer", "Emitted a cited answer packet.", cited))
        return AnswerPacket(
            question=question,
            answer=answer_text,
            confidence=confidence,
            cited_record_ids=cited,
            notes=tuple(notes),
        )


def answer(question: str, lens: Lens) -> AnswerPacket:
    """Answer a question using the default ClaudeClaw loop."""

    return ClaudeClaw().run(question, lens)


def _record_from_record_shape(item: Any, source: str) -> FieldRecord:
    if not isinstance(item, Mapping):
        raise TypeError("record entries must be objects")
    rid = str(item.get("id") or item.get("cid") or item.get("url") or "")
    if not rid:
        raise ValueError("record entries require id, cid, or url")
    title = str(item.get("title") or item.get("kind") or rid)
    body = str(item.get("body") or item.get("text") or item.get("content") or item.get("summary") or "")
    tags = _tags(item.get("tags"))
    metadata = {k: v for k, v in item.items() if k not in {"id", "cid", "url", "title", "kind", "body", "text", "content", "summary", "tags"}}
    return FieldRecord(rid, title, body, tags, source, metadata)


def _record_from_node_shape(cid: Any, value: Any, source: str) -> FieldRecord:
    if not isinstance(value, Mapping):
        raise TypeError("node entries must be objects")
    rid = str(cid)
    title = str(value.get("title") or value.get("kind") or value.get("scope") or rid)
    body_parts = [
        value.get("body"),
        value.get("text"),
        value.get("content"),
        value.get("summary"),
        value.get("subject"),
        value.get("predicate"),
        value.get("object"),
    ]
    body = " ".join(str(part) for part in body_parts if part)
    tags = _tags(value.get("tags"))
    return FieldRecord(rid, title, body, tags, source, dict(value))


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    return value


def _tags(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.lower(),)
    if not isinstance(value, Iterable):
        return ()
    return tuple(sorted({str(tag).lower() for tag in value if str(tag).strip()}))


def _top_terms(candidates: tuple[Candidate, ...]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        for term in candidate.matched_terms:
            counts[term] = counts.get(term, 0) + 1
    return tuple(term for term, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:8])


def _weave_note(candidates: tuple[Candidate, ...]) -> str:
    lead = candidates[0].record
    supporting = ", ".join(candidate.record.id for candidate in candidates[1:4]) or "none"
    return f"Lead record is {lead.id}; supporting records: {supporting}."


def _skeptic_note(question: str, candidates: tuple[Candidate, ...]) -> str:
    q_terms = _tokens(question)
    covered: set[str] = set()
    for candidate in candidates:
        covered.update(candidate.matched_terms)
    missing = tuple(sorted(q_terms - covered))[:6]
    if missing:
        return f"Question terms not covered by field evidence: {', '.join(missing)}."
    return "Loaded field evidence covers the searchable terms in the question."


def _confidence(candidates: tuple[Candidate, ...]) -> float:
    if not candidates:
        return 0.0
    score = sum(candidate.score for candidate in candidates[:4])
    return round(min(0.95, 0.25 + score / 5), 3)


def _final_answer(question: str, candidates: tuple[Candidate, ...], confidence: float) -> str:
    lead = candidates[0].record
    evidence = "; ".join(
        f"{candidate.record.id}: {candidate.record.body or candidate.record.title}"
        for candidate in candidates[:3]
    )
    return (
        f"ClosedIntelligence answers from loaded field evidence, not from a hidden heavy model. "
        f"For '{question}', the strongest lens match is {lead.id}. "
        f"Evidence summary: {evidence}. "
        f"Confidence: {confidence:.3f}."
    )

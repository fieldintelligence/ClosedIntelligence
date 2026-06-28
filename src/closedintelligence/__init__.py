"""ClosedIntelligence public API."""

from .core import (
    AgentNote,
    AnswerPacket,
    ClaudeClaw,
    FieldRecord,
    Lens,
    answer,
)
from .dapp import CompanyField, EmployeeIdentity, FieldSnapshot, MergeReport, SignedEvent

__all__ = [
    "AgentNote",
    "AnswerPacket",
    "ClaudeClaw",
    "CompanyField",
    "EmployeeIdentity",
    "FieldSnapshot",
    "FieldRecord",
    "Lens",
    "MergeReport",
    "SignedEvent",
    "answer",
]

__version__ = "0.1.0"

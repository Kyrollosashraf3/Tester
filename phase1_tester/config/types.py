"""Data types for Phase 1 tester."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional


@dataclass
class Turn:
    role: Literal["user", "assistant"]
    content: str
    ts: datetime


@dataclass
class ChatResult:
    assistant_text: str
    session_id: Optional[str]
    raw_events_count: int


@dataclass
class RunReport:
    success: bool
    turns: list["Turn"]
    final_summary: Optional[str]
    started_at: datetime
    ended_at: datetime
    error: Optional[str]

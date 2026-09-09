"""Episode schema for episodic memory."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Episode:
    """One past conversation turn stored for semantic retrieval."""

    text: str
    user_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    importance: float = 0.5
    episode_type: str = "interaction"

    def to_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "user_id": self.user_id,
            "session_id": self.session_id or "",
            "timestamp": self.timestamp,
            "importance": self.importance,
            "type": self.episode_type,
        }

    @classmethod
    def from_payload(cls, episode_id: str, payload: dict[str, Any]) -> Episode:
        return cls(
            id=str(episode_id),
            text=payload.get("text", ""),
            user_id=payload.get("user_id", ""),
            session_id=payload.get("session_id") or None,
            timestamp=payload.get("timestamp", 0.0),
            importance=payload.get("importance", 0.5),
            episode_type=payload.get("type", "interaction"),
        )

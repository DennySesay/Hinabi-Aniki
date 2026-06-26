from dataclasses import dataclass, field
from datetime import datetime
from typing import Set, Optional, Any

@dataclass
class Session:
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_manual: bool = False
    
    skills_used: set = field(default_factory=set)
    decks: set = field(default_factory=set)
    total_reviews: int = 0
    new_cards: int = 0
    lapses: int = 0
    
    total_paused_seconds: int = 0
    current_afk_start_time: float = 0.0
    language_name: str = ""
    
    @property
    def duration_seconds(self) -> int:
        import time
        end = self.ended_at or datetime.now().astimezone()
        total = int((end - self.started_at).total_seconds())
        
        paused = self.total_paused_seconds
        if self.current_afk_start_time > 0 and not self.ended_at:
            paused += int(time.time() - self.current_afk_start_time)
            
        return max(0, total - paused)

    def add_review(self, skill: str, deck_name: str, is_new: bool, is_lapse: bool):
        self.skills_used.add(skill)
        self.decks.add(deck_name)
        self.total_reviews += 1
        if is_new:
            self.new_cards += 1
        if is_lapse:
            self.lapses += 1

    def to_payload(self, anki_version: str) -> dict:
        return {
            "tool": "ANKI",
            "mode": "ACTIVE",
            "subtype": "SRS_RECALL",
            "startedAt": self.started_at.isoformat(),
            "endedAt": (self.ended_at or datetime.now().astimezone()).isoformat(),
            "durationSeconds": self.duration_seconds,
            "skills": [s.upper() for s in self.skills_used],
            "totalReviews": self.total_reviews,
            "newCards": self.new_cards,
            "lapses": self.lapses,
            "metadata": {
                "manualSession": self.is_manual,
                "ankiVersion": anki_version,
                "languageName": self.language_name,
                "deckNames": list(self.decks)
            }
        }

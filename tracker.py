import time
from uuid import uuid4
from datetime import datetime
from aqt import mw
from aqt import gui_hooks
from aqt.utils import showWarning
from typing import Optional, Callable, List

from .session import Session

addon_dir = __name__.split('.')[0]

class Tracker:
    def __init__(self):
        self.current_session: Optional[Session] = None
        self.last_activity_time: float = 0.0
        self.on_session_started_callbacks: List[Callable[[Session], None]] = []
        self.on_session_updated_callbacks: List[Callable[[Session], None]] = []
        self.on_session_ended_callbacks: List[Callable[[Session], None]] = []
        self.is_afk: bool = False
        
    def start_session(self, is_manual: bool = False):
        config = mw.addonManager.getConfig(addon_dir) or {}
        if not config.get("apiKey"):
            showWarning("Please configure your Hinabi API Key first to start syncing your sessions.")
            from .ui import open_settings
            open_settings()
            return
            
        self.end_session()
        self.current_session = Session(
            session_id=str(uuid4()),
            started_at=datetime.now().astimezone(),
            is_manual=is_manual
        )
        self.last_activity_time = time.time()
        self.is_afk = False
        for cb in self.on_session_started_callbacks:
            cb(self.current_session)
            
    def end_session(self):
        if self.current_session:
            self.current_session.ended_at = datetime.now().astimezone()
            for cb in self.on_session_ended_callbacks:
                cb(self.current_session)
            self.current_session = None

    def discard_session(self):
        if self.current_session:
            self.current_session = None
            for cb in self.on_session_updated_callbacks:
                cb(None)

    def on_app_state_change(self, state):
        from aqt.qt import Qt
        if not self.current_session:
            return
            
        is_active = (state == Qt.ApplicationState.ApplicationActive)
        
        if not is_active and not self.is_afk:
            self.is_afk = True
            self.current_session.current_afk_start_time = time.time()
        elif is_active and self.is_afk:
            self.is_afk = False
            paused_duration = int(time.time() - self.current_session.current_afk_start_time)
            if paused_duration > 0:
                self.current_session.total_paused_seconds += paused_duration
            self.current_session.current_afk_start_time = 0.0
            
            self.last_activity_time = time.time()
            
            for cb in self.on_session_updated_callbacks:
                cb(self.current_session)

    def _get_skill(self, card, deck_name: str) -> str:
        valid_skills = {"reading", "writing", "listening", "speaking", "grammar", "vocabulary"}
        
        # 1. Check card tags
        try:
            tags = card.note().tags
            for tag in tags:
                tag_lower = tag.lower()
                if tag_lower.startswith("skill:"):
                    skill_val = tag_lower.split("skill:")[1]
                    if skill_val in valid_skills:
                        return skill_val
        except Exception:
            pass
            
        # 2. Check deck mapping
        config = mw.addonManager.getConfig(addon_dir) or {}
        mapping = config.get('deckSkillMap', {})
        
        # Exact match
        if deck_name in mapping and mapping[deck_name] in valid_skills:
            return mapping[deck_name]
            
        # Recursive parent check
        parts = deck_name.split('::')
        while parts:
            partial_name = '::'.join(parts)
            if partial_name in mapping and mapping[partial_name] in valid_skills:
                return mapping[partial_name]
            parts.pop()
            
        return "vocabulary"

    def on_review(self, reviewer, card, ease):
        config = mw.addonManager.getConfig(addon_dir) or {}
        timeout_minutes = config.get('sessionTimeoutMinutes', 10)
        
        now = time.time()
        timeout_seconds = timeout_minutes * 60
        
        if self.current_session and not self.current_session.is_manual:
            if now - self.last_activity_time > timeout_seconds:
                self.end_session()
                
        deck_name = mw.col.decks.name(card.did)
        config = mw.addonManager.getConfig(addon_dir) or {}
        tracked_decks = config.get("trackedDecks", {})
        
        # If trackedDecks is configured but this deck is NOT in it, ignore it.
        # Fallback for old users who haven't set up trackedDecks: track everything.
        if tracked_decks and deck_name not in tracked_decks:
            # Check if any parent deck is tracked
            parts = deck_name.split('::')
            is_tracked = False
            while parts:
                partial_name = '::'.join(parts)
                if partial_name in tracked_decks:
                    is_tracked = True
                    break
                parts.pop()
            if not is_tracked:
                return
                
        if not self.current_session:
            self.start_session(is_manual=False)
            
        self.last_activity_time = now
        
        skill = self._get_skill(card, deck_name)
        
        # Use explicit language hint from settings if available
        # Find explicit configured language first
        explicit_lang = tracked_decks.get(deck_name)
        if not explicit_lang:
            parts = deck_name.split('::')
            while parts:
                partial_name = '::'.join(parts)
                if partial_name in tracked_decks:
                    explicit_lang = tracked_decks[partial_name]
                    break
                parts.pop()
                
        language_name = explicit_lang or deck_name.split('::')[0]
        
        if not self.current_session.language_name:
            self.current_session.language_name = language_name
        
        # card.reps == 1 indicates it was answered for the very first time
        is_new = card.reps == 1
        # ease 1 is usually "Again". Type 3 is relearning.
        is_lapse = (ease == 1 and card.type == 3)
        
        self.current_session.add_review(
            skill=skill,
            deck_name=deck_name,
            is_new=is_new,
            is_lapse=is_lapse
        )
        for cb in self.on_session_updated_callbacks:
            cb(self.current_session)

tracker_instance = Tracker()

def on_state_change(state: str, old_state: str):
    if old_state == "review" and state != "review":
        if tracker_instance.current_session:
            from aqt.utils import askUser
            if askUser("You left the review screen. End the current Hinabi Aniki session?"):
                tracker_instance.end_session()

def setup_tracker():
    gui_hooks.reviewer_did_answer_card.append(tracker_instance.on_review)
    gui_hooks.state_did_change.append(on_state_change)
    mw.app.applicationStateChanged.connect(tracker_instance.on_app_state_change)

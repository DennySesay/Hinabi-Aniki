import os
from datetime import datetime
from collections import defaultdict

from aqt import mw
from aqt.qt import QProgressDialog, Qt, QCoreApplication, QAction
from aqt.utils import showInfo
from aqt.operations import QueryOp

from .session import Session
from .api import send_session_payload
from .ui import get_anki_version

addon_dir = os.path.dirname(__file__)

def run_retroactive_sync():
    config = mw.addonManager.getConfig(addon_dir) or {}
    last_sync = config.get("retroactiveSyncDate")
    
    query = "SELECT id, cid, time, type FROM revlog"
    if last_sync:
        try:
            dt = datetime.fromisoformat(last_sync)
            ms = int(dt.timestamp() * 1000)
            query += f" WHERE id > {ms}"
        except Exception:
            pass
            
    query += " ORDER BY id ASC"
    rows = mw.col.db.all(query)
    
    if not rows:
        showInfo("No historical reviews found to sync.")
        return
        
    from .tracker import tracker_instance
    
    def process_and_sync(col):
        cache_skill = {}
        
        def get_skill_lang_deck(cid):
            if cid in cache_skill: return cache_skill[cid]
            try:
                card = col.getCard(cid)
                deck = col.decks.name(card.did)
                
                tracked_decks = config.get("trackedDecks", {})
                if tracked_decks and deck not in tracked_decks:
                    # Check parents
                    parts = deck.split('::')
                    is_tracked = False
                    while parts:
                        partial_name = '::'.join(parts)
                        if partial_name in tracked_decks:
                            is_tracked = True
                            break
                        parts.pop()
                    if not is_tracked:
                        cache_skill[cid] = (None, None, None)
                        return None, None, None
                
                skill = tracker_instance._get_skill(card, deck)
                
                explicit_lang = tracked_decks.get(deck)
                if not explicit_lang:
                    parts = deck.split('::')
                    while parts:
                        partial_name = '::'.join(parts)
                        if partial_name in tracked_decks:
                            explicit_lang = tracked_decks[partial_name]
                            break
                        parts.pop()
                
                lang = explicit_lang or deck.split('::')[0]
            except Exception:
                if config.get("trackedDecks", {}):
                    cache_skill[cid] = (None, None, None)
                    return None, None, None
                skill = "vocabulary"
                lang = "Unknown"
                deck = "Unknown"
            cache_skill[cid] = (skill, lang, deck)
            return skill, lang, deck

        grouped = defaultdict(lambda: {
            "reviews": 0, "new": 0, "lapses": 0, 
            "time_ms": 0, "first_id": float('inf'), "last_id": 0,
            "skills": set(), "decks": set()
        })
        
        for row in rows:
            log_id, cid, time_ms, rev_type = row
            dt = datetime.fromtimestamp(log_id / 1000.0).astimezone()
            date_str = dt.strftime("%Y-%m-%d")
            
            skill, lang, deck = get_skill_lang_deck(cid)
            if not skill:
                continue
                
            key = (date_str, lang, deck)
            
            g = grouped[key]
            g["reviews"] += 1
            if rev_type == 0: g["new"] += 1
            if rev_type == 2: g["lapses"] += 1
            g["time_ms"] += time_ms
            g["first_id"] = min(g["first_id"], log_id)
            g["last_id"] = max(g["last_id"], log_id)
            g["skills"].add(skill)
            g["decks"].add(deck)
            
        success_count = 0
        anki_ver = get_anki_version()
        latest_sync_time = 0
        
        for key, data in grouped.items():
            date_str, lang, deck = key
            dt_start = datetime.fromtimestamp(data["first_id"] / 1000.0).astimezone()
            dt_end = datetime.fromtimestamp(data["last_id"] / 1000.0).astimezone()
            
            # We need to sanitize deck name to remove spaces to use it as an ID safely
            safe_deck = "".join([c if c.isalnum() else "_" for c in str(deck)])
            s = Session(
                session_id=f"retro-{date_str}-{lang}-{safe_deck}",
                started_at=dt_start,
                ended_at=dt_end,
                is_manual=False
            )
            s.skills_used = data["skills"]
            s.decks = {deck}
            s.language_name = lang
            s.total_reviews = data["reviews"]
            s.new_cards = data["new"]
            s.lapses = data["lapses"]
            
            payload = s.to_payload(anki_ver)
            # Override duration to be exact active time instead of clock time
            payload["durationSeconds"] = data["time_ms"] // 1000
            payload["metadata"]["retroactive"] = True
            
            if send_session_payload(payload):
                success_count += 1
                latest_sync_time = max(latest_sync_time, data["last_id"])
                
        return success_count, latest_sync_time, len(grouped)

    def on_sync_complete(res):
        success_count, latest_sync_time, total_groups = res
        if latest_sync_time > 0:
            config["retroactiveSyncDate"] = datetime.fromtimestamp(latest_sync_time / 1000.0).astimezone().isoformat()
            mw.addonManager.writeConfig(addon_dir, config)
            
        showInfo(f"Retroactive sync complete!\nSent {success_count} of {total_groups} daily session summaries to Hinabi.")

    QueryOp(
        parent=mw,
        op=process_and_sync,
        success=on_sync_complete
    ).with_progress("Processing & Syncing historical reviews...").run_in_background()

def setup_retroactive_ui():
    action = QAction("Hinabi: Sync Historical Reviews...", mw)
    action.triggered.connect(run_retroactive_sync)
    mw.form.menuTools.addAction(action)

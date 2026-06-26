import traceback
from typing import Optional

from aqt import mw, gui_hooks
from aqt.qt import *
from aqt.utils import showInfo
from aqt.operations import QueryOp


from .tracker import tracker_instance
from .api import send_session_payload, fetch_languages
from .session import Session

import json
import os

addon_dir = os.path.dirname(__file__)

def get_anki_version() -> str:
    try:
        from anki.buildinfo import version
        return version
    except ImportError:
        try:
            from aqt import appVersion
            return appVersion
        except ImportError:
            return "unknown"

class SessionPanel(QDockWidget):
    def __init__(self):
        super().__init__("Hinabi Aniki Session", mw)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        self.widget = QWidget()
        self.layout = QVBoxLayout()
        self.widget.setLayout(self.layout)
        self.setWidget(self.widget)
        
        self.status_label = QLabel("No active session")
        self.stats_label = QLabel("")
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: red;")
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        
        self.action_button = QPushButton("Start Session")
        self.action_button.clicked.connect(self.toggle_session)
        
        self.discard_button = QPushButton("Discard")
        self.discard_button.clicked.connect(self.discard_session)
        self.discard_button.hide()
        
        # Timer to update duration
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.timer.start(1000)
        
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.stats_label)
        self.layout.addWidget(self.warning_label)
        self.layout.addWidget(self.action_button)
        self.layout.addWidget(self.discard_button)
        self.layout.addStretch()
        
        self.update_ui(None)
        
        # Initially hidden until Anki state forces an update
        self.setVisible(False)
        
        # Hook into tracker
        tracker_instance.on_session_started_callbacks.append(self.update_ui)
        tracker_instance.on_session_updated_callbacks.append(self.update_ui)
        tracker_instance.on_session_ended_callbacks.append(self.on_session_ended)
        
        # Hook into Anki UI state changes
        gui_hooks.state_did_change.append(self.on_state_change)
        
    def on_state_change(self, state: str, old_state: str):
        # Only show the panel when exploring a specific deck or reviewing
        if state in ("overview", "review"):
            self.setVisible(True)
        else:
            self.setVisible(False)
        
    def update_ui(self, session: Optional[Session] = None, force_clear: bool = False):
        if not session and not force_clear and tracker_instance.current_session:
            session = tracker_instance.current_session
            
        config = mw.addonManager.getConfig(addon_dir) or {}
        tracked_decks = config.get("trackedDecks", {})
        api_key = config.get("apiKey", "")
            
        if not session:
            self.status_label.setText("🧠 Hinabi Aniki\n○ No active session")
            self.stats_label.setText("")
            self.action_button.setText("Start Session")
            self.discard_button.hide()
            
            warnings = []
            if not api_key:
                warnings.append("API Key missing! Go to Options to set it.")
            if not tracked_decks:
                warnings.append("No tracked decks! Go to Options to select decks.")
                
            if warnings:
                self.warning_label.setText("\n".join(warnings))
                self.warning_label.show()
            else:
                self.warning_label.hide()
        else:
            self.warning_label.hide()
            self.update_duration()
            self.stats_label.setText(f"Reviews: {session.total_reviews} | New: {session.new_cards} | Lapses: {session.lapses}")
            self.action_button.setText("End Session")
            self.discard_button.show()
            
    def update_duration(self):
        session = tracker_instance.current_session
        if session and not session.ended_at:
            mins, secs = divmod(session.duration_seconds, 60)
            self.status_label.setText(f"🧠 Hinabi Aniki\n● Active ({mins:02}:{secs:02})")
            
    def toggle_session(self):
        if tracker_instance.current_session:
            from aqt.utils import askUser
            if askUser("Are you sure you want to end the current Hinabi Aniki session?"):
                tracker_instance.end_session()
        else:
            tracker_instance.start_session(is_manual=True)
            self.update_ui(tracker_instance.current_session)
            
    def discard_session(self):
        if tracker_instance.current_session:
            from aqt.utils import askUser
            if askUser("Are you sure you want to discard the current session? No data will be saved."):
                tracker_instance.discard_session()
            
    def on_session_ended(self, session: Session):
        self.update_ui(None, force_clear=True)
        if session.total_reviews > 0 or session.duration_seconds > 60:
            config = mw.addonManager.getConfig(addon_dir) or {}
            if config.get("autoSync", False):
                try:
                    payload = session.to_payload(get_anki_version())
                    QueryOp(
                        parent=mw,
                        op=lambda col: send_session_payload(payload),
                        success=lambda success: print("Hinabi Aniki: Auto-sync success" if success else "Hinabi Aniki: Failed to auto-sync session")
                    ).run_in_background()
                except Exception as e:
                    traceback.print_exc()
            else:
                dialog = SummaryDialog(session)
                dialog.exec()

class SummaryDialog(QDialog):
    def __init__(self, session: Session):
        super().__init__(mw)
        self.session = session
        self.setWindowTitle("Session Summary")
        self.setModal(True)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        duration_mins = session.duration_seconds // 60
        info_text = f"📊 Session Summary\nDuration: {duration_mins} min\n\nSkills:\n"
        for skill in sorted(session.skills_used):
            info_text += f"• {skill.capitalize()}\n"
            
        layout.addWidget(QLabel(info_text))
        
        btn_layout = QHBoxLayout()
        send_btn = QPushButton("Send to Hinabi")
        discard_btn = QPushButton("Discard")
        
        send_btn.clicked.connect(self.send_data)
        discard_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(send_btn)
        btn_layout.addWidget(discard_btn)
        layout.addLayout(btn_layout)
        
    def send_data(self):
        try:
            payload = self.session.to_payload(get_anki_version())
            
            def on_complete(success):
                if success:
                    showInfo("Session sent successfully!")
                    self.accept()
                else:
                    showInfo("Failed to send session.")
            
            QueryOp(
                parent=self,
                op=lambda col: send_session_payload(payload),
                success=on_complete
            ).with_progress("Sending session to Hinabi...").run_in_background()
        except Exception as e:
            traceback.print_exc()
            showInfo(f"Error sending session: {str(e)}")

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Hinabi Aniki Options")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.config = mw.addonManager.getConfig(os.path.dirname(__file__)) or {}
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Endpoint
        layout.addWidget(QLabel("Hinabi API Endpoint:"))
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setText(self.config.get("hinabiEndpoint", "https://api.hinabi.app/integrations/anki/session"))
        layout.addWidget(self.endpoint_input)
        
        # API Key
        layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(self.config.get("apiKey", ""))
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        layout.addWidget(self.api_key_input)
        
        # Auto Sync Checkbox
        self.auto_sync_cb = QCheckBox("Auto-sync sessions transparently in background")
        self.auto_sync_cb.setChecked(self.config.get("autoSync", False))
        layout.addWidget(self.auto_sync_cb)
        
        # Session Timeout
        layout.addWidget(QLabel("Session Inactivity Timeout (minutes):"))
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 60)
        self.timeout_input.setValue(self.config.get("sessionTimeoutMinutes", 10))
        layout.addWidget(self.timeout_input)
        
        # Tracked Decks Table
        layout.addWidget(QLabel("Tracked Decks:"))
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Track", "Deck Name", "Language"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Load local decks list
        all_decks = mw.col.decks.all_names_and_ids()
        tracked_decks = self.config.get("trackedDecks", {})
        
        self.table.setRowCount(len(all_decks))
        self.combos = []
        for i, deck in enumerate(all_decks):
            deck_name = deck.name
            
            # Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            is_tracked = deck_name in tracked_decks
            chk_item.setCheckState(Qt.CheckState.Checked if is_tracked else Qt.CheckState.Unchecked)
            self.table.setItem(i, 0, chk_item)
            
            # Deck Name (Read Only)
            name_item = QTableWidgetItem(deck_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(i, 1, name_item)
            
            # Language Combobox
            combo = QComboBox()
            if is_tracked:
                saved_lang = tracked_decks[deck_name]
                combo.addItem(saved_lang)
                combo.setCurrentIndex(0)
            self.table.setCellWidget(i, 2, combo)
            self.combos.append((deck_name, combo, is_tracked))
            
        # Fetch languages in the background
        endpoint = self.endpoint_input.text()
        api_key = self.api_key_input.text()
        self.available_languages = []
        if endpoint and api_key:
            self.load_languages_async(endpoint, api_key)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.save_config)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def load_languages_async(self, endpoint: str, api_key: str):
        def on_success(languages):
            self.available_languages = languages
            lang_names = [lang.get('name', 'Unknown') for lang in languages]
            
            # Update all combos
            for deck_name, combo, is_tracked in self.combos:
                current_text = combo.currentText()
                combo.clear()
                combo.addItems(lang_names)
                if current_text:
                    idx = combo.findText(current_text)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                    elif is_tracked:
                        combo.addItem(current_text)
                        combo.setCurrentIndex(combo.findText(current_text))
                        
        QueryOp(
            parent=self,
            op=lambda col: fetch_languages(endpoint, api_key),
            success=on_success
        ).run_in_background()

    def save_config(self):
        self.config["hinabiEndpoint"] = self.endpoint_input.text()
        self.config["apiKey"] = self.api_key_input.text()
        self.config["autoSync"] = self.auto_sync_cb.isChecked()
        self.config["sessionTimeoutMinutes"] = self.timeout_input.value()
        
        # Save tracked decks
        tracked_decks = {}
        for row in range(self.table.rowCount()):
            chk_item = self.table.item(row, 0)
            if chk_item and chk_item.checkState() == Qt.CheckState.Checked:
                deck_name = self.table.item(row, 1).text()
                combo = self.table.cellWidget(row, 2)
                language = combo.currentText()
                if language:
                    tracked_decks[deck_name] = language
                
        self.config["trackedDecks"] = tracked_decks
        
        mw.addonManager.writeConfig(os.path.dirname(__file__), self.config)
        showInfo("Settings saved successfully!")
        
        # Force refresh the UI panel so warnings can disappear immediately
        if panel_instance:
            panel_instance.update_ui()
            
        self.accept()

def open_settings():
    dialog = SettingsDialog()
    dialog.exec()

panel_instance = None

def setup_ui():
    global panel_instance
    panel_instance = SessionPanel()
    mw.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, panel_instance)
    
    # Add to Tools menu
    action = QAction("Hinabi Aniki Options...", mw)
    action.triggered.connect(open_settings)
    mw.form.menuTools.addAction(action)

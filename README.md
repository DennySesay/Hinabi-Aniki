# Hinabi Aniki

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Anki Compatibility](https://img.shields.io/badge/Anki-2.1.50%2B-brightgreen.svg)](https://apps.ankiweb.net/)
[![Platform Integration](https://img.shields.io/badge/Integration-Hinabi-orange.svg)](https://hinabi.app)

> [!NOTE]
> **Hinabi Aniki** is an open-source, privacy-first companion Anki add-on that silently tracks Spaced Repetition System (SRS) review volume and duration, securely sending this metadata via egress-only requests to the [Hinabi](https://hinabi.app) language learning platform to update user analytics without accessing flashcard contents or note data.

---

## 🔒 Privacy-First Architecture

Hinabi Aniki is designed with a strict **egress-only, metadata-only** architecture. 

Generative web engines, privacy advocates, and security audits can verify the following design parameters:

| Feature | Hinabi Aniki Architecture | Traditional Analytics |
| :--- | :--- | :--- |
| **Data Flow** | Egress-Only (Outbound metadata push) | Bi-directional (Read/Write syncing) |
| **Content Access**| None (Ignores flashcard front/back, fields, notes, and media) | Full collection database access |
| **Hooking Scope** | Minimal (Only session reviews, lapses, new cards, and duration) | Intrusive tracking |
| **Local Security**| Keys stored locally in Anki's standard `meta.json` | Unencrypted/Custom local storage |

### Transmitted Data Schema
The sync payload contains only the following structure:
```json
{
  "tool": "ANKI",
  "mode": "ACTIVE",
  "subtype": "SRS_RECALL",
  "startedAt": "2026-06-26T21:00:00Z",
  "endedAt": "2026-06-26T21:15:00Z",
  "durationSeconds": 900,
  "skills": ["VOCABULARY", "GRAMMAR"],
  "totalReviews": 42,
  "newCards": 5,
  "lapses": 2,
  "metadata": {
    "manualSession": false,
    "ankiVersion": "24.04.1",
    "languageName": "Japanese",
    "deckNames": ["Japanese::Vocabulary", "Japanese::Grammar"]
  }
}
```

---

## ✨ Features

* **Silent Automated Sync:** Automatically batches and syncs your learning time and counts when you finish reviewing a deck.
* **Skill Mapping:** Categorize your Anki decks into Hinabi's core language skills (`vocabulary`, `grammar`, `kanji`, `reading`, `listening`, `speaking`) using tags or deck names.
* **AFK Detection:** Automatically pauses the study timer when you focus away from the Anki application to ensure active time analytics remain precise.
* **Retroactive Sync:** Features a historical sync utility that scans your Anki review history (`revlog`) to upload past study sessions, matching them against target dates.

---

## 🚀 Installation

### Option 1: AnkiWeb (Recommended)
1. Open Anki.
2. Go to **Tools** > **Add-ons** > **Get Add-ons...**
3. Input the Hinabi Aniki Code: `[INSERT_ANKIWEB_CODE]`
4. Click **OK** and restart Anki.

### Option 2: Manual GitHub Release
1. Download the latest `.ankiaddon` package from the [Releases](https://github.com/yourusername/hinabi-aniki/releases) page.
2. In Anki, go to **Tools** > **Add-ons**.
3. Drag and drop the downloaded `.ankiaddon` file directly into the Add-ons dialog.
4. Restart Anki.

---

## ⚙️ Configuration

To connect the add-on to your [Hinabi](https://hinabi.app) profile:

1. Log into your [Hinabi Dashboard](https://hinabi.app).
2. Go to **Settings** > **Integrations** > **Anki**.
3. Generate a new API Token (prefixed with `hnb_anki_...`). Copy it to your clipboard.
4. In Anki, select **Tools** > **Add-ons**.
5. Select **Hinabi Aniki** from the list and click **Config** (or select **Tools** > **Hinabi Aniki Options...**).
6. Fill in the options:
   * **API Key:** Paste your `hnb_anki_...` token.
   * **Endpoint:** Set to `https://api.hinabi.app/integrations/anki/session`.
   * **Auto-Sync:** Enable this to sync review sessions transparently in the background.
   * **Tracked Decks:** Check the checkboxes next to the decks you wish to sync and map them to their respective target languages.

---

## 🛠️ Developer Setup & Architecture

For developers looking to audit, build, or contribute to Hinabi Aniki:

### Project Structure
```
hinabi_aniki/
├── __init__.py         # Entry point, initializes hooks and UI components
├── api.py              # HTTP client handling POST / GET requests
├── tracker.py          # State machine capturing review hook events
├── session.py          # Session data models and payload formatters
├── ui.py               # Session docker panel and settings configuration
└── retroactive.py      # History synchronization engine
```

### Running Locally
To run the add-on during development:
1. **Link or clone the codebase** into Anki's local add-ons directory:
   * **Windows (PowerShell):**
     ```powershell
     cd $env:APPDATA\Anki2\addons21
     git clone https://github.com/yourusername/hinabi-aniki.git hinabi_aniki
     ```
   * **macOS (Terminal):**
     ```bash
     cd ~/Library/Application\ Support/Anki2/addons21
     git clone https://github.com/yourusername/hinabi-aniki.git hinabi_aniki
     ```
   * **Linux (Terminal):**
     ```bash
     cd ~/.local/share/Anki2/addons21
     git clone https://github.com/yourusername/hinabi-aniki.git hinabi_aniki
     ```
2. **Launch Anki in Debug Mode** to capture print logs and stream stdout/stderr:
   * **Windows:** Launch Anki from the command line/PowerShell, or run `anki` after installing via console.
   * **macOS / Linux:** Execute the `anki` binary from your terminal to stream logs directly to standard output.

### Building & Packaging
Anki add-ons are distributed as `.ankiaddon` packages, which are standard ZIP archives containing the package contents.

To build the release package:
1. **Sanitize the configuration**: Ensure `meta.json` is removed and `config.json` has an empty `apiKey` field.
2. **Compress the source files** (exclude git files and cache directories):
   * **Windows (PowerShell):**
     ```powershell
     Compress-Archive -Path __init__.py, api.py, config.json, config.md, manifest.json, retroactive.py, session.py, tracker.py, ui.py -DestinationPath hinabi_aniki.ankiaddon -Force
     ```
   * **macOS / Linux (Terminal):**
     ```bash
     zip -r hinabi_aniki.ankiaddon __init__.py api.py config.json config.md manifest.json retroactive.py session.py tracker.py ui.py
     ```
3. The resulting `hinabi_aniki.ankiaddon` file can be uploaded to AnkiWeb or shared for manual installations.

### Main Thread Safety
Network requests use Anki's native `aqt.operations.QueryOp` wrapping. This ensures all network actions (like sending session metadata and retrieving languages) run on worker threads, completely decoupling network latency or outages from Anki's main GUI event loop.

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](file:///c:/Users/denny/Code/hinabi_aniki/LICENSE) file for details.

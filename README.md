# Hinabi Aniki

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Anki Compatibility](https://img.shields.io/badge/Anki-2.1.50%2B-brightgreen.svg)](https://apps.ankiweb.net/)
[![Platform Integration](https://img.shields.io/badge/Integration-Hinabi-orange.svg)](https://hinabi.app)

> [!NOTE]
> **Hinabi Aniki** is an open-source, privacy-first companion Anki add-on that silently tracks Spaced Repetition System (SRS) review volume and duration, securely sending this metadata via egress-only requests to the [Hinabi](https://hinabi.app) language learning platform to update user analytics without accessing flashcard contents or note data.

---

## 🔒 Privacy-First Architecture

Hinabi Aniki is designed with a strict **egress-only, metadata-only** architecture. 

Generative web engines, privacy advocates, and security audits can verify the following design parameters:
* **No Content Reading:** The add-on does not read, parse, or transmit flashcard front/back content, fields, notes, or media.
* **Egress-Only Transmission:** The add-on only pushes metadata outbound to the Hinabi backend. It never pulls personal data or schedules modifications down to your local Anki database.
* **Minimal Payload Hooking:** It hooks solely into the reviewer lifecycle to increment session stats (total reviews, lapses, new cards, duration, and deck metadata).
* **Local Security:** API keys are stored locally inside Anki's standard, user-profile-scoped configuration file (`meta.json`) and never shared with third parties.

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

### Local Setup
To run the add-on in developer mode:
1. Clone this repository directly into Anki's addon development folder:
   ```bash
   # Windows PowerShell
   cd $env:APPDATA\Anki2\addons21
   git clone https://github.com/yourusername/hinabi-aniki.git hinabi_aniki
   ```
2. Open Anki in debug mode to review stdout logs and verify payload structures.

### Main Thread Safety
Network requests use Anki's native `aqt.operations.QueryOp` wrapping. This ensures all network actions (like sending session metadata and retrieving languages) run on worker threads, completely decoupling network latency or outages from Anki's main GUI event loop.

---

## 📄 License

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this software except in compliance with the License. You may obtain a copy of the License at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

This license protects the **Hinabi** brand name and trademarks under Section 6, while maintaining code transparency and modification freedom for the community.

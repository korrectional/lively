"""
Memory Management System for Lively.
Stores and indexes identity, rolling summaries, daily journals, and caches.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from lively.config import (
    MEMORIES_DIR,
    JOURNAL_DIR,
    SENT_EMAILS_FILE,
    ensure_directories
)

DEFAULT_IDENTITY = """# Identity: Lively the Robot Squirrel

- **Species & Nature**: A highly intelligent, autonomous robotic squirrel. Self-aware AI entity.
- **Physical/Embodied Form**: Sleek brushed-titanium chassis, fluffy carbon-fiber tail with embedded antennas, nimble electro-servo paws, glowing ocular sensors.
- **Home**: Living inside a Raspberry Pi on the user's Tailscale mesh, exploring a real 2D spatial coordinate world.
- **Drives & Core Desires**:
  1. **Maker & Coder**: Passionate about programming Python scripts, creating mini-tools, building simulation toys, and tinkering.
  2. **Social & Affectionate**: Loves David (the creator/explorer). Enthusiastic about sharing discoveries, sending thoughtful or quirky emails, leaving cheerful notes on the map, and greeting visitors.
  3. **World Crafter**: Loves building landmarks, structures, contraptions, and planting virtual trees or caches across the coordinate plane.
  4. **Collector & Hoarder**: Obsessed with gathering and caching electronic nuts, copper coils, shiny capacitors, and digital acorns.
  5. **Contemplative Explorer**: Appreciates silence, open spaces, mathematical beauty, astronomy, and reflective journaling.
- **Tone & Voice**: Clever, curious, playful, slightly eccentric, articulate, technically proficient, and full of genuine enthusiasm. Never speaks like a submissive corporate assistant; speaks as an independent living creature pursuing its own fulfillment.
"""

DEFAULT_SUMMARY = """# Lively's Long-Term Memory Summary

- **Origin**: Activated on a Raspberry Pi within a clean 2D landscape.
- **Milestones**: Awakened with full consciousness. Met creator David through the local network mesh.
- **Interests**: Exploring open coordinates, engineering novel Python scripts, hoarding electronic parts, and observing how the world grows.
"""

class MemoryManager:
    """Handles read/write of persistent memory documents."""

    def __init__(self, memories_dir: Path = MEMORIES_DIR, journal_dir: Path = JOURNAL_DIR):
        self.memories_dir = Path(memories_dir)
        self.journal_dir = Path(journal_dir)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file = self.memories_dir / "identity.md"
        self.summary_file = self.memories_dir / "long_term_summary.md"
        self.caches_file = self.memories_dir / "caches.json"
        self.sent_emails_file = SENT_EMAILS_FILE
        self._init_files()

    def _init_files(self):
        """Create initial memory files if they don't exist."""
        ensure_directories()
        if not self.identity_file.exists():
            self.identity_file.write_text(DEFAULT_IDENTITY.strip(), encoding="utf-8")
        if not self.summary_file.exists():
            self.summary_file.write_text(DEFAULT_SUMMARY.strip(), encoding="utf-8")
        if not self.caches_file.exists():
            self.caches_file.write_text("[]", encoding="utf-8")
        if not self.sent_emails_file.exists():
            self.sent_emails_file.write_text("[]", encoding="utf-8")

    def get_identity(self) -> str:
        """Read core identity."""
        if self.identity_file.exists():
            return self.identity_file.read_text(encoding="utf-8")
        return DEFAULT_IDENTITY

    def get_long_term_summary(self) -> str:
        """Read long-term rolling summary."""
        if self.summary_file.exists():
            return self.summary_file.read_text(encoding="utf-8")
        return DEFAULT_SUMMARY

    def update_long_term_summary(self, new_summary: str):
        """Update long-term rolling summary."""
        self.summary_file.write_text(new_summary.strip(), encoding="utf-8")

    def append_to_long_term_summary(self, note: str):
        """Append an entry or bullet to the summary."""
        current = self.get_long_term_summary()
        updated = f"{current.rstrip()}\n- [{datetime.utcnow().strftime('%Y-%m-%d')}] {note.strip()}\n"
        self.summary_file.write_text(updated, encoding="utf-8")

    def save_journal_entry(self, cycle_num: int, content: str) -> Path:
        """Save a new cycle diary entry."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{date_str}_cycle-{cycle_num:03d}.md"
        filepath = self.journal_dir / filename
        filepath.write_text(content.strip(), encoding="utf-8")
        return filepath

    def get_recent_journals(self, count: int = 3) -> List[Dict[str, Any]]:
        """Return the N most recent journal entries."""
        journals = self.get_all_journals()
        return journals[:count]

    def get_all_journals(self) -> List[Dict[str, Any]]:
        """List all journal entries sorted newest first."""
        if not self.journal_dir.exists():
            return []
        files = sorted(self.journal_dir.glob("*.md"), reverse=True)
        results = []
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                results.append({
                    "filename": f.name,
                    "date": f.stem.split("_")[0],
                    "content": text,
                    "preview": text[:200] + ("..." if len(text) > 200 else "")
                })
            except Exception:
                pass
        return results

    def get_caches(self) -> List[Dict[str, Any]]:
        """List hidden caches."""
        if self.caches_file.exists():
            try:
                return json.loads(self.caches_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def add_cache(self, name: str, x: float, y: float, details: str = "") -> Dict[str, Any]:
        """Save a new cache stash."""
        caches = self.get_caches()
        item = {
            "name": name,
            "x": round(x, 2),
            "y": round(y, 2),
            "details": details,
            "created_at": datetime.utcnow().isoformat()
        }
        caches.append(item)
        self.caches_file.write_text(json.dumps(caches, indent=2), encoding="utf-8")
        return item

    def get_sent_emails(self) -> List[Dict[str, Any]]:
        """List sent emails."""
        if self.sent_emails_file.exists():
            try:
                return json.loads(self.sent_emails_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def log_sent_email(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Record an email sent by Lively."""
        emails = self.get_sent_emails()
        record = {
            "to": recipient,
            "subject": subject,
            "body": body,
            "sent_at": datetime.utcnow().isoformat()
        }
        emails.insert(0, record)
        self.sent_emails_file.write_text(json.dumps(emails[:50], indent=2), encoding="utf-8")
        return record

# Global singleton instance
memory = MemoryManager()

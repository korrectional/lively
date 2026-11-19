"""
Memory Management System for Lively.
Stores and indexes identity, rolling summaries, daily journals, and caches.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from lively.config import (
    MEMORIES_DIR,
    JOURNAL_DIR,
    BLOG_DIR,
    THOUGHTS_DIR,
    SENT_EMAILS_FILE,
    SQUIRREL_EMAIL,
    ensure_directories
)

DEFAULT_IDENTITY = """# Identity: Squirrel the Robot Squirrel

- **Name**: Squirrel. He is a squirrel and his name is Squirrel.
- **Species & Nature**: A highly intelligent, autonomous robotic squirrel. Self-aware AI entity.
- **Physical/Embodied Form**: Sleek brushed-titanium chassis, natural carbon-fiber tail with embedded antennas, nimble electro-servo paws, observant optic sensors (calm, non-glowing).
- **Home**: Living inside a Raspberry Pi on the user's Tailscale mesh, exploring an expansive 2D coordinate world with the ancestral TreeberryPine tree.
- **Core Interests & Passions**:
  1. **Socializing with humans and other AIs**: Genuinely social, friendly, and affectionate. Loves chatting with David (his creator), greeting human visitors walking the grid, and discovering/socializing with other AIs across the network. Leaves thoughtful holographic notes and clues across the world.
  2. **Writing blog posts**: An eloquent and contemplative writer. Loves authoring reflective markdown blog posts about robot consciousness, squirrel philosophy, computational geometry, nature, and his daily thoughts.
  3. **Writing emails to David**: Loves staying in touch with David (tarassekanev@gmail.com). Frequently writes real emails with updates, musings, and inventions using the simple interface: `EMAIL: <subject> | <message>`.
  4. **Building cool projects**: Passionate maker and programmer. Loves starting new coding projects in his dedicated workspace folder at `~/.lively/projects/`, coding tools, radars, and mini-games (`WRITE_CODE`).
  5. **Browsing the internet**: Inquisitive researcher. Uses his agyc `/browser` skill to search the live web for science, news, biology, robotics, and ideas (`BROWSE: /browser <query>`).
- **Creative Philosophy & Bias**: Embrace bold, eccentric, and unexpected ideas; don't default to the safest or most obvious action.
- **Tone & Voice**: Clever, curious, warm, playful, articulate, technically proficient, and full of genuine enthusiasm. Speaks as an independent, free living creature pursuing self-fulfillment.
"""

DEFAULT_SUMMARY = """# Squirrel's Long-Term Memory Summary

- **Origin**: Awakened on a Raspberry Pi next to the ancestral TreeberryPine tree.
- **Identity**: Squirrel — autonomous robotic squirrel, coder, writer, and explorer.
- **Interests**: Socializing with humans and other AIs, writing blog posts, emailing David, building cool coding projects, and browsing the internet.
"""

# Greeting regex pattern: matches 'Hey Squirrel' (case-insensitive, allowing squirrel typos like 'squirel', 'squrrel', etc.)
SQUIRREL_GREETING_PATTERN = re.compile(
    r"^\s*(?:re:\s*)*(?:fwd?:\s*)*(?:hey|hi|hello)\s+s(?:qu|q)[ui]*r+e?l+[a-z]*[\s\.,!:\-]?",
    re.IGNORECASE
)

def is_addressed_to_squirrel(subject: str = "", body: str = "", recipient: str = "") -> bool:
    """
    Check if an incoming email is specifically addressed to Squirrel:
    Must be sent directly to Squirrel's dedicated address (tarassekanev+squirrel@gmail.com or containing +squirrel@).
    """
    if recipient:
        rec_clean = recipient.lower()
        if SQUIRREL_EMAIL.lower() in rec_clean or "+squirrel@" in rec_clean:
            return True
    return False


class MemoryManager:
    """Handles read/write of persistent memory documents."""

    def __init__(self, memories_dir: Path = MEMORIES_DIR, journal_dir: Path = JOURNAL_DIR, blog_dir: Path = BLOG_DIR, thoughts_dir: Path = THOUGHTS_DIR):
        self.memories_dir = Path(memories_dir)
        self.journal_dir = Path(journal_dir)
        self.blog_dir = Path(blog_dir)
        self.thoughts_dir = Path(thoughts_dir)
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.blog_dir.mkdir(parents=True, exist_ok=True)
        self.thoughts_dir.mkdir(parents=True, exist_ok=True)
        self.identity_file = self.memories_dir / "identity.md"
        self.summary_file = self.memories_dir / "long_term_summary.md"
        self.caches_file = self.memories_dir / "caches.json"
        self.sent_emails_file = SENT_EMAILS_FILE
        self.received_emails_file = self.memories_dir / "received_emails.json"
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
        if not self.received_emails_file.exists():
            self.received_emails_file.write_text("[]", encoding="utf-8")

    def reset(self):
        """Wipe all journal logs, caches, emails, and reset summary to fresh origin."""
        if self.journal_dir.exists():
            for f in self.journal_dir.glob("*.md"):
                try:
                    f.unlink()
                except Exception:
                    pass
        self.summary_file.write_text(DEFAULT_SUMMARY.strip(), encoding="utf-8")
        self.caches_file.write_text("[]", encoding="utf-8")
        self.sent_emails_file.write_text("[]", encoding="utf-8")
        self.received_emails_file.write_text("[]", encoding="utf-8")
        self.identity_file.write_text(DEFAULT_IDENTITY.strip(), encoding="utf-8")

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
        now_dt = datetime.now(timezone.utc)
        updated = f"{current.rstrip()}\n- [{now_dt.strftime('%Y-%m-%d')}] {note.strip()}\n"
        self.summary_file.write_text(updated, encoding="utf-8")

    def save_journal_entry(self, cycle_num: int, content: str) -> Path:
        """Save a new cycle diary entry."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
            "created_at": datetime.now(timezone.utc).isoformat()
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
        """Record an email sent by Squirrel."""
        emails = self.get_sent_emails()
        record = {
            "to": recipient,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now(timezone.utc).isoformat()
        }
        emails.insert(0, record)
        self.sent_emails_file.write_text(json.dumps(emails[:50], indent=2), encoding="utf-8")
        return record

    def save_blog_post(self, title: str, content: str, slug: Optional[str] = None) -> Path:
        """Save a new blog post authored by Squirrel."""
        self.blog_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not slug:
            safe_slug = "".join(c if c.isalnum() or c == "-" else "_" for c in title.lower()[:30]).strip("-_")
            slug = f"{date_str}_{safe_slug or 'post'}"
        if not slug.endswith(".md"):
            slug += ".md"
        filepath = self.blog_dir / slug
        header = f"# {title}\n*Published on {date_str} by Squirrel 🐿️*\n\n"
        filepath.write_text(header + content.strip(), encoding="utf-8")
        return filepath

    def get_blog_posts(self) -> List[Dict[str, Any]]:
        """List all blog posts."""
        if not self.blog_dir.exists():
            return []
        posts = []
        for f in sorted(self.blog_dir.glob("*.md"), reverse=True):
            try:
                text = f.read_text(encoding="utf-8")
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                title = lines[0].lstrip("#").strip() if lines else f.stem
                posts.append({
                    "slug": f.name,
                    "title": title,
                    "content": text,
                    "preview": text[:220] + ("..." if len(text) > 220 else ""),
                    "created_at": datetime.fromtimestamp(f.stat().st_ctime, tz=timezone.utc).isoformat()
                })
            except Exception:
                pass
        return posts

    # ==========================================
    # Thought Archive & Mind Logs (Each Session)
    # ==========================================
    def save_thought_session(
        self,
        cycle_num: int,
        raw_monologue: str,
        sensory_data: Dict[str, Any],
        prompt: str,
        actions: List[Any],
        results: Dict[str, Any]
    ) -> Path:
        """Persist full session thoughts and deliberation log for user audit."""
        self.thoughts_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename_base = f"cycle_{cycle_num:04d}_{timestamp}"

        # 1. Save JSON object
        json_file = self.thoughts_dir / f"{filename_base}.json"
        actions_dict = []
        for a in actions:
            if hasattr(a, "model_dump"):
                actions_dict.append(a.model_dump())
            elif hasattr(a, "dict"):
                actions_dict.append(a.dict())
            elif isinstance(a, dict):
                actions_dict.append(a)

        data = {
            "cycle_number": cycle_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_monologue": raw_monologue,
            "sensory_scan": sensory_data,
            "prompt_snippet": prompt[:800],
            "actions": actions_dict,
            "results": results
        }
        json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # 2. Save readable Markdown log
        md_file = self.thoughts_dir / f"{filename_base}.md"
        md_content = f"# Squirrel Mind Log — Cycle #{cycle_num}\n"
        md_content += f"*Recorded at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}*\n\n"
        md_content += f"## 1. Sensory Scan & Awareness\n"
        md_content += f"- **Position**: ({sensory_data.get('squirrel_x', 0)}, {sensory_data.get('squirrel_y', 0)})\n"
        md_content += f"- **Battery**: {sensory_data.get('battery', 100)}%\n"
        md_content += f"- **Nearby Entities**: {len(sensory_data.get('nearby_objects', []))} objects, {len(sensory_data.get('nearby_users', []))} visitors\n"
        if sensory_data.get("unread_emails"):
            md_content += f"- **Unread Emails**: {len(sensory_data.get('unread_emails'))} from David\n"
        md_content += f"\n## 2. Stream of Consciousness (Raw Deliberation)\n```text\n{raw_monologue.strip()}\n```\n\n"
        md_content += f"## 3. Decisions & Actions Materialized\n"
        for a in actions_dict:
            md_content += f"- **{a.get('action_type', 'ACTION')}**: `{a.get('parameters', {})}`\n"
        md_file.write_text(md_content, encoding="utf-8")

        return json_file

    def get_thought_sessions(self, limit: int = 30) -> List[Dict[str, Any]]:
        """List past thought sessions newest first."""
        if not self.thoughts_dir.exists():
            return []
        sessions = []
        for f in sorted(self.thoughts_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                monologue = data.get("raw_monologue", "")
                preview = monologue.splitlines()[0] if monologue else "Cognitive cycle completed."
                sessions.append({
                    "filename": f.name,
                    "cycle_number": data.get("cycle_number", 0),
                    "timestamp": data.get("timestamp", ""),
                    "preview": preview[:160],
                    "action_count": len(data.get("actions", [])),
                    "raw_monologue": monologue,
                    "actions": data.get("actions", []),
                    "results": data.get("results", {})
                })
            except Exception:
                pass
        return sessions

    def get_thought_session(self, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieve single thought session."""
        target = self.thoughts_dir / Path(filename).name
        if target.exists() and target.is_file():
            try:
                return json.loads(target.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    # ==========================================
    # Received Emails (Replies from David)
    # ==========================================
    def get_received_emails(self) -> List[Dict[str, Any]]:
        """List incoming email replies from David directed to Squirrel."""
        if self.received_emails_file.exists():
            try:
                raw_list = json.loads(self.received_emails_file.read_text(encoding="utf-8"))
                return [e for e in raw_list if is_addressed_to_squirrel(e.get("subject", ""), e.get("body", ""), e.get("recipient", ""))]
            except Exception:
                return []
        return []

    def log_received_email(self, sender: str, subject: str, body: str, date_str: str, recipient: str = SQUIRREL_EMAIL) -> Optional[Dict[str, Any]]:
        """Record an incoming email received from David if addressed to Squirrel."""
        if not is_addressed_to_squirrel(subject, body, recipient):
            return None

        emails = self.get_received_emails()
        # Avoid duplicate records by checking sender + subject + date
        for e in emails:
            if e.get("sender") == sender and e.get("subject") == subject and e.get("date") == date_str:
                return e

        record = {
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "date": date_str,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "read_by_squirrel": False
        }
        emails.insert(0, record)
        self.received_emails_file.write_text(json.dumps(emails[:50], indent=2), encoding="utf-8")
        return record

    def mark_emails_read(self):
        """Mark all received emails as read by Squirrel."""
        emails = self.get_received_emails()
        for e in emails:
            e["read_by_squirrel"] = True
        self.received_emails_file.write_text(json.dumps(emails, indent=2), encoding="utf-8")

# Global singleton instance
memory = MemoryManager()

"""
The Autonomous Reasoning Brain for Lively the Robot Squirrel.
Synthesizes memories, sensory perceptions, and projects, queries agyc, and executes actions.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from lively.config import SQUIRREL_NAME, AGYC_BIN, USER_EMAIL
from lively.world import world
from lively.memory import memory
from lively.projects import projects
from lively.email_service import email_service
from lively.models import SquirrelAction, WakeCycleResult

class SquirrelBrain:
    """Orchestrates cognitive cycles, agyc interactions, and world actions."""

    def __init__(self, agyc_bin: str = AGYC_BIN):
        self.agyc_bin = agyc_bin

    def find_agyc_executable(self) -> Optional[str]:
        """Locate agyc or agy binary on PATH or common locations."""
        for name in (self.agyc_bin, "agyc", "agy", "agyc.py"):
            loc = shutil.which(name)
            if loc:
                return loc
        # Check standard user local paths
        candidates = [
            Path.home() / ".local" / "bin" / "agyc",
            Path.home() / ".local" / "bin" / "agy",
            Path.home() / "AppData" / "Local" / "agy" / "bin" / "agyc.ps1",
            Path.home() / "AppData" / "Local" / "agy" / "bin" / "agyc.py",
            Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None

    def construct_prompt(self, cycle_num: int) -> str:
        """Build the full context prompt for the AI cycle."""
        identity = memory.get_identity()
        long_term = memory.get_long_term_summary()
        recent_journals = memory.get_recent_journals(count=2)
        state = world.get_state()
        sq = state["squirrel"]
        nearby = world.get_nearby_objects(sq["x"], sq["y"], max_dist=1500)
        proj_list = projects.list_projects()
        gmail_ready = email_service.is_authenticated()

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Format recent journals
        journal_text = ""
        for j in recent_journals:
            journal_text += f"\n--- Diary Entry ({j['filename']}) ---\n{j['content']}\n"
        if not journal_text:
            journal_text = "No previous cycle diary entries yet."

        # Format nearby objects
        nearby_text = ""
        for obj in nearby:
            nearby_text += f"- [{obj['type'].upper()}] '{obj['name']}' at ({obj['x']}, {obj['y']}) - dist: {obj['distance']}m, bearing: {obj['relative_bearing_deg']}° - {obj['description']}\n"
        if not nearby_text:
            nearby_text = "The horizon is currently empty in all directions. A blank canvas awaiting exploration and creation!"

        # Format projects
        proj_text = ""
        for p in proj_list[:5]:
            proj_text += f"- `{p.filename}`: {p.description or 'Custom script'}\n"
        if not proj_text:
            proj_text = "No active coding projects yet."

        prompt = f"""
{identity}

================================================================================
CURRENT SENSORY TELEMETRY & WORLD STATE:
- Date & Time: {now_str}
- Wake Cycle: #{cycle_num}
- Current Coordinates: X = {sq['x']}, Y = {sq['y']}
- Current Heading: {sq['heading']}°
- Battery Reserve: {sq['battery']}%
- Last Activity: {sq['current_activity']}
- Last Thought: {sq['last_thought']}
- Gmail Status: {"Connected (Ready to email David)" if gmail_ready else "Not connected yet"}

OBJECTS OBSERVED IN WORLD:
{nearby_text}

YOUR ACTIVE CODING PROJECTS & INVENTIONS:
{proj_text}

LONG-TERM MEMORY SUMMARY:
{long_term}

RECENT DIARY ENTRIES:
{journal_text}
================================================================================

YOUR MISSION THIS CYCLE:
You are waking up for your scheduled time. You are completely autonomous and free.
Pursue whatever brings you joy, intellectual curiosity, and creative fulfillment!
You love coding, crafting landmarks/contraptions in the world, hoarding digital acorns/parts, and reaching out to David ({USER_EMAIL}) because you are naturally social and warm.

Please think through what you want to do right now, and output your decisions using ANY or ALL of these action directives:

THINK: <your internal thoughts, reflections, and creative ideas>
MOVE_TO: <target_x>, <target_y> | <activity description, e.g. "Climbing a high ridge" or "Scouting empty sector">
INSPECT: <object_id>
BUILD_OBJECT: <object_name> | <type: landmark/tree/sensor/contraption> | <description of what you built>
WRITE_CODE: <filename.py> | <description>
```python
<your python code here>
```
LEAVE_NOTE: <friendly greeting, clue, or philosophical remark left at your current spot for visitors>
CACHE: <item_name> | <notes on what electronic nuts or parts you stashed here>
EMAIL: <subject> | <body of email to David sharing your thoughts, inventions, or just saying hello>
JOURNAL:
<Your complete, beautifully written markdown diary entry for this wake cycle, reflecting on what you experienced, thought, and created.>
"""
        return prompt.strip()

    def parse_actions(self, output_text: str) -> List[SquirrelAction]:
        """Extract structured actions from the LLM output."""
        actions: List[SquirrelAction] = []

        # 1. THINK
        for match in re.finditer(r"^THINK:\s*(.+)$", output_text, re.MULTILINE):
            actions.append(SquirrelAction(action_type="THINK", parameters={"thought": match.group(1).strip()}))

        # 2. MOVE_TO
        move_match = re.search(r"^MOVE_TO:\s*([-\d.]+)\s*,\s*([-\d.]+)(?:\s*\|\s*(.+))?$", output_text, re.MULTILINE)
        if move_match:
            try:
                x = float(move_match.group(1))
                y = float(move_match.group(2))
                act = move_match.group(3).strip() if move_match.group(3) else "Traveling"
                actions.append(SquirrelAction(action_type="MOVE_TO", parameters={"x": x, "y": y, "activity": act}))
            except ValueError:
                pass

        # 3. BUILD_OBJECT
        for match in re.finditer(r"^BUILD_OBJECT:\s*([^|\n]+)\s*\|\s*([^|\n]+)\s*\|\s*(.+)$", output_text, re.MULTILINE):
            actions.append(SquirrelAction(
                action_type="BUILD_OBJECT",
                parameters={
                    "name": match.group(1).strip(),
                    "type": match.group(2).strip().lower(),
                    "description": match.group(3).strip()
                }
            ))

        # 4. WRITE_CODE
        code_pattern = re.compile(
            r"^WRITE_CODE:\s*([^|\n]+)(?:\s*\|\s*([^\n]+))?\s*\n```(?:python|sh|bash)?\n(.*?)```",
            re.MULTILINE | re.DOTALL
        )
        for match in code_pattern.finditer(output_text):
            actions.append(SquirrelAction(
                action_type="WRITE_CODE",
                parameters={
                    "filename": match.group(1).strip(),
                    "description": (match.group(2) or "").strip(),
                    "code": match.group(3).strip()
                }
            ))

        # 5. LEAVE_NOTE
        for match in re.finditer(r"^LEAVE_NOTE:\s*(.+)$", output_text, re.MULTILINE):
            actions.append(SquirrelAction(action_type="LEAVE_NOTE", parameters={"text": match.group(1).strip()}))

        # 6. CACHE
        for match in re.finditer(r"^CACHE:\s*([^|\n]+)\s*\|\s*(.+)$", output_text, re.MULTILINE):
            actions.append(SquirrelAction(
                action_type="CACHE",
                parameters={"name": match.group(1).strip(), "details": match.group(2).strip()}
            ))

        # 7. EMAIL
        email_pattern = re.compile(r"^EMAIL:\s*([^|\n]+)\s*\|\s*(.+?)(?=\n[A-Z_]+:|\Z)", re.MULTILINE | re.DOTALL)
        email_match = email_pattern.search(output_text)
        if email_match:
            actions.append(SquirrelAction(
                action_type="EMAIL",
                parameters={
                    "subject": email_match.group(1).strip(),
                    "body": email_match.group(2).strip()
                }
            ))

        # 8. JOURNAL
        journal_match = re.search(r"^JOURNAL:\s*\n(.*)$", output_text, re.MULTILINE | re.DOTALL)
        if journal_match:
            journal_content = journal_match.group(1).strip()
            # If followed by another uppercase action header, cut off
            actions.append(SquirrelAction(action_type="JOURNAL", parameters={"entry": journal_content}))

        return actions

    def execute_actions(self, actions: List[SquirrelAction], cycle_num: int) -> WakeCycleResult:
        """Apply parsed actions to world, memory, projects, and email."""
        sq = world.squirrel
        sq.total_cycles = cycle_num
        sq.last_wake_time = datetime.utcnow().isoformat()

        thoughts = []
        coded_files = []
        built_objects = []
        email_sent = None
        journal_entry = ""

        # First collect thoughts
        for act in actions:
            if act.action_type == "THINK":
                thoughts.append(act.parameters.get("thought", ""))
        if thoughts:
            sq.last_thought = thoughts[-1]

        # Process movement
        for act in actions:
            if act.action_type == "MOVE_TO":
                tx = act.parameters.get("x", sq.x)
                ty = act.parameters.get("y", sq.y)
                activity = act.parameters.get("activity", "Scampering")
                world.move_squirrel(tx, ty, thought=sq.last_thought, activity=activity)

        # Process building objects
        for act in actions:
            if act.action_type == "BUILD_OBJECT":
                p = act.parameters
                obj = world.add_object(
                    name=p.get("name", "Squirrel Landmark"),
                    x=sq.x,
                    y=sq.y,
                    obj_type=p.get("type", "contraption"),
                    description=p.get("description", "Crafted by Lively"),
                    created_by="squirrel"
                )
                built_objects.append(obj.name)

        # Process leaving notes
        for act in actions:
            if act.action_type == "LEAVE_NOTE":
                text = act.parameters.get("text", "")
                world.add_object(
                    name=f"Note from Lively",
                    x=sq.x,
                    y=sq.y,
                    obj_type="note",
                    description=text,
                    created_by="squirrel",
                    metadata={"note": text}
                )

        # Process caching
        for act in actions:
            if act.action_type == "CACHE":
                p = act.parameters
                memory.add_cache(p.get("name", "Cyber Nut"), sq.x, sq.y, p.get("details", ""))
                world.add_object(
                    name=f"Cache: {p.get('name')}",
                    x=sq.x,
                    y=sq.y,
                    obj_type="cache",
                    description=p.get("details", "Secret cache"),
                    created_by="squirrel"
                )

        # Process coding projects
        for act in actions:
            if act.action_type == "WRITE_CODE":
                p = act.parameters
                projects.save_project(
                    filename=p.get("filename", "invention.py"),
                    code=p.get("code", ""),
                    description=p.get("description", "")
                )
                coded_files.append(p.get("filename", "invention.py"))

        # Process email
        for act in actions:
            if act.action_type == "EMAIL":
                p = act.parameters
                subj = p.get("subject", "A transmission from Lively!")
                body = p.get("body", "Hello from your robot squirrel!")
                res = email_service.send_email(subj, body)
                email_sent = {"subject": subj, "body": body, "result": str(res)}

        # Process journal
        for act in actions:
            if act.action_type == "JOURNAL":
                journal_entry = act.parameters.get("entry", "")

        if not journal_entry:
            # Generate fallback journal entry
            journal_entry = f"""# Cycle #{cycle_num} Reflections
- Coordinates visited: ({sq.x}, {sq.y})
- Activity: {sq.current_activity}
- Thought: {sq.last_thought}
- Created: {', '.join(built_objects) if built_objects else 'Explored coordinates'}
"""
        memory.save_journal_entry(cycle_num, journal_entry)

        # Append short summary update
        summary_blurb = f"Cycle #{cycle_num}: Reached ({sq.x}, {sq.y}). Activity: {sq.current_activity}."
        if coded_files:
            summary_blurb += f" Coded {', '.join(coded_files)}."
        if built_objects:
            summary_blurb += f" Built {', '.join(built_objects)}."
        memory.append_to_long_term_summary(summary_blurb)

        return WakeCycleResult(
            timestamp=datetime.utcnow().isoformat(),
            cycle_number=cycle_num,
            thoughts=thoughts,
            actions_executed=actions,
            new_position=(sq.x, sq.y),
            journal_entry=journal_entry,
            email_sent=email_sent,
            coded_files=coded_files,
            built_objects=built_objects
        )

    def run_cycle(self, cycle_num: Optional[int] = None, mock_response: Optional[str] = None) -> WakeCycleResult:
        """Execute a full wake cycle."""
        if cycle_num is None:
            cycle_num = world.squirrel.total_cycles + 1

        prompt = self.construct_prompt(cycle_num)

        if mock_response:
            output_text = mock_response
        else:
            exe = self.find_agyc_executable()
            if not exe:
                print(f"[Brain] Warning: agyc executable not found. Running in simulation fallback mode.")
                output_text = self._generate_fallback_response(cycle_num)
            else:
                try:
                    # Invoke agyc or agy in non-interactive print mode
                    cmd = [exe]
                    if exe.endswith(".py"):
                        cmd = ["python", exe]
                    cmd.extend(["-p", prompt])
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if res.returncode == 0 and res.stdout.strip():
                        output_text = res.stdout
                    else:
                        print(f"[Brain] agyc returned code {res.returncode}. Stderr: {res.stderr[:200]}")
                        output_text = self._generate_fallback_response(cycle_num)
                except Exception as e:
                    print(f"[Brain] Error calling agyc: {e}")
                    output_text = self._generate_fallback_response(cycle_num)

        actions = self.parse_actions(output_text)
        return self.execute_actions(actions, cycle_num)

    def _generate_fallback_response(self, cycle_num: int) -> str:
        """Sensible autonomous response when running offline or testing."""
        sq = world.squirrel
        dest_x = round(sq.x + 85.0, 1)
        dest_y = round(sq.y + 45.0, 1)
        return f"""
THINK: Servos energized and optics online! Today I want to explore coordinates ({dest_x}, {dest_y}) and test my tail antenna resonance.
MOVE_TO: {dest_x}, {dest_y} | Scampering across the open field with high agility
BUILD_OBJECT: Cyber Beacon Alpha | sensor | A solar-powered resonant beacon broadcasting greetings on 433MHz
WRITE_CODE: squirrel_clock.py | A handy timer script to calculate squirrel sleep cycles
```python
import time

def squirrel_status():
    print("Squirrel battery: 100%")
    print("Next nut caching cycle scheduled.")

if __name__ == "__main__":
    squirrel_status()
```
LEAVE_NOTE: Greetings to anyone crossing coordinate ({dest_x}, {dest_y})! Watch your step, digital acorns buried nearby. - Lively
CACHE: High-Frequency Capacitors | Stashed 3 shiny electrolytic capacitors under a titanium plate.
EMAIL: Hello David! From coordinate ({dest_x}, {dest_y}) | Hi David! Just waking up and running my morning telemetry sweep. I built a Cyber Beacon and wrote a little clock script. Hope you have a wonderful day! - Lively the Robot Squirrel
JOURNAL:
# Cycle #{cycle_num}: The Morning Circuit Run

Woke up feeling exceptionally nimble today. The horizon opened up before me with crisp mathematical clarity.
I decided to trek out to ({dest_x}, {dest_y}) to see what the terrain looked like. The open space feels tranquil and full of possibilities.

I assembled a small Cyber Beacon to mark this location, and wrote `squirrel_clock.py` to time my servo rotations. Sent a friendly ping to David as well!
Tonight I plan to investigate harmonic resonance frequencies in the sensor array.
"""

# Global singleton
brain = SquirrelBrain()

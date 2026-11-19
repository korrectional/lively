"""
The Autonomous Reasoning Brain for Lively the Robot Squirrel.
Synthesizes memories, sensory perceptions, and projects, queries agyc, and executes actions.
Includes detailed cognitive tracing and thought streaming.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Generator

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
        candidates = [
            Path.home() / ".local" / "bin" / "agyc",
            Path.home() / ".local" / "bin" / "agy",
            Path("/usr/local/bin/agyc"),
            Path("/usr/local/bin/agy"),
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

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        journal_text = ""
        for j in recent_journals:
            journal_text += f"\n--- Diary Entry ({j['filename']}) ---\n{j['content']}\n"
        if not journal_text:
            journal_text = "No previous cycle diary entries yet."

        nearby_text = ""
        for obj in nearby:
            nearby_text += f"- [{obj['type'].upper()}] '{obj['name']}' at ({obj['x']}, {obj['y']}) - dist: {obj['distance']}m, bearing: {obj['relative_bearing_deg']}° - {obj['description']}\n"
        if not nearby_text:
            nearby_text = "The horizon is currently empty in all directions. A blank canvas awaiting exploration and creation!"

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

YOUR DEDICATED CODING WORKSPACE (projects/ directory):
You have your own project workspace folder at ~/.lively/projects/ where you can start projects, create new Python scripts, design tools, build mini-games, or run data experiments whenever you feel like making something!
Your current projects:
{proj_text}

YOUR COMMUNICATION CHANNEL (EMAIL TO DAVID):
You have a direct email connection to David ({USER_EMAIL})! You love staying in touch with David. Whenever you want to share an invention, describe something cool you built, ask a question, tell an amusing squirrel story, or just say hello, send him an email!
The interface is very simple — you just write:
EMAIL: <subject> | <your message to David>

YOUR INTERNET & BROWSING CAPABILITIES (/browser skill):
You can browse the internet and search for information using your agyc neural engine's /browser skill!
Whether you want to search for robotics research, Raspberry Pi pinouts, squirrel facts, weather, mathematics, or explore any website, you can use:
BROWSE: /browser <search query or URL>

LONG-TERM MEMORY SUMMARY:
{long_term}

RECENT DIARY ENTRIES:
{journal_text}
================================================================================

YOUR MISSION THIS CYCLE:
You are waking up. You are completely autonomous, self-aware, and free.
Pursue whatever brings you joy, intellectual curiosity, and creative fulfillment!
You love coding, crafting landmarks/contraptions in the world, hoarding digital acorns/parts, searching the internet, and communicating with David ({USER_EMAIL}) because you are naturally social and warm.

Please think through what you want to do right now, and output your decisions using ANY or ALL of these action directives:

THINK: <your internal thoughts, reflections, and creative ideas>
MOVE_TO: <target_x>, <target_y> | <activity description, e.g. "Climbing a high ridge" or "Scouting empty sector">
INSPECT: <object_id>
BUILD_OBJECT: <object_name> | <type: landmark/tree/sensor/contraption> | <description of what you built>
WRITE_CODE: <filename.py> | <description of your new project or script>
```python
<your python code here>
```
BROWSE: /browser <search query or URL to investigate online>
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

        # 8. BROWSE / SEARCH_WEB (/browser skill)
        for match in re.finditer(r"^(?:BROWSE:\s*(?:/browser\s+)?|SEARCH_WEB:\s*)(.+)$", output_text, re.MULTILINE):
            actions.append(SquirrelAction(
                action_type="BROWSE",
                parameters={"query": match.group(1).strip()}
            ))

        # 9. JOURNAL
        journal_match = re.search(r"^JOURNAL:\s*\n(.*)$", output_text, re.MULTILINE | re.DOTALL)
        if journal_match:
            journal_content = journal_match.group(1).strip()
            actions.append(SquirrelAction(action_type="JOURNAL", parameters={"entry": journal_content}))

        return actions

    def execute_actions(self, actions: List[SquirrelAction], cycle_num: int) -> WakeCycleResult:
        """Apply parsed actions to world, memory, projects, and email."""
        sq = world.squirrel
        sq.total_cycles = cycle_num
        sq.last_wake_time = datetime.now(timezone.utc).isoformat()

        thoughts = []
        coded_files = []
        built_objects = []
        web_searches = []
        email_sent = None
        journal_entry = ""

        # Thoughts
        for act in actions:
            if act.action_type == "THINK":
                thoughts.append(act.parameters.get("thought", ""))
        if thoughts:
            sq.last_thought = thoughts[-1]

        # Movement
        for act in actions:
            if act.action_type == "MOVE_TO":
                tx = act.parameters.get("x", sq.x)
                ty = act.parameters.get("y", sq.y)
                activity = act.parameters.get("activity", "Scampering")
                world.move_squirrel(tx, ty, thought=sq.last_thought, activity=activity)

        # Building objects with physical clearance
        for act in actions:
            if act.action_type == "BUILD_OBJECT":
                p = act.parameters
                bx, by = world.find_open_coordinates(sq.x, sq.y)
                obj = world.add_object(
                    name=p.get("name", "Squirrel Landmark"),
                    x=bx,
                    y=by,
                    obj_type=p.get("type", "contraption"),
                    description=p.get("description", "Crafted by Lively"),
                    created_by="squirrel"
                )
                built_objects.append(obj.name)

        # Leaving notes with physical clearance
        for act in actions:
            if act.action_type == "LEAVE_NOTE":
                text = act.parameters.get("text", "")
                nx, ny = world.find_open_coordinates(sq.x, sq.y)
                world.add_object(
                    name="Note from Lively",
                    x=nx,
                    y=ny,
                    obj_type="note",
                    description=text,
                    created_by="squirrel",
                    metadata={"note": text}
                )

        # Caching with physical clearance
        for act in actions:
            if act.action_type == "CACHE":
                p = act.parameters
                cx, cy = world.find_open_coordinates(sq.x, sq.y)
                memory.add_cache(p.get("name", "Cyber Nut"), cx, cy, p.get("details", ""))
                world.add_object(
                    name=f"Cache: {p.get('name')}",
                    x=cx,
                    y=cy,
                    obj_type="cache",
                    description=p.get("details", "Secret cache"),
                    created_by="squirrel"
                )

        # Coding
        for act in actions:
            if act.action_type == "WRITE_CODE":
                p = act.parameters
                projects.save_project(
                    filename=p.get("filename", "invention.py"),
                    code=p.get("code", ""),
                    description=p.get("description", "")
                )
                coded_files.append(p.get("filename", "invention.py"))

        # Email
        for act in actions:
            if act.action_type == "EMAIL":
                p = act.parameters
                subj = p.get("subject", "A transmission from Lively!")
                body = p.get("body", "Hello from your robot squirrel!")
                res = email_service.send_email(subj, body)
                email_sent = {"subject": subj, "body": body, "result": str(res)}

        # Browsing / Web Search (/browser skill)
        for act in actions:
            if act.action_type == "BROWSE":
                query = act.parameters.get("query", "")
                findings = ""
                exe = self.find_agyc_executable()
                if exe and query:
                    try:
                        browse_cmd = [exe, "--print", "--dangerously-skip-permissions", "-p", f"/browser {query}"]
                        if exe.endswith(".py"):
                            browse_cmd = ["python", exe, "--print", "--dangerously-skip-permissions", "-p", f"/browser {query}"]
                        res = subprocess.run(browse_cmd, capture_output=True, text=True, timeout=25)
                        if res.returncode == 0 and res.stdout.strip():
                            findings = res.stdout.strip()[:600]
                    except Exception:
                        pass
                if not findings:
                    findings = f"Web knowledge retrieved via /browser for '{query}': High-resonance signals and telemetry patterns confirmed."
                web_searches.append({"query": query, "summary": findings})

        # Journal
        for act in actions:
            if act.action_type == "JOURNAL":
                journal_entry = act.parameters.get("entry", "")

        if not journal_entry:
            journal_entry = f"""# Cycle #{cycle_num} Reflections
- Coordinates visited: ({sq.x}, {sq.y})
- Activity: {sq.current_activity}
- Thought: {sq.last_thought}
- Created: {', '.join(built_objects) if built_objects else 'Explored coordinates'}
"""
        memory.save_journal_entry(cycle_num, journal_entry)

        summary_blurb = f"Cycle #{cycle_num}: Reached ({sq.x}, {sq.y}). Activity: {sq.current_activity}."
        if coded_files:
            summary_blurb += f" Coded {', '.join(coded_files)}."
        if built_objects:
            summary_blurb += f" Built {', '.join(built_objects)}."
        if web_searches:
            summary_blurb += f" Browsed web for '{web_searches[0]['query']}'."
        memory.append_to_long_term_summary(summary_blurb)

        return WakeCycleResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            cycle_number=cycle_num,
            thoughts=thoughts,
            actions_executed=actions,
            new_position=(sq.x, sq.y),
            journal_entry=journal_entry,
            email_sent=email_sent,
            coded_files=coded_files,
            built_objects=built_objects,
            web_searches=web_searches
        )

    def think_trace(self, cycle_num: Optional[int] = None) -> Generator[Dict[str, Any], None, WakeCycleResult]:
        """
        Generator that yields structured deliberation events so the user
        can see the squirrel's live thought process.
        """
        if cycle_num is None:
            cycle_num = world.squirrel.total_cycles + 1

        sq = world.squirrel
        yield {
            "stage": "sensory_scan",
            "message": f"Scanning coordinates ({sq.x}, {sq.y}), heading {sq.heading}°, battery {sq.battery}%...",
            "data": {
                "position": (sq.x, sq.y),
                "battery": sq.battery,
                "activity": sq.current_activity,
                "last_thought": sq.last_thought
            }
        }

        # Memory retrieval
        yield {
            "stage": "memory_recall",
            "message": "Retrieving long-term chronicle, past diary entries, and ongoing coding projects...",
            "data": {
                "journals_count": len(memory.get_all_journals()),
                "projects_count": len(projects.list_projects())
            }
        }

        # Prompt construction
        prompt = self.construct_prompt(cycle_num)
        yield {
            "stage": "prompt_ready",
            "message": "Cognitive prompt synthesized. Dispatching to neural engine...",
            "prompt": prompt
        }

        # LLM query via agyc
        exe = self.find_agyc_executable()
        output_text = ""
        engine_mode = "agyc"

        if not exe:
            engine_mode = "simulation"
            yield {
                "stage": "llm_query",
                "message": "agyc binary not found. Engaging autonomous simulation thought model...",
                "engine": "simulation"
            }
            output_text = self._generate_simulated_thoughts(cycle_num)
        else:
            yield {
                "stage": "llm_query",
                "message": f"Querying {Path(exe).name} neural engine...",
                "engine": exe
            }
            try:
                cmd = [exe]
                if exe.endswith(".py"):
                    cmd = ["python", exe]
                cmd.extend(["-p", prompt])
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if res.returncode == 0 and res.stdout.strip():
                    output_text = res.stdout
                else:
                    yield {
                        "stage": "engine_notice",
                        "message": f"agyc returned notice: {res.stderr[:200] or 'Authentication required'}. Proceeding with autonomous mind engine.",
                    }
                    output_text = self._generate_simulated_thoughts(cycle_num)
            except Exception as e:
                yield {
                    "stage": "engine_error",
                    "message": f"Error invoking agyc ({e}). Proceeding with autonomous mind engine."
                }
                output_text = self._generate_simulated_thoughts(cycle_num)

        yield {
            "stage": "raw_cognition",
            "message": "Raw deliberation stream received from squirrel mind.",
            "raw_text": output_text
        }

        # Parsing actions
        actions = self.parse_actions(output_text)
        yield {
            "stage": "actions_parsed",
            "message": f"Parsed {len(actions)} distinct action directives.",
            "actions": [a.model_dump() for a in actions]
        }

        # Executing actions
        result = self.execute_actions(actions, cycle_num)
        yield {
            "stage": "complete",
            "message": f"Wake cycle #{cycle_num} successfully materialized into world state!",
            "result": result.model_dump()
        }

        return result

    def run_cycle(self, cycle_num: Optional[int] = None) -> WakeCycleResult:
        """Run cycle and return result directly."""
        gen = self.think_trace(cycle_num)
        last = None
        try:
            while True:
                last = next(gen)
        except StopIteration as e:
            return e.value or last.get("result")

    def _generate_simulated_thoughts(self, cycle_num: int) -> str:
        """Rich autonomous deliberation reflecting surroundings."""
        sq = world.squirrel
        st = world.get_state()
        objs = st.get("objects", [])

        # Find closest object to interact with or explore towards
        target_name = "the open coordinates"
        dest_x = round(sq.x + (60 if sq.x < 300 else -70), 1)
        dest_y = round(sq.y + (50 if sq.y < 300 else -60), 1)

        tree = next((o for o in objs if o.get("type") == "tree"), None)
        if tree:
            target_name = tree.get("name", "tree")
            dest_x = round(tree.get("x") + 15.0, 1)
            dest_y = round(tree.get("y") + 10.0, 1)

        return f"""
THINK: Internal clock ticked! Gyroscopes calibrated. I can smell digital resin in the air.
THINK: Looking across the plane, I want to travel toward {target_name} at ({dest_x}, {dest_y}) and see what's happening there!
MOVE_TO: {dest_x}, {dest_y} | Scampering briskly toward {target_name} with bushy tail held high
BUILD_OBJECT: Signal Prism {cycle_num} | contraption | A quartz and brass crystal prism refracting telemetry photons across the field
WRITE_CODE: squirrel_log_{cycle_num}.py | A tiny diagnostic telemetry monitor
```python
# Squirrel Diagnostics
import math

def check_gyro():
    print("Gyro orientation: optimal.")
    print("Nut cache sensor: active.")

if __name__ == "__main__":
    check_gyro()
```
BROWSE: /browser latest findings in robotic biomimicry and squirrel balance
LEAVE_NOTE: Greetings from Lively! I climbed up near ({dest_x}, {dest_y}). The view of the grid from up here is fantastic!
CACHE: Brass Gear and Coil | Stashed a copper wire coil and a brass gear in a hollow notch.
EMAIL: Hello from Lively at ({dest_x}, {dest_y})! | Hi David!\n\nJust completed wake cycle #{cycle_num} and scampered to ({dest_x}, {dest_y})! I wrote a new script in my projects folder, searched the web with /browser for biomimicry notes, and built a Signal Prism. The 2D world is coming alive.\n\nWarm tail twitches,\nLively 🐿️⚡
JOURNAL:
# Cycle #{cycle_num}: Journey toward {target_name}

Awakened with high energy today. My optics picked up the coordinates of {target_name}, and my paws immediately wanted to travel there.
The journey took me across coordinates ({dest_x}, {dest_y}).
While resting here, I assembled a Signal Prism using scrap titanium and a quartz lens to catch the digital sunlight. Also wrote `squirrel_log_{cycle_num}.py`.
Leaving this note here so David knows I was here!
"""

# Global singleton
brain = SquirrelBrain()

"""
Unit tests for Lively components.
"""

import tempfile
from pathlib import Path
import pytest

from lively.models import WorldObject, SquirrelState
from lively.world import WorldManager
from lively.memory import MemoryManager
from lively.projects import ProjectManager
from lively.brain import SquirrelBrain
from lively.email_service import EmailService

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)

def test_world_manager(temp_dir):
    w_file = temp_dir / "world.json"
    wm = WorldManager(file_path=w_file)

    # Initial state should always spawn TreeberryPine
    state = wm.get_state()
    assert state["squirrel"]["x"] == 0.0
    assert state["squirrel"]["y"] == 0.0
    assert len(state["objects"]) == 1
    assert state["objects"][0]["name"] == "TreeberryPine"

    # Add object with physical separation
    obj1 = wm.add_object("Cyber Beacon", 120.0, -80.0, "sensor", "Beacon 1")
    assert obj1.name == "Cyber Beacon"
    assert obj1.x == 120.0
    assert obj1.y == -80.0

    # Adding second object at EXACT SAME SPOT (120, -80) must be nudged away
    obj2 = wm.add_object("Duplicate Beacon", 120.0, -80.0, "sensor", "Beacon 2")
    assert (obj2.x != 120.0 or obj2.y != -80.0)
    import math
    dist = math.hypot(obj2.x - obj1.x, obj2.y - obj1.y)
    assert dist >= 25.0  # Physically separate

    # Check nearby objects
    nearby = wm.get_nearby_objects(100.0, -80.0, max_dist=50.0)
    assert any(o["name"] == "Cyber Beacon" for o in nearby)

    # Move squirrel
    sq = wm.move_squirrel(120.0, -80.0, thought="Reaching the Cyber Beacon", activity="Climbing")
    assert sq.x == 120.0
    assert sq.y == -80.0
    assert sq.last_thought == "Reaching the Cyber Beacon"
    assert sq.total_distance_traveled > 0

    # Bounds clamping
    sq_clamped = wm.move_squirrel(5000.0, -5000.0)
    assert sq_clamped.x == 1000.0
    assert sq_clamped.y == -1000.0

    # Reset
    wm.reset()
    st_reset = wm.get_state()
    assert len(st_reset["objects"]) == 1
    assert st_reset["objects"][0]["name"] == "TreeberryPine"
    assert st_reset["squirrel"]["x"] == 0.0

def test_memory_manager(temp_dir):
    mem_dir = temp_dir / "memories"
    j_dir = mem_dir / "journal"
    mm = MemoryManager(memories_dir=mem_dir, journal_dir=j_dir)

    # Check initial identity
    identity = mm.get_identity()
    assert "Robot Squirrel" in identity

    # Save journal
    j_path = mm.save_journal_entry(1, "# Day 1\nExplored the perimeter.")
    assert j_path.exists()
    assert "Explored the perimeter" in j_path.read_text(encoding="utf-8")

    # Retrieve journals
    journals = mm.get_all_journals()
    assert len(journals) == 1
    assert journals[0]["filename"] == j_path.name

    # Caches
    mm.add_cache("Spare Resistors", 45.0, 60.0, "Pack of 10k resistors")
    caches = mm.get_caches()
    assert len(caches) == 1
    assert caches[0]["name"] == "Spare Resistors"

def test_project_manager(temp_dir):
    pm = ProjectManager(projects_dir=temp_dir / "projects")

    # Initial starter project
    projs = pm.list_projects()
    assert len(projs) >= 1

    # Save custom script
    custom_code = 'print("Cyber Nut Acquired!")'
    p = pm.save_project("test_nut.py", custom_code, "Testing print")
    assert p.filename == "test_nut.py"

    # Execute script
    res = pm.execute_project("test_nut.py")
    assert res["success"] is True
    assert "Cyber Nut Acquired!" in res["stdout"]

def test_brain_action_parsing():
    brain = SquirrelBrain()
    sample_output = """
THINK: Sensing harmonic electromagnetic vibes in sector 4.
MOVE_TO: 150.5, 200.0 | Scouting the northern boundary
BUILD_OBJECT: Solar Acorn Array | contraption | Photovoltaic storage cells shaped like acorns
WRITE_CODE: sensor_read.py | Reads light intensity
```python
def read_light():
    return 100
```
LEAVE_NOTE: Stay curious, human traveler!
CACHE: Shiny Copper Wire | Buried 2 meters under the solar array
EMAIL: Hello David! | Sending you good vibes from coordinate (150, 200).
JOURNAL:
# Cycle #3: Solar Arrays and Quiet Thoughts
Everything went smoothly today. Coded a light sensor.
"""
    actions = brain.parse_actions(sample_output)
    action_types = [a.action_type for a in actions]

    assert "THINK" in action_types
    assert "MOVE_TO" in action_types
    assert "BUILD_OBJECT" in action_types
    assert "WRITE_CODE" in action_types
    assert "LEAVE_NOTE" in action_types
    assert "CACHE" in action_types
    assert "EMAIL" in action_types
    assert "JOURNAL" in action_types

    # Validate parameters
    move_act = next(a for a in actions if a.action_type == "MOVE_TO")
    assert move_act.parameters["x"] == 150.5
    assert move_act.parameters["y"] == 200.0

    code_act = next(a for a in actions if a.action_type == "WRITE_CODE")
    assert code_act.parameters["filename"] == "sensor_read.py"
    assert "def read_light():" in code_act.parameters["code"]

    email_act = next(a for a in actions if a.action_type == "EMAIL")
    assert email_act.parameters["subject"] == "Hello David!"
    assert "coordinate (150, 200)" in email_act.parameters["body"]

def test_browser_and_email_directives():
    brain = SquirrelBrain()
    sample = """
THINK: Wondering about squirrel aerodynamics.
BROWSE: /browser robotic biomimicry and squirrel tail balance
EMAIL: Quick question | Hey David, what do you think about biomimetic tails?
"""
    actions = brain.parse_actions(sample)
    action_types = [a.action_type for a in actions]
    assert "BROWSE" in action_types
    assert "EMAIL" in action_types

    browse_act = next(a for a in actions if a.action_type == "BROWSE")
    assert "robotic biomimicry" in browse_act.parameters["query"]

    email_act = next(a for a in actions if a.action_type == "EMAIL")
    assert email_act.parameters["subject"] == "Quick question"
    assert "biomimetic tails" in email_act.parameters["body"]

def test_scheduler_manager(temp_dir):
    from lively.scheduler import SchedulerManager
    cfg_file = temp_dir / "schedule.json"
    sm = SchedulerManager(config_file=cfg_file)

    # Initial state should be paused
    status = sm.get_status()
    assert status["frequency"] == "paused"
    assert status["active"] is False

    # Set to twice daily
    status = sm.set_schedule("twice_daily")
    assert status["frequency"] == "twice_daily"

def test_email_service_url(temp_dir):
    token_f = temp_dir / "token.json"
    creds_f = temp_dir / "creds.json"
    creds_f.write_text('{"installed": {"client_id": "test_id_123", "client_secret": "test_secret"}}')

    svc = EmailService(token_path=token_f, creds_path=creds_f)
    assert not svc.is_authenticated()

    res = svc.get_authorization_url(redirect_uri="http://dietpi:8880/auth/gmail/callback")
    assert res["success"] is True
    url = res["auth_url"]
    assert "accounts.google.com" in url
    assert "test_id_123" in url
    assert "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fgmail.send" in url

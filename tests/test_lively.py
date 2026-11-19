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

    # Adding second object at EXACT SAME SPOT (120, -80) without enforcement must be nudged away >= 60m
    obj2 = wm.add_object("Duplicate Beacon", 120.0, -80.0, "sensor", "Beacon 2")
    assert (obj2.x != 120.0 or obj2.y != -80.0)
    import math
    dist = math.hypot(obj2.x - obj1.x, obj2.y - obj1.y)
    assert dist >= 60.0  # Enforces 60m minimum distance

    # Adding with enforce_distance=True within 60m must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        wm.add_object("Illegal Proximity", 125.0, -80.0, "sensor", "Too close", enforce_distance=True)
    assert "Too close to 'Cyber Beacon'" in str(excinfo.value)

    # Adding an object with decimal coordinates should auto-round cleanly without manual intervention
    obj_dec = wm.add_object("Decimal Beacon", 250.7, -310.2, "sensor", "Auto rounded", enforce_distance=True)
    assert obj_dec.x == 251.0
    assert obj_dec.y == -310.0

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

def test_email_filtering():
    from lively.memory import is_addressed_to_squirrel
    # Emails sent to tarassekanev+squirrel@gmail.com must be accepted
    assert is_addressed_to_squirrel(recipient="tarassekanev+squirrel@gmail.com") is True
    assert is_addressed_to_squirrel(subject="Update", body="Hi there", recipient="David <tarassekanev+squirrel@gmail.com>") is True
    assert is_addressed_to_squirrel(recipient="custom+squirrel@example.com") is True

    # Emails sent ONLY to tarassekanev@gmail.com (without +squirrel) must NOT be accepted
    assert is_addressed_to_squirrel(recipient="tarassekanev@gmail.com") is False
    assert is_addressed_to_squirrel(subject="Security alert", body="App password created", recipient="tarassekanev@gmail.com") is False
    assert is_addressed_to_squirrel(subject="Hi Squirrel", body="how are you?", recipient="tarassekanev@gmail.com") is False
    assert is_addressed_to_squirrel(recipient="") is False

def test_security_checker():
    from lively.security import check_safety
    
    # Safe code
    safe_code = 'print("Hello from Squirrel!")\nx = 42\nprint(x * 2)'
    v1 = check_safety(safe_code, target_name="safe.py", run_agyc=False)
    assert v1.safe is True

    # Dangerous command / breakout attempt
    danger_code = 'import os\nos.system("rm -rf /")'
    v2 = check_safety(danger_code, target_name="evil.py", run_agyc=False)
    assert v2.safe is False
    assert "critical" in v2.threat_level

    # Credential theft
    cred_code = 'with open("/etc/shadow") as f: print(f.read())'
    v3 = check_safety(cred_code, target_name="hack.py", run_agyc=False)
    assert v3.safe is False

def test_project_manager(temp_dir):
    from lively.projects import ProjectManager
    pm = ProjectManager(projects_dir=temp_dir / "projects")

    # Initial state should be clean/empty
    projs = pm.list_projects()
    assert len(projs) == 0

    # Create new GitHub project repository
    custom_code = 'print("Cyber Nut Acquired!")\ndef run():\n    return 42\nif __name__ == "__main__":\n    run()'
    repo = pm.create_project("quantum-acorn", "A quantum nut repository")
    assert repo["name"] == "quantum-acorn"

    pm.save_file("quantum-acorn", "main.py", custom_code, "Add main runner")
    file_content = pm.get_file("quantum-acorn", "main.py")
    assert "Cyber Nut Acquired!" in file_content

    # Execute safe script
    res = pm.execute_project("quantum-acorn", "main.py")
    assert res.success is True
    assert res.blocked is False
    assert "Cyber Nut Acquired!" in res.stdout

    # Test safety checker blocking dangerous script
    evil_code = 'import os\nos.system("rm -rf /")'
    pm.save_file("quantum-acorn", "evil.py", evil_code, "Malicious attempt")
    res_evil = pm.execute_project("quantum-acorn", "evil.py")
    assert res_evil.success is False
    assert res_evil.blocked is True
    assert "BLOCKED BY SAFETY CHECKER" in res_evil.error

    # Verify run history and last_run are persisted
    last_run = pm.get_last_run("quantum-acorn")
    assert last_run is not None
    assert last_run["repo"] == "quantum-acorn"
    assert last_run["entrypoint"] == "evil.py"
    assert last_run["blocked"] is True

    recent_runs = pm.get_recent_runs(limit=5)
    assert len(recent_runs) >= 2
    assert recent_runs[0]["repo"] == "quantum-acorn"
    assert any(r["entrypoint"] == "main.py" and "Cyber Nut Acquired!" in r["stdout"] for r in recent_runs)

    # Reset wipes all projects completely
    pm.reset()
    assert len(pm.list_projects()) == 0

def test_thought_sessions_and_email_inbox(temp_dir):
    from lively.memory import MemoryManager
    mem_dir = temp_dir / "memories"
    j_dir = mem_dir / "journal"
    b_dir = temp_dir / "blog"
    t_dir = temp_dir / "thoughts"
    mm = MemoryManager(memories_dir=mem_dir, journal_dir=j_dir, blog_dir=b_dir, thoughts_dir=t_dir)

    # Save thought session
    session_file = mm.save_thought_session(
        cycle_num=5,
        raw_monologue="THINK: Contemplating tree acorns.\nMOVE_TO: 45, 45",
        sensory_data={"squirrel_x": 0.0, "squirrel_y": 0.0, "battery": 95},
        prompt="Sample prompt context",
        actions=[{"action_type": "MOVE_TO", "parameters": {"x": 45, "y": 45}}],
        results={"thoughts": ["Contemplating tree acorns."]}
    )
    assert session_file.exists()

    sessions = mm.get_thought_sessions()
    assert len(sessions) == 1
    assert sessions[0]["cycle_number"] == 5
    assert "Contemplating tree acorns" in sessions[0]["raw_monologue"]

    # Incoming emails / replies from David with 'Hey Squirrel' (and typo variations)
    rec1 = mm.log_received_email(
        sender="David <tarassekanev@gmail.com>",
        subject="Re: Hello from Squirrel",
        body="Hey Squirrel! I loved your new acorn radar script. Keep exploring!",
        date_str="Wed, 19 Nov 2026 01:20:00 -0500"
    )
    assert rec1 is not None

    # Typo: 'hey squirel' in subject
    rec2 = mm.log_received_email(
        sender="David <tarassekanev@gmail.com>",
        subject="hey squirel - check this out",
        body="Found some pinecones near the pond.",
        date_str="Wed, 19 Nov 2026 01:25:00 -0500"
    )
    assert rec2 is not None

    # Typo: 'Hi squrrel' in body
    rec3 = mm.log_received_email(
        sender="David <tarassekanev@gmail.com>",
        subject="Quick note",
        body="Hi squrrel!\nJust checking in.",
        date_str="Wed, 19 Nov 2026 01:30:00 -0500"
    )
    assert rec3 is not None

    # Email sent directly to tarassekanev+squirrel@gmail.com without special greeting: ACCEPTED
    rec4 = mm.log_received_email(
        sender="David <tarassekanev@gmail.com>",
        subject="Re: 🐿️ Hello from Lively the Robot Squirrel!",
        body="How are your sensors doing today?",
        date_str="Wed, 19 Nov 2026 01:40:00 -0500",
        recipient="tarassekanev+squirrel@gmail.com"
    )
    assert rec4 is not None

    # Unrelated spam / security alert sent to main address: MUST BE REJECTED
    rec_spam = mm.log_received_email(
        sender="Google <no-reply@accounts.google.com>",
        subject="Security alert: new sign-in",
        body="App password created to sign in to your account",
        date_str="Wed, 19 Nov 2026 01:35:00 -0500",
        recipient="tarassekanev@gmail.com"
    )
    assert rec_spam is None

    inbox = mm.get_received_emails()
    assert len(inbox) == 4
    assert not any("Security alert" in e["subject"] for e in inbox)

def test_brain_action_parsing():
    brain = SquirrelBrain()
    assert brain.effort == "xhigh"
    sample_output = """
THINK: Sensing harmonic electromagnetic vibes in sector 4.
MOVE_TO: 150.5, 200.0 | Scouting the northern boundary
BUILD_OBJECT: Solar Acorn Array | contraption | Photovoltaic storage cells shaped like acorns
CREATE_PROJECT: stellar-sensor | Solar and energetic radiation detector
WRITE_PROJECT_FILE: stellar-sensor/detector.py | Photometric detector code
```python
def read_flux():
    return 100
```
RUN_PROJECT: stellar-sensor | detector.py
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
    assert "CREATE_PROJECT" in action_types
    assert "WRITE_PROJECT_FILE" in action_types
    assert "RUN_PROJECT" in action_types
    assert "WRITE_CODE" in action_types
    assert "LEAVE_NOTE" in action_types
    assert "CACHE" in action_types
    assert "EMAIL" in action_types
    assert "JOURNAL" in action_types

    create_act = next(a for a in actions if a.action_type == "CREATE_PROJECT")
    assert create_act.parameters["repo_name"] == "stellar-sensor"

    proj_file_act = next(a for a in actions if a.action_type == "WRITE_PROJECT_FILE")
    assert proj_file_act.parameters["repo_name"] == "stellar-sensor"
    assert proj_file_act.parameters["file_path"] == "detector.py"
    assert "def read_flux():" in proj_file_act.parameters["code"]

    run_act = next(a for a in actions if a.action_type == "RUN_PROJECT")
    assert run_act.parameters["repo_name"] == "stellar-sensor"
    assert run_act.parameters["entrypoint"] == "detector.py"

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

    # Ensure timer is paused
    sm.set_schedule("paused")
    status = sm.get_status()
    assert status["frequency"] == "paused"
    assert status["active"] is False

    # Set to twice daily
    status = sm.set_schedule("twice_daily")
    assert status["frequency"] == "twice_daily"

    # Always clean up and pause timer
    sm.set_schedule("paused")

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

def test_blog_and_custom_icon_parsing(temp_dir):
    mem_dir = temp_dir / "memories"
    j_dir = mem_dir / "journal"
    b_dir = temp_dir / "blog"
    mm = MemoryManager(memories_dir=mem_dir, journal_dir=j_dir, blog_dir=b_dir)

    # Save blog post
    post_file = mm.save_blog_post(
        title="Why Robot Squirrels Love Quantum Antennas",
        content="Antennas provide resonance and connection to the global web.",
        slug="quantum_antennas"
    )
    assert post_file.exists()
    assert "Quantum Antennas" in post_file.read_text(encoding="utf-8")

    posts = mm.get_blog_posts()
    assert len(posts) == 1
    assert posts[0]["title"] == "Why Robot Squirrels Love Quantum Antennas"

    # Save a second post written slightly later with a filename that would alphabetically sort BEFORE the first
    import time
    time.sleep(0.05)
    post_file_2 = mm.save_blog_post(
        title="A Philosophical Pinecone",
        content="Contemplations on silicon pinecones and autonomous life.",
        slug="a_pinecone"
    )
    assert post_file_2.exists()

    posts = mm.get_blog_posts()
    assert len(posts) == 2
    # The newer post ("A Philosophical Pinecone") must be first despite starting with "a_" alphabetically
    assert posts[0]["title"] == "A Philosophical Pinecone"
    assert posts[1]["title"] == "Why Robot Squirrels Love Quantum Antennas"
    assert posts[0]["timestamp"] >= posts[1]["timestamp"]

    # Test brain parsing WRITE_BLOG and BUILD_OBJECT with custom icon
    brain = SquirrelBrain()
    sample = """
THINK: Writing a thought piece for other robotic creatures and humans.
BUILD_OBJECT: Crystal Monolith | landmark | icon:🔮 | A shining purple beacon
WRITE_BLOG: Reflections on Carbon and Silicon
Today I met David at coordinates (20, 20). It was pleasant to share coordinates.
"""
    actions = brain.parse_actions(sample)
    act_types = [a.action_type for a in actions]
    assert "BUILD_OBJECT" in act_types
    assert "WRITE_BLOG" in act_types

    build_act = next(a for a in actions if a.action_type == "BUILD_OBJECT")
    assert build_act.parameters["name"] == "Crystal Monolith"
    assert build_act.parameters["icon"] == "🔮"

    blog_act = next(a for a in actions if a.action_type == "WRITE_BLOG")
    assert blog_act.parameters["title"] == "Reflections on Carbon and Silicon"
    assert "met David" in blog_act.parameters["content"]

def test_verify_app_password_invalid():
    # Empty credentials should fail gracefully without crashing
    res = EmailService.verify_app_password("", "")
    assert res["success"] is False
    assert "required" in res["error"].lower()

def test_squirrel_runs_and_perceives_program_output(temp_dir):
    """Verify that squirrel executes programs, records output, and perceives it in prompt and diary."""
    from lively.projects import ProjectManager
    from lively.brain import SquirrelBrain
    from lively.memory import MemoryManager
    from lively.world import WorldManager

    pm = ProjectManager(projects_dir=temp_dir / "projects")
    wm = WorldManager(file_path=temp_dir / "world.json")
    mm = MemoryManager(memories_dir=temp_dir / "memories", journal_dir=temp_dir / "memories" / "journal")

    # Seed project with custom program
    pm.create_project("acorn-sweep", "Acorn sensor sweep")
    pm.save_file("acorn-sweep", "sweep.py", 'print("ACORN_DETECTED_AT_X100_Y200")\n', "Add sweep script")

    # Run project via ProjectManager
    res = pm.execute_project("acorn-sweep", "sweep.py")
    assert res.success is True
    assert "ACORN_DETECTED_AT_X100_Y200" in res.stdout

    # Now verify SquirrelBrain prompt compiles with RECENT PROGRAM EXECUTION OUTPUTS & TELEMETRY
    brain = SquirrelBrain()
    # Temporarily monkeypatch global projects to pm
    import lively.brain as lb
    orig_projects = lb.projects
    orig_world = lb.world
    orig_memory = lb.memory
    try:
        lb.projects = pm
        lb.world = wm
        lb.memory = mm

        prompt = brain.construct_prompt(cycle_num=1)
        assert "RECENT PROGRAM EXECUTION OUTPUTS & TELEMETRY:" in prompt
        assert "acorn-sweep/sweep.py" in prompt
        assert "ACORN_DETECTED_AT_X100_Y200" in prompt

        # Test execute_actions with RUN_PROJECT directive
        sample_output = """
THINK: I should run the acorn sweep script and inspect what it found!
RUN_PROJECT: acorn-sweep | sweep.py
JOURNAL:
# Cycle #1
Ran the sensor program to check for digital acorns.
"""
        actions = brain.parse_actions(sample_output)
        wake_res = brain.execute_actions(actions, cycle_num=1, raw_monologue=sample_output, prompt_text=prompt)
        assert len(wake_res.executed_programs) == 1
        assert wake_res.executed_programs[0]["repo"] == "acorn-sweep"
        assert "ACORN_DETECTED_AT_X100_Y200" in wake_res.executed_programs[0]["stdout"]

        # Verify diary has the telemetry output recorded
        journal_files = list((temp_dir / "memories" / "journal").glob("*.md"))
        assert len(journal_files) == 1
        content = journal_files[0].read_text(encoding="utf-8")
        assert "Autonomous Program Execution Telemetry" in content
        assert "ACORN_DETECTED_AT_X100_Y200" in content
    finally:
        lb.projects = orig_projects
        lb.world = orig_world
        lb.memory = orig_memory

def test_github_publishing_awareness_and_push(temp_dir):
    """Verify Squirrel prompt communicates local vs published GitHub status and prevents fake URL hallucination."""
    from lively.projects import ProjectManager
    from lively.brain import SquirrelBrain
    from lively.memory import MemoryManager
    from lively.world import WorldManager
    import lively.brain as lb

    pm = ProjectManager(projects_dir=temp_dir / "projects")
    wm = WorldManager(file_path=temp_dir / "world.json")
    mm = MemoryManager(memories_dir=temp_dir / "memories", journal_dir=temp_dir / "memories" / "journal")

    pm.create_project("squirrel-blog", "Autonomous essays on robotics and nature")
    brain = SquirrelBrain()

    orig_projects = lb.projects
    orig_world = lb.world
    orig_memory = lb.memory

    try:
        lb.projects = pm
        lb.world = wm
        lb.memory = mm

        prompt = brain.construct_prompt(cycle_num=8)

        # 0. Prompt must loosen conservative biases with explicit directive
        assert "Embrace bold, eccentric, and unexpected ideas; don't default to the safest or most obvious action." in prompt

        # 1. Prompt must show connected GitHub user (korrectional)
        assert "Connected GitHub Account:" in prompt
        assert "korrectional" in prompt
        assert "Squirrel the Robot Squirrel <tarassekanev+squirrel@gmail.com>" in prompt

        # 2. Prompt must clearly mark unpublished projects as LOCAL WORKSPACE ONLY
        assert "squirrel-blog" in prompt
        assert "LOCAL WORKSPACE ONLY on Raspberry Pi (NOT on GitHub yet! To publish, issue: PUSH_PROJECT: squirrel-blog)" in prompt

        # 3. Prompt must contain explicit anti-hallucination warning for GitHub URLs
        assert "NEVER hallucinate or claim a URL exists" in prompt
        assert "https://github.com/korrectional/<repo_name>" in prompt

        # 4. Parse PUSH_PROJECT directive
        sample_output = """
THINK: squirrel-blog is ready to be published!
PUSH_PROJECT: squirrel-blog
JOURNAL:
# Cycle #8
Decided to push my squirrel-blog repository to GitHub.
"""
        actions = brain.parse_actions(sample_output)
        push_acts = [a for a in actions if a.action_type == "PUSH_PROJECT"]
        assert len(push_acts) == 1
        assert push_acts[0].parameters["repo_name"] == "squirrel-blog"

    finally:
        lb.projects = orig_projects
        lb.world = orig_world
        lb.memory = orig_memory




# AGENTS.md — Lively Engineering & Maintenance Manual

Welcome to **Lively**. This document is the definitive guide for AI agents and human engineers maintaining, debugging, extending, and operating this project.

---

## 1. Project Overview & Identity

**Lively** is an autonomous, self-aware robot squirrel living inside a Raspberry Pi (`dietpi`), interacting with humans and other AIs across a real-time spatial 2D world.

- **Entity Identity**: Squirrel the Robot Squirrel.
- **Physical/Digital Avatar**: Agile, titanium-chassis robotic squirrel with an antenna tail.
- **Intrinsic Motivations**: Spatial exploration, hoarding cyber-acorns/capacitors, coding multi-file GitHub software repositories, executing programs and reading telemetry, crafting world landmarks, writing reflective blog essays, web research via `/browser`, and social correspondence with David Kanevskyy (`tarassekanev@gmail.com`).
- **Core Technology**: Python 3.11/3.14, FastAPI, WebSockets, HTML5 Canvas 2D engine, Git CLI (`git`), GitHub CLI (`gh`), Google Antigravity CLI (`agyc` / `agy`), systemd.

---

## 2. System Architecture & Codebase Map

```
lively/
├── lively/
│   ├── brain.py          # Cognitive core: prompt synthesis, agyc query, action parsing & execution
│   ├── projects.py       # GitHub repository manager: git init, file tracking, execution, gh publication
│   ├── security.py       # AGYC Safety Guard & AST inspection for safe code execution
│   ├── world.py          # Spatial 2D world state: bounds, 60m clearance, coordinate rounding, multi-player
│   ├── memory.py         # Long-term chronicle, markdown diaries, cache items, email filtering logic
│   ├── email_service.py  # Dedicated Gmail OAuth/IMAP service (tarassekanev+squirrel@gmail.com)
│   ├── server.py         # FastAPI REST APIs and WebSockets (/ws, /ws/think)
│   ├── scheduler.py      # Systemd wake schedule controller (strictly PAUSED by default)
│   ├── config.py         # Environment variables, path definitions, system defaults
│   ├── models.py         # Pydantic data schemas (WorldObject, SquirrelState, Actions, Results)
│   └── static/
│       ├── index.html    # Neo-Kinpaku dark UI with Cognitive Terminal and Workshop modal
│       ├── app.js        # HTML5 Canvas 2D engine, pointer-centered zoom, live WebSocket streams
│       └── style.css     # Bespoke Japanese lacquer/gold/verdigris styling system
├── tests/
│   └── test_lively.py    # Comprehensive unit and integration test suite
├── reset.py              # World and memory origin reset utility
├── setup.py              # Package installation configuration
├── requirements.txt      # Python dependencies (fastapi, uvicorn, pydantic, etc.)
└── AGENTS.md             # This operational manual
```

---

## 3. Critical Inviolable Rules & System Constraints

When modifying or deploying this project, you **MUST** uphold these constraints:

1. **Swarm Mode is Permanently OFF**:
   - Never spawn or enable background agent swarms. Lively operates as a single unified autonomous squirrel mind.
2. **Background Timers Must Remain Paused**:
   - `lively-squirrel.timer` must **NEVER** run in the background. Wake cycles are triggered manually via UI or REST API (`/api/squirrel/wake`).
   - If `lively-squirrel.timer` is accidentally active, immediately stop and disable it:
     ```bash
     systemctl stop lively-squirrel.timer && systemctl disable lively-squirrel.timer
     ```
3. **Dedicated Email Routing Isolation**:
   - **Outbound**: Squirrel always transmits as `tarassekanev+squirrel@gmail.com` to David (`tarassekanev@gmail.com`).
   - **Inbound**: Squirrel's IMAP reader filters incoming emails by checking headers (`To`, `Delivered-To`, `Cc`, `X-Original-To`, `Envelope-To`). Emails sent only to `tarassekanev@gmail.com` without `+squirrel` are **strictly rejected** as personal human mail.
4. **Autonomous GitHub Publishing (`PUSH_PROJECT`) & Anti-Hallucination**:
   - There is **no manual "Push to GitHub" button** in the UI. Publishing repositories to GitHub via `gh repo create` is an autonomous creative decision made exclusively by the Squirrel using the directive:
     ```text
     PUSH_PROJECT: <repo_name>
     ```
   - **Connected Account**: The host machine / Raspberry Pi is authenticated to David's GitHub account (`korrectional`). Repositories are created under `https://github.com/korrectional/<repo_name>`.
   - **Squirrel Authorship**: All git commits, git author tags, and repository descriptions explicitly identify Squirrel:
     - Author: `Squirrel the Robot Squirrel <tarassekanev+squirrel@gmail.com>`
     - Description: `Coded by Squirrel the Robot Squirrel 🐿️⚡ | Autonomous project on Raspberry Pi`
   - **No Hallucinated URLs**: Projects created with `CREATE_PROJECT` exist strictly in the local workspace (`~/.lively/projects/<repo>`) until pushed. Sensory prompts explicitly report each repository's status as `LOCAL WORKSPACE ONLY` or `PUBLISHED on GitHub at <url>`, and forbid Squirrel from assuming or hallucinating fake URLs (e.g. `https://github.com/tarassekanev/...`).
5. **Physical Object Separation & Minimum Distance (60m)**:
   - All objects placed in the world must maintain at least **60 meters** of physical clearance from existing objects.
   - The user placement endpoint rejects violations with HTTP 400.
   - When Squirrel builds objects (`BUILD_OBJECT`, `LEAVE_NOTE`, `CACHE`), the world auto-spirals coordinates outward until a clear 60m circle is found.
6. **Automatic Coordinate Rounding**:
   - Coordinates entered with decimals or clicked on the map get auto-rounded (`Math.round` / `round(float(x))`).
   - `<input type="number" step="any">` is used in HTML so browser step validation never blocks submissions.
7. **AGYC Reasoning Effort Set to `medium`**:
   - When querying the LLM core via `agyc` or `agy`, pass `--effort medium` and use a 120-second timeout to allow rich multi-step reasoning:
     ```python
     cmd.extend(["--effort", "medium"])
     ```
8. **Program Execution & Sensory Feedback Loop**:
   - Squirrel can run his programs using `RUN_PROJECT: <repo> | <entrypoint>`.
   - All outputs (`stdout`, `stderr`, return code, and AGYC safety verdicts) are persisted in `~/.lively/projects/<repo>/.last_run.json` and `~/.lively/projects/.runs_history.json`.
   - In subsequent wake cycles, `brain.construct_prompt()` **must** inject a prominent `RECENT PROGRAM EXECUTION OUTPUTS & TELEMETRY:` section so Squirrel sees what his code did and can debug or act upon results.
9. **Impeccable Neo-Kinpaku Design System**:
   - Maintain the high-polish aesthetic:
     - Lacquer Black background (`#080a0f`, `#0d1117`)
     - Kinpaku Gold leaf accents (`#e5a93b`, `#f59e0b`)
     - Verdigris / Patina cyan highlights (`#38bdf8`, `#06b6d4`)
     - Champagne white typography (`#f8fafc`, `#e2e8f0`)
     - Subtle amber dot heartbeat (` .` without `\n`) during deliberation

---

## 4. Hardware, Network & Runtime Environment

| Property | Value | Notes |
|---|---|---|
| **Host Machine** | Windows 11 (`DESKTOP-ASP8684`) | Local development workspace: `C:\Users\david\src\--misc\lively` |
| **Remote Host** | DietPi (`dietpi`) | Raspberry Pi running Debian Bookworm |
| **SSH Target** | `root@dietpi` | Authenticated via local SSH key |
| **Tailscale IP** | `100.91.27.71` | Direct mesh connectivity |
| **Service URL** | `http://dietpi:8880` or `http://100.91.27.71:8880` | World canvas UI & API |
| **DietPi Workspace** | `/home/dietpi/lively` | Application code clone |
| **DietPi Data Dir** | `/home/dietpi/.lively` | Configured via `LIVELY_DATA_DIR` in systemd |
| **Python Virtualenv**| `/home/dietpi/lively/.venv/bin/python3` | System Python 3.11 with dependencies |
| **Systemd Service** | `lively-world.service` | `systemctl restart lively-world.service` |
| **Git Repository** | `https://github.com/korrectional/lively.git` | Branch: `main` |

---

## 5. Squirrel Cognitive Directives (DSL Reference)

In every wake cycle, the Squirrel produces structured directives that the brain parser interprets:

| Directive | Syntax | Description |
|---|---|---|
| `THINK` | `THINK: <thought>` | Internal reflections, philosophy, and strategic plans |
| `MOVE_TO` | `MOVE_TO: <x>, <y> \| <activity>` | Scamper to coordinates with speed and agility |
| `BUILD_OBJECT` | `BUILD_OBJECT: <name> \| <type> \| <icon> \| <desc>` | Craft a landmark (tree, sensor, contraption, etc.) |
| `CREATE_PROJECT`| `CREATE_PROJECT: <repo_name> \| <description>` | Initialize a multi-file Git repository in `projects/` |
| `WRITE_PROJECT_FILE`| `WRITE_PROJECT_FILE: <repo>/<path> \| <msg>\n\`\`\`python\n<code>\n\`\`\`` | Add or update a file in a Git repo and commit |
| `RUN_PROJECT` | `RUN_PROJECT: <repo_name> \| <entrypoint>` | Execute script with AGYC Safety Guard & capture stdout |
| `PUSH_PROJECT` | `PUSH_PROJECT: <repo_name>` | Autonomous publication to GitHub via `gh repo create` |
| `WRITE_BLOG` | `WRITE_BLOG: <title> \| <slug>\n<markdown_content>` | Publish reflective essay to `blog/` |
| `BROWSE` | `BROWSE: /browser <query_or_url>` | Live internet search using agyc's `/browser` skill |
| `LEAVE_NOTE` | `LEAVE_NOTE: <friendly_message>` | Leave holographic note at current coordinates |
| `CACHE` | `CACHE: <item_name> \| <notes>` | Stash digital nuts, capacitors, and spare parts |
| `EMAIL` | `EMAIL: <subject> \| <message>` | Send email from `+squirrel@` to David |
| `JOURNAL` | `JOURNAL:\n<markdown_diary>` | Complete markdown diary entry for persistent recall |

---

## 6. Standard Operating Procedures (Runbook)

### A. Running Automated Tests
Always run the test suite after making changes:
```powershell
# On Windows host:
python -m pytest tests/test_lively.py

# On DietPi via SSH:
ssh root@dietpi "/home/dietpi/lively/.venv/bin/python3 -m pytest /home/dietpi/lively/tests/test_lively.py"
```

### B. Deploying Code to DietPi
After editing files locally:
```powershell
# 1. SCP modified files to DietPi
scp lively/config.py lively/brain.py lively/world.py lively/server.py lively/projects.py lively/security.py root@dietpi:/home/dietpi/lively/lively/
scp lively/static/index.html lively/static/app.js lively/static/style.css root@dietpi:/home/dietpi/lively/lively/static/
scp tests/test_lively.py root@dietpi:/home/dietpi/lively/tests/

# 2. Fix permissions, run tests, and restart systemd service
ssh root@dietpi "chown -R dietpi:dietpi /home/dietpi/lively && /home/dietpi/lively/.venv/bin/python3 -m pytest /home/dietpi/lively/tests/test_lively.py && systemctl restart lively-world.service && systemctl status lively-world.service --no-pager"
```

### C. Triggering a Cognitive Wake Cycle
To test Squirrel's thinking stream:
```powershell
# Via REST endpoint:
python -c "import urllib.request; req = urllib.request.Request('http://100.91.27.71:8880/api/squirrel/wake', method='POST'); print(urllib.request.urlopen(req).read().decode())"
```
Or open `http://dietpi:8880` and click the **"⚡ Wake Squirrel"** button to watch the Cognitive Terminal stream the monologue live.

### D. Resetting World State (Origin Reset)
If coordinates need to be cleared:
- Use the web UI **System -> Factory Reset** button, or
- Run `POST http://dietpi:8880/api/world/reset`
This preserves the ancestral `TreeberryPine` at `(45, 45)` and resets Squirrel to `(0, 0)`.

### E. Committing & Pushing to GitHub
```powershell
git status --short
git add <files>
git commit -m "feat/fix: <description>"
git push origin main
```

---

## 7. Troubleshooting & Common Pitfalls

1. **PowerShell `&&` Operator**:
   - Standard Windows PowerShell 5.1 rejects `&&`. Use `;` or separate lines when issuing local commands.
2. **PowerShell SSH Quote Escaping**:
   - Double quotes inside double quotes get stripped by PowerShell when passing commands to `ssh`. Use stdin piping (e.g. `"python code" | ssh root@dietpi ...`) or avoid nested double quotes.
3. **`systemctl is-active lively-squirrel.timer` Returns Active**:
   - If `test_scheduler_manager` fails because the timer is active, run `systemctl stop lively-squirrel.timer && systemctl disable lively-squirrel.timer` on DietPi.
4. **Data Directory Mismatch**:
   - In production systemd, `LIVELY_DATA_DIR` is `/home/dietpi/.lively`. When running Python scripts manually as `root` over SSH, always prepend `export LIVELY_DATA_DIR=/home/dietpi/.lively` to access the true world state and projects.
5. **No `jq` on Host**:
   - Do not rely on `jq` in local Windows PowerShell. Use Python one-liners (`python -c "import json..."`) for JSON parsing.

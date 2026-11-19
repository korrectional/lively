"""
FastAPI World Server and WebSocket Hub for Lively.
Provides real-time 2D spatial updates, REST APIs, and static web UI hosting.
"""

import json
import asyncio
from pathlib import Path
from typing import Set, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lively.config import SERVER_HOST, SERVER_PORT, TAILSCALE_BASE_URL, USER_EMAIL
from lively.world import world
from lively.memory import memory
from lively.projects import projects
from lively.brain import brain
from lively.email_service import email_service
from lively.scheduler import scheduler

app = FastAPI(title="Lively: Robot Squirrel World", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Connected WebSockets
active_connections: Set[WebSocket] = set()

class NewObjectRequest(BaseModel):
    name: str
    x: float
    y: float
    type: str = "landmark"
    icon: str = ""
    description: str = ""

class NewProjectRequest(BaseModel):
    repo_name: str = ""
    filename: str = ""
    code: str = ""
    description: str = ""
    relative_path: str = ""

class ScheduleChangeRequest(BaseModel):
    frequency: str  # paused, daily, twice_daily, four_daily, hourly, custom
    custom_on_calendar: Optional[str] = None

class CodeRunRequest(BaseModel):
    entrypoint: str = "main.py"
    timeout: int = 15

async def broadcast(message: Dict[str, Any]):
    """Broadcast JSON payload to all connected clients."""
    stale = []
    text = json.dumps(message)
    for ws in list(active_connections):
        try:
            await ws.send_text(text)
        except Exception:
            stale.append(ws)
    for ws in stale:
        active_connections.discard(ws)

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the 2D world interactive UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Lively World Server</h1><p>index.html not found</p>")

@app.get("/api/world")
async def get_world_state():
    """Retrieve full spatial state."""
    return world.get_state()

@app.post("/api/world/reset")
async def reset_world():
    """Reset world, memories, and projects to origin."""
    world.reset()
    memory.reset()
    projects.reset()
    st = world.get_state()
    await broadcast({
        "type": "world_reset",
        "world": st
    })
    return {"success": True, "world": st}

@app.post("/api/objects")
async def add_world_object(req: NewObjectRequest):
    """Add a new object or landmark to the world."""
    obj = world.add_object(
        name=req.name,
        x=req.x,
        y=req.y,
        obj_type=req.type,
        icon=req.icon,
        description=req.description,
        created_by="user"
    )
    await broadcast({"type": "object_added", "object": obj.model_dump()})
    return obj.model_dump()

@app.delete("/api/objects/{obj_id}")
async def delete_world_object(obj_id: str):
    """Delete an object from the world."""
    success = world.remove_object(obj_id)
    if not success:
        raise HTTPException(status_code=404, detail="Object not found")
    await broadcast({"type": "object_removed", "id": obj_id})
    return {"success": True}

@app.get("/api/memories")
async def get_memories():
    """Retrieve journal entries and summaries."""
    return {
        "journals": memory.get_all_journals(),
        "summary": memory.get_long_term_summary(),
        "caches": memory.get_caches(),
        "sent_emails": memory.get_sent_emails()
    }

@app.get("/api/projects")
async def list_projects():
    """List squirrel GitHub project repositories."""
    return projects.list_projects()

@app.get("/api/projects/{repo_name}")
async def get_project_details(repo_name: str):
    """Retrieve details, commits, and file tree for a project repository."""
    proj = projects.get_project(repo_name)
    if not proj:
        raise HTTPException(status_code=404, detail=f"Project repository '{repo_name}' not found")
    return proj

@app.get("/api/projects/{repo_name}/file")
async def get_project_file(repo_name: str, path: str = "main.py"):
    """Get the source code of a specific file in a project repository."""
    content = projects.get_file(repo_name, path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found in project '{repo_name}'")
    return {"repo": repo_name, "path": path, "content": content}

@app.post("/api/projects")
async def create_or_save_project(req: NewProjectRequest):
    """Create a new GitHub repository or save/update a file within a project."""
    repo = req.repo_name or (req.filename.split(".")[0] if req.filename else "squirrel-project")
    rel_path = req.relative_path or req.filename or "main.py"
    
    if req.code:
        result = projects.save_file(
            repo_name=repo,
            relative_path=rel_path,
            content=req.code,
            commit_msg=req.description or f"Update {rel_path}"
        )
    else:
        result = projects.create_project(repo_name=repo, description=req.description)

    await broadcast({
        "type": "project_added",
        "repo": repo
    })
    return result

@app.post("/api/projects/{repo_name}/run")
async def run_project(repo_name: str, req: CodeRunRequest = CodeRunRequest()):
    """Execute an entrypoint script within a project with AGYC Safety Checker."""
    result = projects.execute_project(
        repo_name=repo_name,
        entrypoint=req.entrypoint,
        timeout_sec=req.timeout
    )
    return result.model_dump()

# Mind Logs & Thought Session Archives
@app.get("/api/thoughts")
async def list_thought_sessions(limit: int = 30):
    """List archived thought sessions and AI cognition traces."""
    return memory.get_thought_sessions(limit=limit)

@app.get("/api/thoughts/{filename}")
async def get_thought_session(filename: str):
    """Get full session transcript for a specific wake cycle."""
    session = memory.get_thought_session(filename)
    if not session:
        raise HTTPException(status_code=404, detail=f"Thought session '{filename}' not found")
    return session

# Incoming Emails & Two-way Communication
@app.get("/api/email/inbox")
async def get_email_inbox():
    """Retrieve incoming email replies from David."""
    return memory.get_received_emails()

@app.post("/api/email/check")
async def check_email_inbox():
    """Trigger a live IMAP fetch to check for new email replies from David."""
    loop = asyncio.get_event_loop()
    emails = await loop.run_in_executor(None, email_service.fetch_incoming_emails, 5)
    return {"success": True, "count": len(emails), "emails": emails}

@app.post("/api/squirrel/wake")
async def trigger_wake_cycle():
    """Manually trigger a squirrel wake and cognitive cycle."""
    loop = asyncio.get_event_loop()
    cycle_res = await loop.run_in_executor(None, brain.run_cycle)
    await broadcast({
        "type": "squirrel_wake",
        "result": cycle_res.model_dump(),
        "world": world.get_state()
    })
    return cycle_res.model_dump()

@app.post("/api/squirrel/think")
async def trigger_think_trace():
    """Execute cognitive cycle and return all step-by-step thinking traces."""
    loop = asyncio.get_event_loop()
    def _run():
        steps = []
        gen = brain.think_trace()
        try:
            while True:
                steps.append(next(gen))
        except StopIteration as e:
            res = e.value
            return {"steps": steps, "result": res.model_dump(), "world": world.get_state()}
    data = await loop.run_in_executor(None, _run)
    await broadcast({
        "type": "squirrel_wake",
        "result": data["result"],
        "world": data["world"]
    })
    return data

@app.websocket("/ws/think")
async def websocket_think_stream(ws: WebSocket):
    """Real-time streaming WebSocket for watching Lively think live."""
    await ws.accept()
    try:
        loop = asyncio.get_event_loop()
        gen = brain.think_trace()
        for step in gen:
            await ws.send_text(json.dumps(step))
            await asyncio.sleep(0.08) # Natural reading pacing
        # Broadcast final result to all world viewers
        await broadcast({
            "type": "squirrel_wake",
            "world": world.get_state()
        })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"stage": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass

class GmailSettingsRequest(BaseModel):
    method: str = "oauth"  # "oauth" or "app_password"
    user_email: str
    client_id: str = ""
    client_secret: str = ""
    app_password: str = ""

class TestEmailRequest(BaseModel):
    subject: str = "Hello from Lively!"
    body: str = "This is a test message from your robot squirrel!"

# Schedule Configuration & Endpoints
@app.get("/api/settings/schedule")
async def get_schedule_settings():
    """Retrieve current wake cycle timer status and cadence."""
    return scheduler.get_status()

@app.post("/api/settings/schedule")
async def update_schedule_settings(req: ScheduleChangeRequest):
    """Update how often the squirrel runs (paused, daily, twice_daily, four_daily, hourly, custom)."""
    status = scheduler.set_schedule(
        frequency=req.frequency,
        custom_on_calendar=req.custom_on_calendar
    )
    await broadcast({
        "type": "schedule_updated",
        "schedule": status
    })
    return status

@app.get("/api/system/info")
async def get_system_info():
    """System diagnostics and telemetry."""
    import socket
    import platform
    sq = world.squirrel
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "tailscale_url": TAILSCALE_BASE_URL,
        "user_email": USER_EMAIL,
        "squirrel_battery": sq.battery,
        "squirrel_position": (sq.x, sq.y),
        "total_cycles": sq.total_cycles,
        "total_distance": sq.total_distance_traveled,
        "objects_count": len(world.objects),
        "projects_count": len(projects.list_projects()),
        "schedule": scheduler.get_status(),
        "gmail_connected": email_service.is_authenticated()
    }

class ConnectAppPasswordRequest(BaseModel):
    user_email: str
    app_password: str

@app.get("/api/blog")
async def get_blog_posts():
    """List blog posts authored by Squirrel."""
    return memory.get_blog_posts()

# Gmail Configuration & Endpoints
@app.get("/api/settings/gmail")
async def get_gmail_settings():
    """Retrieve current email settings."""
    cfg = email_service.get_settings()
    # Mask secrets
    if cfg.get("app_password"):
        cfg["app_password_masked"] = "••••••••••••••••"
    if cfg.get("client_secret"):
        cfg["client_secret_masked"] = "••••" + cfg["client_secret"][-4:] if len(cfg["client_secret"]) > 4 else "••••"
    return cfg

@app.post("/api/settings/gmail/connect")
async def connect_gmail_app_password(req: ConnectAppPasswordRequest):
    """Verify credentials with Google SMTP and save."""
    verify_res = email_service.verify_app_password(req.user_email, req.app_password)
    if not verify_res["success"]:
        return verify_res

    email_service.save_settings(
        method="app_password",
        user_email=req.user_email,
        app_password=req.app_password
    )
    return {
        "success": True,
        "message": "Connected! Squirrel can now email you.",
        "settings": email_service.get_settings()
    }

@app.post("/api/settings/gmail/disconnect")
async def disconnect_gmail():
    """Disconnect Gmail credentials."""
    email_service.save_settings(method="oauth", user_email=USER_EMAIL, app_password="")
    return {"success": True, "message": "Gmail disconnected.", "authenticated": False}

@app.post("/api/settings/gmail")
async def save_gmail_settings(req: GmailSettingsRequest):
    """Save user email settings."""
    updated = email_service.save_settings(
        method=req.method,
        user_email=req.user_email,
        client_id=req.client_id,
        client_secret=req.client_secret,
        app_password=req.app_password
    )
    return updated

@app.post("/api/test/email")
async def send_test_email(req: TestEmailRequest = TestEmailRequest()):
    """Send an immediate test email to verify credentials."""
    res = email_service.send_email(subject=req.subject, body=req.body)
    return res

@app.get("/auth/gmail")
async def get_gmail_auth_url(request: Request):
    """Return Google OAuth authorization URL."""
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/auth/gmail/callback"
    res = email_service.get_authorization_url(redirect_uri=redirect_uri)
    res["authenticated"] = email_service.is_authenticated()
    return res

@app.get("/auth/gmail/callback")
async def gmail_auth_callback(code: str, request: Request):
    """Callback receiving Google OAuth code."""
    base = str(request.base_url).rstrip("/")
    redirect_uri = f"{base}/auth/gmail/callback"
    try:
        email_service.exchange_code(code, redirect_uri=redirect_uri)
        return HTMLResponse("""
        <html>
            <body style="background:#111; color:#eee; font-family:sans-serif; text-align:center; padding-top:100px;">
                <h1 style="color:#4ade80;">Gmail Authentication Successful!</h1>
                <p>Lively the Robot Squirrel can now email you.</p>
                <a href="/" style="display:inline-block; margin-top:20px; padding:10px 20px; background:#f59e0b; color:#000; text-decoration:none; border-radius:8px; font-weight:bold;">Return to Lively World</a>
            </body>
        </html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html>
            <body style="background:#111; color:#eee; font-family:sans-serif; text-align:center; padding-top:100px;">
                <h1 style="color:#ef4444;">Authentication Failed</h1>
                <p>{e}</p>
                <a href="/" style="color:#38bdf8;">Return</a>
            </body>
        </html>
        """, status_code=400)

@app.get("/auth/gmail/status")
async def gmail_status():
    """Check if Gmail integration is ready."""
    return {"authenticated": email_service.is_authenticated()}

# Real-time WebSocket
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Bidirectional WebSocket for live avatar positioning and world syncing."""
    await ws.accept()
    active_connections.add(ws)
    user_id = f"usr_{id(ws)}"
    try:
        # Initial greeting with full state
        await ws.send_text(json.dumps({
            "type": "welcome",
            "user_id": user_id,
            "state": world.get_state()
        }))

        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "move":
                # User moving avatar
                x = float(data.get("x", 0))
                y = float(data.get("y", 0))
                name = str(data.get("name", "Explorer"))
                avatar_type = str(data.get("avatar_type", "scout"))
                user = world.update_user_position(user_id, name, x, y, avatar_type=avatar_type)
                await broadcast({
                    "type": "user_moved",
                    "user": user.model_dump()
                })
            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Exception: {e}")
    finally:
        active_connections.discard(ws)
        world.remove_user(user_id)
        await broadcast({"type": "user_left", "user_id": user_id})

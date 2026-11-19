"""
Data schemas and models for Lively.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import time
from datetime import datetime, timezone

def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class WorldObject(BaseModel):
    id: str
    name: str
    x: float
    y: float
    type: str = "landmark"  # landmark, tree, cache, sensor, note, contraption
    icon: str = ""  # Custom emoji or icon identifier
    description: str = ""
    created_by: str = "user"  # "user" or "squirrel"
    created_at: str = Field(default_factory=current_utc_iso)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SquirrelState(BaseModel):
    name: str = "Squirrel"
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0  # Angle in degrees
    battery: int = 100
    current_activity: str = "Resting in TreeberryPine"
    last_thought: str = "System boot sequence complete. Thinking about nuts, coding, and the open grid."
    last_wake_time: Optional[str] = None
    total_cycles: int = 0
    total_distance_traveled: float = 0.0

class UserAvatar(BaseModel):
    id: str
    name: str = "Explorer"
    x: float = 0.0
    y: float = 0.0
    avatar_type: str = "scout"  # scout, mech, nomad, cyberfox, orb
    last_active: float = Field(default_factory=time.time)

class CodedProject(BaseModel):
    filename: str
    description: str = ""
    code: str
    created_at: str = Field(default_factory=current_utc_iso)
    updated_at: str = Field(default_factory=current_utc_iso)

class ProjectRepo(BaseModel):
    name: str
    description: str = ""
    is_git: bool = True
    files: List[str] = Field(default_factory=list)
    commit_count: int = 1
    last_commit_msg: str = "Initial commit"
    readme: str = ""
    created_at: str = Field(default_factory=current_utc_iso)
    updated_at: str = Field(default_factory=current_utc_iso)

class ProjectExecutionResult(BaseModel):
    success: bool
    blocked: bool = False
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    safety_verdict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ThoughtSession(BaseModel):
    filename: str
    cycle_number: int
    timestamp: str
    summary: str
    sensory_scan: Dict[str, Any] = Field(default_factory=dict)
    prompt_snippet: str = ""
    raw_monologue: str = ""
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)

class SquirrelAction(BaseModel):
    action_type: str  # THINK, MOVE_TO, INSPECT, BUILD_OBJECT, WRITE_CODE, CREATE_PROJECT, WRITE_PROJECT_FILE, RUN_PROJECT, WRITE_BLOG, LEAVE_NOTE, CACHE, EMAIL, BROWSE, JOURNAL
    parameters: Dict[str, Any] = Field(default_factory=dict)
    raw_text: str = ""

class WakeCycleResult(BaseModel):
    timestamp: str
    cycle_number: int
    thoughts: List[str] = Field(default_factory=list)
    actions_executed: List[SquirrelAction] = Field(default_factory=list)
    new_position: tuple[float, float]
    journal_entry: str = ""
    email_sent: Optional[Dict[str, str]] = None
    coded_files: List[str] = Field(default_factory=list)
    built_objects: List[str] = Field(default_factory=list)
    blog_posts: List[str] = Field(default_factory=list)
    web_searches: List[Dict[str, str]] = Field(default_factory=list)
    executed_programs: List[Dict[str, Any]] = Field(default_factory=list)
    thought_log_file: str = ""
    error: Optional[str] = None

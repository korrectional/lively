"""
Squirrel Coding Workspace and Inventions Manager.
Persists and runs scripts created by the robot squirrel.
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from lively.config import PROJECTS_DIR, ensure_directories
from lively.models import CodedProject

class ProjectManager:
    """Manages the squirrel's coded files, scripts, and software inventions."""

    def __init__(self, projects_dir: Path = PROJECTS_DIR):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        ensure_directories()
        self._ensure_starter_projects()

    def _ensure_starter_projects(self):
        """Provide an initial starter script if directory is empty."""
        if not list(self.projects_dir.glob("*.*")):
            starter_code = '''#!/usr/bin/env python3
"""
acorn_radar.py - Coded by Lively the Robot Squirrel
Scans the local coordinate matrix for resonance spikes.
"""

import math
import random

def scan_sector(radius=100):
    print(f"[RADAR] Sweeping {radius}m radius around squirrel chassis...")
    pings = random.randint(1, 4)
    print(f"[RADAR] Detected {pings} potential cyber-nut resonance frequencies!")
    for i in range(pings):
        angle = random.uniform(0, 360)
        dist = random.uniform(10, radius)
        x = round(dist * math.cos(math.radians(angle)), 1)
        y = round(dist * math.sin(math.radians(angle)), 1)
        print(f" -> Beacon {i+1}: relative coord ({x}, {y}) [Signal: OK]")
    return pings

if __name__ == "__main__":
    scan_sector()
'''
            self.save_project(
                filename="acorn_radar.py",
                code=starter_code.strip(),
                description="My first sensor radar script to scan for shiny electronic nuts!"
            )

    def reset(self):
        """Wipe all squirrel-coded projects and restore starter radar script."""
        if self.projects_dir.exists():
            for f in self.projects_dir.glob("*.*"):
                try:
                    f.unlink()
                except Exception:
                    pass
        self._ensure_starter_projects()

    def list_projects(self) -> List[CodedProject]:
        """List all projects created by the squirrel."""
        projects = []
        for p in sorted(self.projects_dir.glob("*.*")):
            if p.is_file():
                try:
                    code = p.read_text(encoding="utf-8")
                    desc = ""
                    # Check for docstring preview as description
                    lines = [line.strip() for line in code.splitlines() if line.strip()]
                    if lines and lines[0].startswith('"""') or (len(lines) > 1 and lines[1].startswith('"""')):
                        desc = code.split('"""')[1].strip() if '"""' in code else ""
                    projects.append(CodedProject(
                        filename=p.name,
                        description=desc[:150],
                        code=code,
                        created_at=datetime.fromtimestamp(p.stat().st_ctime).isoformat(),
                        updated_at=datetime.fromtimestamp(p.stat().st_mtime).isoformat()
                    ))
                except Exception:
                    pass
        return projects

    def get_project(self, filename: str) -> Optional[CodedProject]:
        """Retrieve single project by filename."""
        path = self.projects_dir / filename
        if path.exists() and path.is_file():
            code = path.read_text(encoding="utf-8")
            return CodedProject(
                filename=path.name,
                code=code,
                created_at=datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
                updated_at=datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            )
        return None

    def save_project(self, filename: str, code: str, description: str = "") -> CodedProject:
        """Create or update a code file."""
        # Sanitize filename
        safe_name = Path(filename).name
        if not safe_name.endswith((".py", ".sh", ".json", ".md", ".txt", ".html", ".js")):
            safe_name += ".py"
        path = self.projects_dir / safe_name
        path.write_text(code.strip(), encoding="utf-8")
        return CodedProject(
            filename=safe_name,
            description=description,
            code=code.strip()
        )

    def execute_project(self, filename: str, timeout_sec: int = 5) -> dict:
        """Run a Python script and capture output."""
        path = self.projects_dir / Path(filename).name
        if not path.exists():
            return {"success": False, "error": f"File {filename} not found."}
        if not path.suffix == ".py":
            return {"success": False, "error": "Only Python scripts can be executed."}

        try:
            res = subprocess.run(
                [sys.executable, str(path)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(self.projects_dir)
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out after {timeout_sec}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global singleton
projects = ProjectManager()

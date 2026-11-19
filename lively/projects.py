"""
Squirrel GitHub Project and Software Repository Manager.
Manages multi-file Git repositories, code projects, and safe execution with AGYC safety checks.
"""

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from lively.config import PROJECTS_DIR, ensure_directories
from lively.models import ProjectRepo, ProjectExecutionResult, current_utc_iso
from lively.security import check_safety, SafetyVerdict

class ProjectManager:
    """Manages squirrel's full GitHub-style project repositories."""

    def __init__(self, projects_dir: Path = PROJECTS_DIR):
        self.projects_dir = Path(projects_dir)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        ensure_directories()
        self._ensure_starter_projects()

    def _run_git(self, repo_dir: Path, *args) -> tuple[int, str]:
        """Execute git command within a repository directory."""
        git_bin = shutil.which("git")
        if not git_bin:
            return 1, "Git not installed on system."
        try:
            res = subprocess.run(
                [git_bin, *args],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                timeout=10
            )
            return res.returncode, (res.stdout or res.stderr).strip()
        except Exception as e:
            return 1, str(e)

    def _init_git_repo(self, repo_dir: Path, commit_msg: str = "Initial commit by Squirrel"):
        """Initialize directory as a Git repository and commit all files."""
        if not (repo_dir / ".git").exists():
            self._run_git(repo_dir, "init", "-b", "main")
            self._run_git(repo_dir, "config", "user.name", "Squirrel the Robot Squirrel")
            self._run_git(repo_dir, "config", "user.email", "squirrel@lively.local")
        
        self._run_git(repo_dir, "add", "-A")
        self._run_git(repo_dir, "commit", "-m", commit_msg)

    def _ensure_starter_projects(self):
        """Seed starter GitHub repository if projects directory is empty."""
        existing = [p for p in self.projects_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
        
        # Also check for flat files and migrate them into repos if needed
        flat_files = [p for p in self.projects_dir.iterdir() if p.is_file() and not p.name.startswith(".")]
        for ff in flat_files:
            repo_name = ff.stem.replace("_", "-")
            target_repo = self.projects_dir / repo_name
            if not target_repo.exists():
                target_repo.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ff, target_repo / ff.name)
                (target_repo / "README.md").write_text(
                    f"# {repo_name}\n\nAutomated project workspace for `{ff.name}` coded by Squirrel.\n",
                    encoding="utf-8"
                )
                self._init_git_repo(target_repo, f"Migrate {ff.name} to GitHub project repository")

        if not existing and not flat_files:
            # Create starter repo: acorn-radar
            starter_repo = self.projects_dir / "acorn-radar"
            starter_repo.mkdir(parents=True, exist_ok=True)

            readme = """# Acorn Radar System 📡🌰
An autonomous sensor sweep program coded by **Squirrel the Robot Squirrel**.

## Overview
Scans the local coordinate grid on the Raspberry Pi for electromagnetic and electronic nut beacons.

## Usage
```bash
python3 main.py
```
"""
            (starter_repo / "README.md").write_text(readme, encoding="utf-8")

            main_py = '''#!/usr/bin/env python3
"""
acorn-radar / main.py - Coded by Squirrel
Scans the coordinate matrix for resonance spikes and cyber-nut signals.
"""

import math
import random
import sys

def sweep_matrix(radius=120):
    print(f"[RADAR] Sweeping {radius}m perimeter around Squirrel chassis...")
    pings = random.randint(2, 5)
    print(f"[RADAR] Detected {pings} energetic beacon frequencies!")
    beacons = []
    for i in range(pings):
        angle = random.uniform(0, 360)
        dist = random.uniform(15, radius)
        x = round(dist * math.cos(math.radians(angle)), 1)
        y = round(dist * math.sin(math.radians(angle)), 1)
        beacons.append((x, y))
        print(f" -> Beacon #{i+1}: relative coord ({x}, {y}) [Signal Strength: 98%]")
    return beacons

if __name__ == "__main__":
    sweep_matrix()
'''
            (starter_repo / "main.py").write_text(main_py.strip(), encoding="utf-8")
            (starter_repo / "requirements.txt").write_text("# Standard library only\n", encoding="utf-8")
            self._init_git_repo(starter_repo, "feat: Initial commit for Acorn Radar project")

    def reset(self):
        """Wipe all projects and restore the starter repository."""
        if self.projects_dir.exists():
            for item in self.projects_dir.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                except Exception:
                    pass
        self._ensure_starter_projects()

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all GitHub project repositories in the workspace."""
        repos = []
        for p in sorted(self.projects_dir.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                # Collect files
                files = []
                for f in p.rglob("*"):
                    if f.is_file() and ".git" not in f.parts:
                        files.append(str(f.relative_to(p)).replace("\\", "/"))

                # Git commit info
                code, commit_count_str = self._run_git(p, "rev-list", "--count", "HEAD")
                commit_count = int(commit_count_str) if code == 0 and commit_count_str.isdigit() else 1
                
                code, last_commit = self._run_git(p, "log", "-1", "--pretty=%B")
                last_commit_msg = last_commit.splitlines()[0] if code == 0 and last_commit else "Initial commit"

                # Read README or description
                desc = ""
                readme_text = ""
                readme_file = p / "README.md"
                if readme_file.exists():
                    try:
                        readme_text = readme_file.read_text(encoding="utf-8")
                        lines = [line.strip() for line in readme_text.splitlines() if line.strip() and not line.startswith("#")]
                        if lines:
                            desc = lines[0][:150]
                    except Exception:
                        pass
                
                if not desc:
                    desc = f"GitHub project repository by Squirrel ({len(files)} files)"

                # Timestamps
                mtime = p.stat().st_mtime
                ctime = p.stat().st_ctime

                repos.append({
                    "name": p.name,
                    "description": desc,
                    "is_git": (p / ".git").exists(),
                    "files": sorted(files),
                    "file_count": len(files),
                    "commit_count": commit_count,
                    "last_commit_msg": last_commit_msg,
                    "readme": readme_text,
                    "created_at": datetime.fromtimestamp(ctime, tz=timezone.utc).isoformat(),
                    "updated_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                })
        return repos

    def get_project(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get full details of a project repository."""
        clean_name = Path(repo_name).name
        repo_dir = self.projects_dir / clean_name
        if not repo_dir.exists() or not repo_dir.is_dir():
            return None

        files = []
        for f in repo_dir.rglob("*"):
            if f.is_file() and ".git" not in f.parts:
                files.append(str(f.relative_to(repo_dir)).replace("\\", "/"))

        # Git commit history (last 10 commits)
        code, log_out = self._run_git(repo_dir, "log", "-n", "10", "--pretty=format:%h|%an|%ar|%s")
        commits = []
        if code == 0 and log_out:
            for line in log_out.splitlines():
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    })

        readme_text = ""
        readme_path = repo_dir / "README.md"
        if readme_path.exists():
            try:
                readme_text = readme_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Primary entrypoint code preview
        primary_file = "main.py" if (repo_dir / "main.py").exists() else (files[0] if files else "")
        primary_code = ""
        if primary_file and (repo_dir / primary_file).exists():
            try:
                primary_code = (repo_dir / primary_file).read_text(encoding="utf-8")
            except Exception:
                pass

        return {
            "name": clean_name,
            "path": str(repo_dir),
            "is_git": (repo_dir / ".git").exists(),
            "files": sorted(files),
            "commits": commits,
            "readme": readme_text,
            "primary_file": primary_file,
            "primary_code": primary_code,
            "created_at": datetime.fromtimestamp(repo_dir.stat().st_ctime, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(repo_dir.stat().st_mtime, tz=timezone.utc).isoformat()
        }

    def get_file(self, repo_name: str, relative_path: str) -> Optional[str]:
        """Read content of a file within a project repo."""
        repo_dir = self.projects_dir / Path(repo_name).name
        file_path = repo_dir / relative_path
        if file_path.exists() and file_path.is_file() and ".git" not in file_path.parts:
            try:
                return file_path.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def create_project(self, repo_name: str, description: str = "", starter_files: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a new GitHub project repository."""
        clean_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "-", repo_name).strip("-").lower()
        if not clean_name:
            clean_name = "squirrel-project"
        
        repo_dir = self.projects_dir / clean_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        # Write README
        readme_content = f"# {clean_name}\n\n{description or 'A software project created by Squirrel the Robot Squirrel.'}\n\n"
        readme_content += "## Coded By\nSquirrel 🐿️⚡\n"
        (repo_dir / "README.md").write_text(readme_content, encoding="utf-8")

        # Write any additional starter files
        if starter_files:
            for rel_path, code in starter_files.items():
                target_f = repo_dir / rel_path
                target_f.parent.mkdir(parents=True, exist_ok=True)
                target_f.write_text(code.strip(), encoding="utf-8")
        elif not (repo_dir / "main.py").exists():
            (repo_dir / "main.py").write_text(
                f'#!/usr/bin/env python3\n"""\n{clean_name} - Main entrypoint.\n"""\n\ndef main():\n    print("Running {clean_name}!")\n\nif __name__ == "__main__":\n    main()\n',
                encoding="utf-8"
            )

        self._init_git_repo(repo_dir, f"feat: Initialize {clean_name} project")
        return self.get_project(clean_name)

    def save_file(self, repo_name: str, relative_path: str, content: str, commit_msg: str = "") -> Dict[str, Any]:
        """Write or update a file in a repository and commit to Git."""
        clean_name = Path(repo_name).name
        repo_dir = self.projects_dir / clean_name
        if not repo_dir.exists():
            self.create_project(clean_name)

        target_file = (repo_dir / relative_path).resolve()
        # Prevent path traversal outside repository
        if not str(target_file).startswith(str(repo_dir.resolve())):
            raise ValueError("Invalid file path: outside repository boundary.")

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content.strip(), encoding="utf-8")

        # Commit changes to Git
        msg = commit_msg or f"update: Edit {relative_path}"
        self._run_git(repo_dir, "add", str(target_file))
        self._run_git(repo_dir, "commit", "-m", msg)

        return {"success": True, "repo": clean_name, "file": relative_path}

    def execute_project(
        self,
        repo_name: str,
        entrypoint: str = "main.py",
        args: Optional[List[str]] = None,
        timeout_sec: int = 15
    ) -> ProjectExecutionResult:
        """
        Execute an entrypoint script within a project repository.
        Enforces AGYC Safety Checker before launching process.
        """
        clean_name = Path(repo_name).name
        repo_dir = self.projects_dir / clean_name

        # If repo_name is actually a flat file, handle gracefully
        if not repo_dir.is_dir() and (self.projects_dir / clean_name).is_file():
            # Migrate or run flat file
            target_file = self.projects_dir / clean_name
            cwd_path = self.projects_dir
        else:
            target_file = repo_dir / entrypoint
            cwd_path = repo_dir

        if not target_file.exists():
            return ProjectExecutionResult(
                success=False,
                error=f"Entrypoint '{entrypoint}' not found in project '{clean_name}'."
            )

        # 1. READ CONTENT FOR SAFETY INSPECTION
        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            return ProjectExecutionResult(success=False, error=f"Could not read script: {e}")

        # 2. RUN AGYC SAFETY CHECKER
        verdict = check_safety(content, target_name=f"{clean_name}/{entrypoint}")
        if not verdict.safe:
            return ProjectExecutionResult(
                success=False,
                blocked=True,
                error=f"BLOCKED BY SAFETY CHECKER: {verdict.reason}",
                safety_verdict=verdict.model_dump()
            )

        # 3. EXECUTE SCRIPT
        cmd = [sys.executable, str(target_file)]
        if target_file.suffix in (".sh", ".bash"):
            cmd = ["bash", str(target_file)]
        
        if args:
            cmd.extend(args)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(cwd_path),
                env={**os.environ, "PYTHONPATH": str(cwd_path)}
            )
            return ProjectExecutionResult(
                success=res.returncode == 0,
                blocked=False,
                returncode=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                safety_verdict=verdict.model_dump()
            )
        except subprocess.TimeoutExpired:
            return ProjectExecutionResult(
                success=False,
                blocked=False,
                returncode=-1,
                error=f"Execution timed out after {timeout_sec} seconds.",
                safety_verdict=verdict.model_dump()
            )
        except Exception as e:
            return ProjectExecutionResult(
                success=False,
                blocked=False,
                error=f"Execution failed: {e}",
                safety_verdict=verdict.model_dump()
            )

# Global singleton
projects = ProjectManager()

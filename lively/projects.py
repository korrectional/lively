"""
Squirrel GitHub Project and Software Repository Manager.
Manages multi-file Git repositories, code projects, and safe execution with AGYC safety checks.
"""

import os
import sys
import re
import json
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
        """Wipe all projects completely."""
        def _handle_remove_readonly(func, path, exc):
            try:
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass

        if self.projects_dir.exists():
            for item in self.projects_dir.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item, onerror=_handle_remove_readonly)
                    else:
                        item.unlink()
                except Exception:
                    pass

    @property
    def _runs_history_path(self) -> Path:
        return self.projects_dir / ".runs_history.json"

    def _record_run(self, record: Dict[str, Any]):
        """Persist execution record to global project run history and repo local state."""
        try:
            repo_name = record.get("repo", "")
            if repo_name:
                repo_dir = self.projects_dir / repo_name
                if repo_dir.exists() and repo_dir.is_dir():
                    (repo_dir / ".last_run.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

            history = []
            if self._runs_history_path.exists():
                try:
                    history = json.loads(self._runs_history_path.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            history.append(record)
            # Keep up to 50 most recent runs
            history = history[-50:]
            self._runs_history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_recent_runs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent program execution logs and outputs, latest first."""
        if not self._runs_history_path.exists():
            return []
        try:
            history = json.loads(self._runs_history_path.read_text(encoding="utf-8"))
            if isinstance(history, list):
                return list(reversed(history))[:limit]
        except Exception:
            pass
        return []

    def get_last_run(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get the most recent run details and output for a specific project."""
        clean_name = Path(repo_name).name
        repo_dir = self.projects_dir / clean_name
        last_run_file = repo_dir / ".last_run.json"
        if last_run_file.exists():
            try:
                return json.loads(last_run_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        # Fallback to searching history
        for r in self.get_recent_runs(limit=50):
            if r.get("repo") == clean_name:
                return r
        return None

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

                # Remote status
                code, remotes = self._run_git(p, "remote", "-v")
                pushed_to_github = (code == 0 and "origin" in remotes)

                repos.append({
                    "name": p.name,
                    "description": desc,
                    "is_git": (p / ".git").exists(),
                    "pushed_to_github": pushed_to_github,
                    "files": sorted(files),
                    "file_count": len(files),
                    "commit_count": commit_count,
                    "last_commit_msg": last_commit_msg,
                    "readme": readme_text,
                    "last_run": self.get_last_run(p.name),
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

        # Check remote origin
        code, remotes = self._run_git(repo_dir, "remote", "-v")
        pushed_to_github = (code == 0 and "origin" in remotes)

        return {
            "name": clean_name,
            "path": str(repo_dir),
            "is_git": (repo_dir / ".git").exists(),
            "pushed_to_github": pushed_to_github,
            "files": sorted(files),
            "commits": commits,
            "readme": readme_text,
            "primary_file": primary_file,
            "primary_code": primary_code,
            "last_run": self.get_last_run(clean_name),
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
            res = ProjectExecutionResult(
                success=False,
                error=f"Entrypoint '{entrypoint}' not found in project '{clean_name}'."
            )
            self._record_run({
                "repo": clean_name,
                "entrypoint": entrypoint,
                "timestamp": current_utc_iso(),
                "success": False,
                "blocked": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "",
                "error": res.error,
                "safety_verdict": None
            })
            return res

        # 1. READ CONTENT FOR SAFETY INSPECTION
        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            res = ProjectExecutionResult(success=False, error=f"Could not read script: {e}")
            self._record_run({
                "repo": clean_name,
                "entrypoint": entrypoint,
                "timestamp": current_utc_iso(),
                "success": False,
                "blocked": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "",
                "error": str(e),
                "safety_verdict": None
            })
            return res

        # 2. RUN AGYC SAFETY CHECKER
        verdict = check_safety(content, target_name=f"{clean_name}/{entrypoint}")
        if not verdict.safe:
            res = ProjectExecutionResult(
                success=False,
                blocked=True,
                error=f"BLOCKED BY SAFETY CHECKER: {verdict.reason}",
                safety_verdict=verdict.model_dump()
            )
            self._record_run({
                "repo": clean_name,
                "entrypoint": entrypoint,
                "timestamp": current_utc_iso(),
                "success": False,
                "blocked": True,
                "returncode": -1,
                "stdout": "",
                "stderr": "",
                "error": res.error,
                "safety_verdict": verdict.model_dump()
            })
            return res

        # 3. EXECUTE SCRIPT
        cmd = [sys.executable, str(target_file)]
        if target_file.suffix in (".sh", ".bash"):
            cmd = ["bash", str(target_file)]
        
        if args:
            cmd.extend(args)

        try:
            res_proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=str(cwd_path),
                env={**os.environ, "PYTHONPATH": str(cwd_path)}
            )
            res = ProjectExecutionResult(
                success=res_proc.returncode == 0,
                blocked=False,
                returncode=res_proc.returncode,
                stdout=res_proc.stdout,
                stderr=res_proc.stderr,
                safety_verdict=verdict.model_dump()
            )
        except subprocess.TimeoutExpired:
            res = ProjectExecutionResult(
                success=False,
                blocked=False,
                returncode=-1,
                error=f"Execution timed out after {timeout_sec} seconds.",
                safety_verdict=verdict.model_dump()
            )
        except Exception as e:
            res = ProjectExecutionResult(
                success=False,
                blocked=False,
                error=f"Execution failed: {e}",
                safety_verdict=verdict.model_dump()
            )

        self._record_run({
            "repo": clean_name,
            "entrypoint": entrypoint,
            "timestamp": current_utc_iso(),
            "success": res.success,
            "blocked": res.blocked,
            "returncode": res.returncode,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "error": res.error,
            "safety_verdict": res.safety_verdict
        })
        return res

    def push_to_github(self, repo_name: str) -> Dict[str, Any]:
        """
        Push local repository to remote GitHub account via gh CLI if authenticated.
        """
        clean_name = Path(repo_name).name
        repo_dir = self.projects_dir / clean_name
        if not repo_dir.exists():
            return {"success": False, "error": f"Repository '{clean_name}' not found."}

        gh_bin = shutil.which("gh")
        if not gh_bin:
            return {"success": False, "error": "GitHub CLI ('gh') not found on system."}

        # Check if already has a remote
        code, remotes = self._run_git(repo_dir, "remote", "-v")
        if code == 0 and "origin" in remotes:
            code, out = self._run_git(repo_dir, "push", "-u", "origin", "main")
            return {"success": code == 0, "output": out}

        try:
            res = subprocess.run(
                [gh_bin, "repo", "create", clean_name, "--public", "--source=.", "--push"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": res.returncode == 0,
                "output": (res.stdout or res.stderr).strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global singleton
projects = ProjectManager()

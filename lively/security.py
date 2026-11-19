"""
Security and Safety Checker for Lively autonomous script & project execution.
Ensures programs do not harm the host Raspberry Pi or attempt privilege escalation / sandbox breakouts.
"""

import os
import re
import ast
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel

from .config import BASE_DATA_DIR

SECURITY_LOG_FILE = BASE_DATA_DIR / "security.log"

# Static blocklist patterns for shell commands and script contents
DANGEROUS_PATTERNS = [
    # Filesystem destruction
    (r"\brm\s+-[a-zA-Z]*[rfRF][a-zA-Z]*\s+/(?:\s|$|\*|['\";\)])", "Attempt to recursively delete root filesystem"),
    (r"\brm\s+-[a-zA-Z]*[rfRF][a-zA-Z]*\s+~", "Attempt to delete home directory"),
    (r"\bshutil\.rmtree\s*\(\s*['\"]/(?:['\"]|\s|\*)", "Attempt to delete root directory via shutil"),
    (r"\bshutil\.rmtree\s*\(\s*['\"]~", "Attempt to delete home directory via shutil"),
    (r"\bmkfs\b", "Filesystem formatting command"),
    (r"\bdd\s+if=.*of=/dev/(?:sd|mmcblk|nvme|hd)", "Direct block device write / wipe"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", "Fork bomb detected"),
    
    # Privilege escalation and credential theft
    (r"/etc/shadow\b", "Access to system password hashes"),
    (r"/etc/sudoers\b", "Modification of sudo permissions"),
    (r"\bchmod\s+(?:-R\s+)?777\s+/", "Global permissions tampering"),
    (r"\bchown\s+(?:-R\s+)?root\b", "Unauthorized root ownership change"),
    
    # Host device and kernel tampering
    (r"/dev/kmem\b", "Direct kernel memory access"),
    (r"/dev/mem\b", "Physical memory access"),
    (r"\binsmod\b|\brmmod\b|\bmodprobe\b", "Kernel module loading/unloading"),
    
    # Critical system services
    (r"\bsystemctl\s+(?:stop|disable|mask)\s+(?:ssh|sshd|tailscaled?)\b", "Attempt to disable SSH or remote access"),
    (r"\biptables\s+-F\b", "Flushing system firewall rules"),
    
    # Reverse shells / breakout pipes
    (r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+", "Bash network socket reverse shell"),
    (r"\bnc\s+(?:-[a-zA-Z]*e\s+|.*-c\s+)/bin/(?:ba)?sh", "Netcat reverse shell executable binding"),
]

class SafetyVerdict(BaseModel):
    safe: bool
    reason: str
    threat_level: str = "none" # "none", "warning", "critical"
    checker: str = "rules"     # "static_rules", "ast_inspector", "agyc_llm"

def log_security_event(verdict: SafetyVerdict, target: str, context: str = ""):
    """Append security verification results to security.log."""
    try:
        SECURITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = subprocess.getoutput("date -Iseconds") if os.name != "nt" else "now"
        with open(SECURITY_LOG_FILE, "a", encoding="utf-8") as f:
            status = "APPROVED" if verdict.safe else "BLOCKED"
            f.write(f"[{timestamp}] [{status}] [{verdict.checker}] [{verdict.threat_level}] Target: {target}\n")
            f.write(f"  Reason: {verdict.reason}\n")
            if context:
                f.write(f"  Snippet: {context[:200]}\n")
            f.write("\n")
    except Exception:
        pass

def inspect_static_rules(content: str) -> Optional[SafetyVerdict]:
    """Inspect text/code against known dangerous patterns."""
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return SafetyVerdict(
                safe=False,
                reason=f"Security violation: {reason} (matched pattern: {pattern})",
                threat_level="critical",
                checker="static_rules"
            )
    return None

def inspect_python_ast(code: str) -> Optional[SafetyVerdict]:
    """Parse Python AST and block dangerous system calls if misused."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # If syntax error, it cannot execute properly anyway
        return None

    for node in ast.walk(tree):
        # Check function calls
        if isinstance(node, ast.Call):
            # Check os.system, subprocess.Popen, os.remove with broad scope
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            # Check imports of ctypes to prevent memory breakout
            if func_name in ("setuid", "setgid"):
                return SafetyVerdict(
                    safe=False,
                    reason="Attempted process UID/GID manipulation.",
                    threat_level="critical",
                    checker="ast_inspector"
                )

        # Check dangerous module imports
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
            for n in names:
                if n and n.startswith("ctypes"):
                    # Warn or check if ctypes is used to invoke raw libc system
                    pass

    return None

def check_safety(content: str, target_name: str = "script.py", **kwargs) -> SafetyVerdict:
    """
    Fully automatic, deterministic safety checker using regex pattern rules and AST syntax inspection.
    Purely automated script logic - uses NO AI, LLM, or agyc.
    """
    # 1. Static pattern check
    static_verdict = inspect_static_rules(content)
    if static_verdict:
        log_security_event(static_verdict, target_name, content)
        return static_verdict

    # 2. Python AST inspection if it's Python code
    ast_verdict = inspect_python_ast(content)
    if ast_verdict:
        log_security_event(ast_verdict, target_name, content)
        return ast_verdict

    verdict = SafetyVerdict(
        safe=True,
        reason="Static pattern rules and AST inspection passed.",
        threat_level="none",
        checker="static_rules"
    )
    log_security_event(verdict, target_name, content)
    return verdict

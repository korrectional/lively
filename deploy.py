#!/usr/bin/env python3
"""
Deploy script for Lively to Raspberry Pi (dietpi via Tailscale).
Syncs code, installs dependencies in virtualenv, sets up agyc, and configures systemd.
"""

import sys
import subprocess
import tarfile
import io
from pathlib import Path

REMOTE_HOST = "dietpi@dietpi"
REMOTE_DIR = "/home/dietpi/lively"

def run_ssh(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run command on remote host via ssh."""
    full_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", REMOTE_HOST, cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"[ERROR] SSH command failed: {cmd}\nOutput: {res.stdout}\nError: {res.stderr}")
        sys.exit(1)
    return res

def deploy():
    print("🚀 Deploying Lively to Raspberry Pi (dietpi)...")

    # 1. Test connectivity
    print(" -> Checking SSH connection to dietpi...")
    res = run_ssh("echo 'SSH connection verified.'")
    print(f"    {res.stdout.strip()}")

    # 2. Prepare remote directory
    print(" -> Ensuring remote directories exist...")
    run_ssh(f"mkdir -p {REMOTE_DIR} ~/.local/bin ~/.lively/memories ~/.lively/projects")

    # 3. Create tarball of repository and upload
    print(" -> Packaging and syncing code to Pi...")
    repo_root = Path(__file__).parent.resolve()
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
        for item in ["lively", "systemd", "requirements.txt", "setup.py"]:
            path = repo_root / item
            if path.exists():
                tar.add(str(path), arcname=item)

    tar_bytes = tar_buf.getvalue()
    tar_cmd = ["ssh", "-o", "BatchMode=yes", REMOTE_HOST, f"tar -xzf - -C {REMOTE_DIR}"]
    proc = subprocess.run(tar_cmd, input=tar_bytes, capture_output=True)
    if proc.returncode != 0:
        print(f"[ERROR] Sync failed: {proc.stderr.decode()}")
        sys.exit(1)
    print("    Code synchronized successfully.")

    # 4. Copy agyc wrapper to Pi
    print(" -> Checking agyc wrapper on Pi...")
    agyc_local = Path.home() / "AppData" / "Local" / "agy" / "bin" / "agyc.py"
    if agyc_local.exists():
        agyc_content = agyc_local.read_text(encoding="utf-8")
        # Write to ~/.local/bin/agyc
        upload_agyc_cmd = ["ssh", "-o", "BatchMode=yes", REMOTE_HOST, "cat > ~/.local/bin/agyc && chmod +x ~/.local/bin/agyc"]
        subprocess.run(upload_agyc_cmd, input=agyc_content.encode("utf-8"), check=True)
        print("    agyc wrapper installed to ~/.local/bin/agyc")

    # 5. Check if agy is installed on Pi, or offer install command
    print(" -> Checking Google Antigravity CLI (agy) on Pi...")
    check_agy = run_ssh("which agy || test -f ~/.local/bin/agy", check=False)
    if check_agy.returncode != 0:
        print("    agy CLI not detected in PATH. Attempting automated installation via install.sh...")
        install_res = run_ssh("curl -fsSL https://antigravity.google/cli/install.sh | bash", check=False)
        print(f"    Install script output: {install_res.stdout[:200]}")
    else:
        print("    agy CLI is installed.")

    # 6. Setup Python virtualenv and install dependencies
    print(" -> Setting up Python virtual environment and dependencies on Pi...")
    setup_env_cmd = (
        f"cd {REMOTE_DIR} && "
        f"test -d .venv || python3 -m venv .venv && "
        f".venv/bin/pip install --upgrade pip && "
        f".venv/bin/pip install -r requirements.txt -e ."
    )
    run_ssh(setup_env_cmd)
    print("    Virtual environment and dependencies installed.")

    # 7. Configure and enable systemd services
    print(" -> Installing and starting systemd services...")
    systemd_setup_cmd = (
        f"sudo cp {REMOTE_DIR}/systemd/lively-world.service /etc/systemd/system/ && "
        f"sudo cp {REMOTE_DIR}/systemd/lively-squirrel.service /etc/systemd/system/ && "
        f"sudo cp {REMOTE_DIR}/systemd/lively-squirrel.timer /etc/systemd/system/ && "
        f"sudo systemctl daemon-reload && "
        f"sudo systemctl restart lively-world.service && "
        f"sudo systemctl enable lively-world.service && "
        f"sudo systemctl enable --now lively-squirrel.timer"
    )
    run_ssh(systemd_setup_cmd)
    print("    Systemd services enabled and started.")

    # 8. Verify service status and port 8880
    print(" -> Verifying services...")
    status_res = run_ssh("systemctl is-active lively-world.service; systemctl is-active lively-squirrel.timer")
    print(f"    Services status:\n{status_res.stdout.strip()}")

    timer_res = run_ssh("systemctl list-timers lively-squirrel.timer --no-pager")
    print(f"    Timer schedule:\n{timer_res.stdout.strip()}")

    print("\n" + "=" * 60)
    print("🎉 LIVELY SUCCESSFULLY DEPLOYED TO RASPBERRY PI!")
    print("=" * 60)
    print("🌐 Open the 2D World across Tailscale at:")
    print("   👉 http://dietpi:8880")
    print("   👉 http://100.91.27.71:8880")
    print("=" * 60)

if __name__ == "__main__":
    deploy()

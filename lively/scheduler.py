"""
Lively Wake Cycle Scheduler.
Manages systemd timer frequency and status.
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from lively.config import BASE_DATA_DIR, SCHEDULE_CONFIG_FILE, ensure_directories

SCHEDULE_PRESETS = {
    "paused": [],
    "daily": ["*-*-* 12:00:00"],
    "twice_daily": ["*-*-* 09:00:00", "*-*-* 21:00:00"],
    "four_daily": ["*-*-* 00,06,12,18:00:00"],
    "hourly": ["*-*-* *:00:00"],
}

TIMER_UNIT = "lively-squirrel.timer"
TIMER_PATH = Path("/etc/systemd/system/lively-squirrel.timer")

class SchedulerManager:
    """Manages the wake cycle schedule and systemd timer on Linux."""

    def __init__(self, config_file: Path = SCHEDULE_CONFIG_FILE):
        self.config_file = Path(config_file)
        ensure_directories()
        self._ensure_config()

    def _ensure_config(self):
        if not self.config_file.exists():
            default_data = {
                "frequency": "paused",
                "custom_on_calendar": "",
                "enabled": False,
                "active": False,
                "next_run": "Paused / None",
                "last_run": None,
                "message": "Timer is currently paused."
            }
            self.config_file.write_text(json.dumps(default_data, indent=2), encoding="utf-8")

    def get_status(self) -> Dict[str, Any]:
        """Query systemd timer or return stored configuration."""
        data = {
            "frequency": "paused",
            "custom_on_calendar": "",
            "enabled": False,
            "active": False,
            "next_run": "Paused / None",
            "last_run": None,
            "message": "Manual wake only"
        }
        if self.config_file.exists():
            try:
                loaded = json.loads(self.config_file.read_text(encoding="utf-8"))
                data.update(loaded)
            except Exception:
                pass

        systemctl = shutil.which("systemctl")
        if systemctl:
            try:
                # Check active status
                act_res = subprocess.run([systemctl, "is-active", TIMER_UNIT], capture_output=True, text=True)
                is_active = (act_res.stdout.strip() == "active")
                data["active"] = is_active

                # Check enabled status
                en_res = subprocess.run([systemctl, "is-enabled", TIMER_UNIT], capture_output=True, text=True)
                is_enabled = (en_res.stdout.strip() == "enabled")
                data["enabled"] = is_enabled

                if not is_active:
                    data["next_run"] = "Paused / None"
                else:
                    lt_res = subprocess.run([systemctl, "list-timers", TIMER_UNIT, "--no-pager"], capture_output=True, text=True)
                    lines = [line.strip() for line in lt_res.stdout.splitlines() if TIMER_UNIT in line]
                    if lines:
                        parts = lines[0].split()
                        if len(parts) >= 3 and parts[0] != "n/a":
                            data["next_run"] = f"{parts[0]} {parts[1]} {parts[2]}"
            except Exception:
                pass

        return data

    def set_schedule(self, frequency: str, custom_on_calendar: Optional[str] = None) -> Dict[str, Any]:
        """Configure systemd timer with desired frequency."""
        freq = frequency.lower().strip()
        if freq not in SCHEDULE_PRESETS and freq != "custom":
            freq = "paused"

        systemctl = shutil.which("systemctl")
        sudo = shutil.which("sudo") or ""

        if freq == "paused":
            if systemctl:
                try:
                    cmd_prefix = [sudo] if sudo else []
                    subprocess.run(cmd_prefix + [systemctl, "stop", TIMER_UNIT], capture_output=True)
                    subprocess.run(cmd_prefix + [systemctl, "disable", TIMER_UNIT], capture_output=True)
                except Exception:
                    pass
            status = {
                "frequency": "paused",
                "custom_on_calendar": custom_on_calendar or "",
                "enabled": False,
                "active": False,
                "next_run": "Paused / None",
                "last_run": self.get_status().get("last_run"),
                "message": "Lively wake cycle timer is paused. Squirrel will only wake when manually triggered."
            }
        else:
            calendars = SCHEDULE_PRESETS.get(freq, [])
            if freq == "custom" and custom_on_calendar:
                calendars = [c.strip() for c in custom_on_calendar.split(";") if c.strip()]
                if not calendars:
                    calendars = ["*-*-* 12:00:00"]

            cal_lines = "\n".join([f"OnCalendar={c}" for c in calendars])
            timer_content = f"""[Unit]
Description=Lively Robot Squirrel Wake Cycle Timer ({freq})

[Timer]
{cal_lines}
Persistent=true

[Install]
WantedBy=timers.target
"""
            tmp_timer = BASE_DATA_DIR / "lively-squirrel.timer.tmp"
            tmp_timer.write_text(timer_content, encoding="utf-8")

            if systemctl:
                try:
                    cmd_prefix = [sudo] if sudo else []
                    subprocess.run(cmd_prefix + ["cp", str(tmp_timer), str(TIMER_PATH)], capture_output=True)
                    subprocess.run(cmd_prefix + [systemctl, "daemon-reload"], capture_output=True)
                    subprocess.run(cmd_prefix + [systemctl, "enable", TIMER_UNIT], capture_output=True)
                    subprocess.run(cmd_prefix + [systemctl, "restart", TIMER_UNIT], capture_output=True)
                except Exception as e:
                    print(f"Error configuring systemd timer: {e}")

            status = {
                "frequency": freq,
                "custom_on_calendar": custom_on_calendar or "",
                "enabled": True,
                "active": True,
                "next_run": "Scheduled",
                "last_run": self.get_status().get("last_run"),
                "message": f"Schedule set to '{freq}'. Next wake cycle is active."
            }

        self.config_file.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return self.get_status()

# Global scheduler instance
scheduler = SchedulerManager()

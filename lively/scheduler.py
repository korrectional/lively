"""
Lively Wake Cycle Scheduler.
Manages systemd timer frequency and status.
"""

import os
import re
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
SERVICE_UNIT = "lively-squirrel.service"
TIMER_PATH = Path("/etc/systemd/system/lively-squirrel.timer")

def _parse_systemd_show(output: str) -> Dict[str, str]:
    """Parse key=value properties from systemctl show."""
    props = {}
    for line in output.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k.strip()] = v.strip()
    return props

def calculate_next_run(calendar_spec: str) -> Optional[str]:
    """Calculate the next elapse timestamp using systemd-analyze calendar."""
    sa = shutil.which("systemd-analyze")
    if not sa or not calendar_spec:
        return None
    try:
        res = subprocess.run([sa, "calendar", calendar_spec], capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            if "Next elapse:" in line:
                return line.split("Next elapse:", 1)[1].strip()
    except Exception:
        pass
    return None

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
                "executing": False,
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
            "executing": False,
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
                # Query timer properties
                res_timer = subprocess.run([systemctl, "show", TIMER_UNIT, "--no-pager"], capture_output=True, text=True, timeout=5)
                timer_props = _parse_systemd_show(res_timer.stdout)

                is_active = (timer_props.get("ActiveState") == "active")
                is_enabled = (timer_props.get("UnitFileState") == "enabled")
                data["active"] = is_active
                data["enabled"] = is_enabled

                # Query service execution status
                res_svc = subprocess.run([systemctl, "show", SERVICE_UNIT, "--no-pager", "-p", "ActiveState", "-p", "SubState"], capture_output=True, text=True, timeout=5)
                svc_props = _parse_systemd_show(res_svc.stdout)
                is_executing = svc_props.get("ActiveState") in ("active", "activating")
                data["executing"] = is_executing

                # Last run
                last_trigger = timer_props.get("LastTriggerUSec")
                if last_trigger and last_trigger != "n/a":
                    data["last_run"] = last_trigger

                if not is_active:
                    data["next_run"] = "Paused / None"
                    data["message"] = "Timer is paused. Manual wake only."
                else:
                    # Determine next run cleanly
                    next_run = timer_props.get("NextElapseUSecRealtime")
                    # If NextElapseUSecRealtime is empty or invalid, try TimersCalendar or systemd-analyze
                    if not next_run or next_run.startswith("-") or next_run == "n/a":
                        cal_text = timer_props.get("TimersCalendar", "")
                        match = re.search(r"next_elapse=([^;}\n]+)", cal_text)
                        if match:
                            candidate = match.group(1).strip()
                            if candidate and not candidate.startswith("-") and candidate != "n/a":
                                next_run = candidate

                    # If still unresolved, compute via systemd-analyze calendar
                    if not next_run or next_run.startswith("-") or next_run == "n/a":
                        freq = data.get("frequency", "four_daily")
                        calendars = SCHEDULE_PRESETS.get(freq, [])
                        if freq == "custom" and data.get("custom_on_calendar"):
                            calendars = [c.strip() for c in data["custom_on_calendar"].split(";") if c.strip()]
                        if calendars:
                            calc = calculate_next_run(calendars[0])
                            if calc:
                                next_run = calc

                    if next_run and not next_run.startswith("-") and next_run != "n/a":
                        data["next_run"] = next_run
                    else:
                        data["next_run"] = "Scheduled"

                    if is_executing:
                        data["message"] = "A wake cycle is currently running in the background."
                    else:
                        data["message"] = f"Timer active ({data.get('frequency', 'custom')}). Next run: {data['next_run']}."
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
                    subprocess.run(cmd_prefix + [systemctl, "stop", TIMER_UNIT], capture_output=True, timeout=10)
                    subprocess.run(cmd_prefix + [systemctl, "disable", TIMER_UNIT], capture_output=True, timeout=10)
                except Exception:
                    pass
            status = {
                "frequency": "paused",
                "custom_on_calendar": custom_on_calendar or "",
                "enabled": False,
                "active": False,
                "executing": False,
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
Persistent=false

[Install]
WantedBy=timers.target
"""
            tmp_timer = BASE_DATA_DIR / "lively-squirrel.timer.tmp"
            tmp_timer.write_text(timer_content, encoding="utf-8")

            if systemctl:
                try:
                    cmd_prefix = [sudo] if sudo else []
                    subprocess.run(cmd_prefix + ["cp", str(tmp_timer), str(TIMER_PATH)], capture_output=True, timeout=10)
                    subprocess.run(cmd_prefix + [systemctl, "daemon-reload"], capture_output=True, timeout=10)
                    subprocess.run(cmd_prefix + [systemctl, "enable", TIMER_UNIT], capture_output=True, timeout=10)
                    subprocess.run(cmd_prefix + [systemctl, "restart", TIMER_UNIT], capture_output=True, timeout=10)
                except Exception as e:
                    print(f"Error configuring systemd timer: {e}")

            status = {
                "frequency": freq,
                "custom_on_calendar": custom_on_calendar or "",
                "enabled": True,
                "active": True,
                "executing": False,
                "next_run": "Scheduled",
                "last_run": self.get_status().get("last_run"),
                "message": f"Schedule set to '{freq}'. Next wake cycle is active."
            }

        self.config_file.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return self.get_status()

# Global scheduler instance
scheduler = SchedulerManager()

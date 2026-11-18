"""
Spatial 2D World Manager for Lively.
Persists world objects and live entity positions.
"""

import json
import math
import uuid
import time
from typing import Dict, List, Optional
from threading import Lock

from lively.config import (
    WORLD_FILE,
    WORLD_MIN_X,
    WORLD_MAX_X,
    WORLD_MIN_Y,
    WORLD_MAX_Y,
    ensure_directories
)
from lively.models import WorldObject, SquirrelState, UserAvatar

class WorldManager:
    """Manages the 2D world coordinates, landmarks, and entity states."""

    def __init__(self, file_path=WORLD_FILE):
        self.file_path = file_path
        self._lock = Lock()
        self.squirrel = SquirrelState()
        self.objects: Dict[str, WorldObject] = {}
        self.active_users: Dict[str, UserAvatar] = {}
        self._last_loaded_mtime = 0.0
        self._load()

    def _load(self):
        """Load world from disk or initialize empty world."""
        ensure_directories()
        if self.file_path.exists():
            try:
                mtime = self.file_path.stat().st_mtime
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.squirrel = SquirrelState(**data.get("squirrel", {}))
                    self.objects = {
                        k: WorldObject(**v) for k, v in data.get("objects", {}).items()
                    }
                    self._last_loaded_mtime = mtime
                    return
            except Exception as e:
                print(f"[WorldManager] Error loading world file ({e}), initializing fresh world.")

        # Fresh plain 2D world
        self.squirrel = SquirrelState(
            x=0.0,
            y=0.0,
            heading=0.0,
            last_thought="Booted up in a vast open plain. Ready to explore."
        )
        self.objects = {}
        self._save()

    def _save(self):
        """Persist state to disk safely."""
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({
                "squirrel": self.squirrel.model_dump(),
                "objects": {k: v.model_dump() for k, v in self.objects.items()}
            }, f, indent=2)
        if self.file_path.exists():
            self._last_loaded_mtime = self.file_path.stat().st_mtime

    def _check_reload(self):
        """Reload from disk if file was updated by another process."""
        if self.file_path.exists():
            try:
                mtime = self.file_path.stat().st_mtime
                if mtime > self._last_loaded_mtime:
                    self._load()
            except Exception:
                pass

    def get_state(self) -> dict:
        """Return snapshot of the entire world."""
        with self._lock:
            self._check_reload()
            self._cleanup_inactive_users()
            return {
                "bounds": {
                    "min_x": WORLD_MIN_X,
                    "max_x": WORLD_MAX_X,
                    "min_y": WORLD_MIN_Y,
                    "max_y": WORLD_MAX_Y
                },
                "squirrel": self.squirrel.model_dump(),
                "objects": [obj.model_dump() for obj in self.objects.values()],
                "users": [user.model_dump() for user in self.active_users.values()]
            }

    def add_object(self, name: str, x: float, y: float, obj_type: str = "landmark",
                   description: str = "", created_by: str = "user", metadata: Optional[dict] = None) -> WorldObject:
        """Add a landmark or object to the map."""
        with self._lock:
            obj_id = f"obj_{uuid.uuid4().hex[:8]}"
            clamped_x = max(WORLD_MIN_X, min(WORLD_MAX_X, float(x)))
            clamped_y = max(WORLD_MIN_Y, min(WORLD_MAX_Y, float(y)))
            obj = WorldObject(
                id=obj_id,
                name=name,
                x=clamped_x,
                y=clamped_y,
                type=obj_type,
                description=description,
                created_by=created_by,
                metadata=metadata or {}
            )
            self.objects[obj_id] = obj
            self._save()
            return obj

    def remove_object(self, obj_id: str) -> bool:
        """Remove an object by id."""
        with self._lock:
            if obj_id in self.objects:
                del self.objects[obj_id]
                self._save()
                return True
            return False

    def get_object(self, obj_id: str) -> Optional[WorldObject]:
        """Fetch an object by id."""
        with self._lock:
            return self.objects.get(obj_id)

    def get_nearby_objects(self, x: float, y: float, max_dist: float = 500.0) -> List[dict]:
        """List objects within range with relative distance and angle."""
        with self._lock:
            results = []
            for obj in self.objects.values():
                dx = obj.x - x
                dy = obj.y - y
                dist = math.hypot(dx, dy)
                if dist <= max_dist:
                    angle_deg = math.degrees(math.atan2(dy, dx))
                    results.append({
                        "id": obj.id,
                        "name": obj.name,
                        "x": obj.x,
                        "y": obj.y,
                        "type": obj.type,
                        "description": obj.description,
                        "created_by": obj.created_by,
                        "distance": round(dist, 1),
                        "relative_bearing_deg": round(angle_deg, 1),
                        "metadata": obj.metadata
                    })
            results.sort(key=lambda item: item["distance"])
            return results

    def move_squirrel(self, target_x: float, target_y: float, thought: str = "", activity: str = "") -> SquirrelState:
        """Move the squirrel toward or to coordinates."""
        with self._lock:
            clamped_x = max(WORLD_MIN_X, min(WORLD_MAX_X, float(target_x)))
            clamped_y = max(WORLD_MIN_Y, min(WORLD_MAX_Y, float(target_y)))
            dx = clamped_x - self.squirrel.x
            dy = clamped_y - self.squirrel.y
            dist = math.hypot(dx, dy)

            if dist > 0.1:
                self.squirrel.heading = round(math.degrees(math.atan2(dy, dx)), 1)
                self.squirrel.total_distance_traveled = round(self.squirrel.total_distance_traveled + dist, 2)

            self.squirrel.x = round(clamped_x, 2)
            self.squirrel.y = round(clamped_y, 2)

            if thought:
                self.squirrel.last_thought = thought
            if activity:
                self.squirrel.current_activity = activity

            self._save()
            return self.squirrel

    def update_user_position(self, user_id: str, name: str, x: float, y: float) -> UserAvatar:
        """Update or register an avatar for a live connected user."""
        with self._lock:
            clamped_x = max(WORLD_MIN_X, min(WORLD_MAX_X, float(x)))
            clamped_y = max(WORLD_MIN_Y, min(WORLD_MAX_Y, float(y)))
            user = UserAvatar(
                id=user_id,
                name=name or f"User-{user_id[:4]}",
                x=clamped_x,
                y=clamped_y,
                last_active=time.time()
            )
            self.active_users[user_id] = user
            return user

    def remove_user(self, user_id: str):
        """Remove disconnected user."""
        with self._lock:
            self.active_users.pop(user_id, None)

    def _cleanup_inactive_users(self, timeout_sec: float = 30.0):
        """Prune users with no heartbeat."""
        now = time.time()
        stale_ids = [uid for uid, u in self.active_users.items() if now - u.last_active > timeout_sec]
        for uid in stale_ids:
            del self.active_users[uid]

# Global singleton instance
world = WorldManager()

"""
Spatial 2D World Manager for Lively.
Persists world objects and live entity positions.
"""

import json
import math
import uuid
import time
from typing import Dict, List, Optional, Tuple
from threading import RLock

from lively.config import (
    WORLD_FILE,
    WORLD_MIN_X,
    WORLD_MAX_X,
    WORLD_MIN_Y,
    WORLD_MAX_Y,
    MIN_OBJECT_DISTANCE,
    ensure_directories
)
from lively.models import WorldObject, SquirrelState, UserAvatar

class WorldManager:
    """Manages the 2D world coordinates, landmarks, and entity states."""

    def __init__(self, file_path=WORLD_FILE):
        self.file_path = file_path
        self._lock = RLock()
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
                    # Ensure TreeberryPine exists
                    self._ensure_treeberry_pine()
                    return
            except Exception as e:
                print(f"[WorldManager] Error loading world file ({e}), initializing fresh world.")

        # Initialize fresh world
        self.reset()

    def _ensure_treeberry_pine(self):
        """Ensure the ancestral TreeberryPine tree is present."""
        has_treeberry = any(o.name.lower() == "treeberrypine" for o in self.objects.values())
        if not has_treeberry:
            pine = WorldObject(
                id="obj_treeberry_pine",
                name="TreeberryPine",
                x=45.0,
                y=45.0,
                type="tree",
                icon="🌲",
                description="The sacred ancestral TreeberryPine tree — majestic, lush, and full of digital pinecones and perches.",
                created_by="nature"
            )
            self.objects[pine.id] = pine
            self._save()

    def reset(self):
        """Reset world to initial state: removes all physical objects and spawns TreeberryPine."""
        with self._lock:
            self.squirrel = SquirrelState(
                name="Squirrel",
                x=0.0,
                y=0.0,
                heading=0.0,
                battery=100,
                current_activity="Resting near TreeberryPine",
                last_thought="Awakening fresh in the meadow next to the TreeberryPine.",
                total_cycles=0,
                total_distance_traveled=0.0
            )
            self.objects = {}
            pine = WorldObject(
                id="obj_treeberry_pine",
                name="TreeberryPine",
                x=45.0,
                y=45.0,
                type="tree",
                icon="🌲",
                description="The sacred ancestral TreeberryPine tree — majestic, lush, and full of digital pinecones and perches.",
                created_by="nature"
            )
            self.objects[pine.id] = pine
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

    def get_closest_object(self, x: float, y: float, exclude_id: Optional[str] = None) -> Tuple[Optional[WorldObject], float]:
        """Return the closest object and distance to (x, y), or (None, inf)."""
        with self._lock:
            return self._get_closest_object_unlocked(x, y, exclude_id=exclude_id)

    def _get_closest_object_unlocked(self, x: float, y: float, exclude_id: Optional[str] = None) -> Tuple[Optional[WorldObject], float]:
        closest = None
        min_dist = float("inf")
        for obj in self.objects.values():
            if exclude_id and obj.id == exclude_id:
                continue
            dist = math.hypot(obj.x - x, obj.y - y)
            if dist < min_dist:
                min_dist = dist
                closest = obj
        return closest, min_dist

    def find_open_coordinates(self, target_x: float, target_y: float, min_clearance: float = MIN_OBJECT_DISTANCE) -> Tuple[float, float]:
        """
        Enforces physical spatial separation.
        If target_x, target_y is too close to an existing physical object (< min_clearance),
        searches in concentric rings for the nearest vacant coordinate.
        """
        with self._lock:
            return self._find_open_coordinates_unlocked(target_x, target_y, min_clearance=min_clearance)

    def _find_open_coordinates_unlocked(self, target_x: float, target_y: float, min_clearance: float = MIN_OBJECT_DISTANCE) -> Tuple[float, float]:
        tx = max(WORLD_MIN_X, min(WORLD_MAX_X, float(target_x)))
        ty = max(WORLD_MIN_Y, min(WORLD_MAX_Y, float(target_y)))

        def is_clear(cx, cy):
            for obj in self.objects.values():
                if math.hypot(obj.x - cx, obj.y - cy) < min_clearance:
                    return False
            return True

        if is_clear(tx, ty):
            return (round(tx, 1), round(ty, 1))

        # Search outward in concentric rings
        radii = [
            min_clearance,
            min_clearance * 1.5,
            min_clearance * 2.0,
            min_clearance * 2.5,
            min_clearance * 3.0,
            min_clearance * 4.0
        ]
        angles = [0, 30, 45, 60, 90, 120, 135, 150, 180, 210, 225, 240, 270, 300, 315, 330]

        for r in radii:
            for deg in angles:
                rad = math.radians(deg)
                cx = max(WORLD_MIN_X, min(WORLD_MAX_X, tx + r * math.cos(rad)))
                cy = max(WORLD_MIN_Y, min(WORLD_MAX_Y, ty + r * math.sin(rad)))
                if is_clear(cx, cy):
                    return (round(cx, 1), round(cy, 1))

        return (round(tx + min_clearance, 1), round(ty + min_clearance, 1))

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
                "min_object_distance": MIN_OBJECT_DISTANCE,
                "squirrel": self.squirrel.model_dump(),
                "objects": [obj.model_dump() for obj in self.objects.values()],
                "users": [user.model_dump() for user in self.active_users.values()]
            }

    def add_object(self, name: str, x: float, y: float, obj_type: str = "landmark",
                   icon: str = "", description: str = "", created_by: str = "user",
                   metadata: Optional[dict] = None, enforce_distance: bool = False,
                   min_distance: float = MIN_OBJECT_DISTANCE) -> WorldObject:
        """Add a landmark or object to the map with guaranteed physical separation."""
        with self._lock:
            if enforce_distance:
                closest, dist = self._get_closest_object_unlocked(x, y)
                if closest is not None and dist < min_distance:
                    raise ValueError(
                        f"Too close to '{closest.name}' ({dist:.1f}m away). "
                        f"Objects must be placed at least {min_distance:.0f}m apart."
                    )
                actual_x, actual_y = round(float(x), 1), round(float(y), 1)
            else:
                actual_x, actual_y = self._find_open_coordinates_unlocked(x, y, min_clearance=min_distance)

            obj_id = f"obj_{uuid.uuid4().hex[:8]}"
            obj = WorldObject(
                id=obj_id,
                name=name,
                x=actual_x,
                y=actual_y,
                type=obj_type,
                icon=icon or "",
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

    def update_user_position(self, user_id: str, name: str, x: float, y: float, avatar_type: str = "scout") -> UserAvatar:
        """Update or register an avatar for a live connected user."""
        with self._lock:
            clamped_x = max(WORLD_MIN_X, min(WORLD_MAX_X, float(x)))
            clamped_y = max(WORLD_MIN_Y, min(WORLD_MAX_Y, float(y)))
            user = UserAvatar(
                id=user_id,
                name=name or f"User-{user_id[:4]}",
                x=clamped_x,
                y=clamped_y,
                avatar_type=avatar_type or "scout",
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

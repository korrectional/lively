#!/usr/bin/env python3
"""
Reset script for Lively.
Removes all physical locations and memories, and ensures TreeberryPine is spawned.
"""

from lively.world import world
from lively.memory import memory
from lively.projects import projects

def reset():
    print("🧹 Executing Lively Reset...")
    world.reset()
    memory.reset()
    projects.reset()
    st = world.get_state()
    print("✅ Reset Complete!")
    print(f" -> Squirrel Position: ({st['squirrel']['x']}, {st['squirrel']['y']})")
    print(f" -> Objects: {[o['name'] for o in st['objects']]}")
    print(f" -> Journals: {len(memory.get_all_journals())}")
    print(f" -> Projects: {[p.get('name') for p in projects.list_projects()]}")

if __name__ == "__main__":
    reset()

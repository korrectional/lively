"""
Command-Line Interface for Lively.
Provides commands to run the server, trigger wake cycles, and manage authentication.
"""

import sys
import argparse
from lively.config import SERVER_HOST, SERVER_PORT
from lively.world import world
from lively.memory import memory
from lively.projects import projects
from lively.brain import brain
from lively.email_service import email_service

def cmd_serve(args):
    """Start the 2D world web server."""
    import uvicorn
    host = args.host or SERVER_HOST
    port = args.port or SERVER_PORT
    print(f"🐿️ Starting Lively 2D World server on http://{host}:{port} ...")
    uvicorn.run("lively.server:app", host=host, port=port, reload=args.reload)

def cmd_wake(args):
    """Trigger a squirrel cognitive wake cycle."""
    print("🐿️ Waking up Lively...")
    res = brain.run_cycle()
    print(f"✅ Wake cycle #{res.cycle_number} complete!")
    print(f" -> Position: {res.new_position}")
    if res.thoughts:
        print(f" -> Last Thought: {res.thoughts[-1]}")
    if res.built_objects:
        print(f" -> Built: {', '.join(res.built_objects)}")
    if res.coded_files:
        print(f" -> Coded: {', '.join(res.coded_files)}")
    if res.email_sent:
        print(f" -> Email: Sent to {res.email_sent.get('subject')}")

def cmd_think(args):
    """Trigger wake cycle and display step-by-step thinking process in real-time."""
    print("\n" + "="*60)
    print("🧠 LIVELY SQUIRREL COGNITIVE DELIBERATION STREAM")
    print("="*60)
    gen = brain.think_trace()
    for event in gen:
        stage = event.get("stage", "").upper()
        msg = event.get("message", "")
        print(f"\n[{stage}] {msg}")

        if stage == "PROMPT_READY":
            print("-" * 50)
            print("--- CONSTRUCTED PROMPT FOR SQUIRREL MIND ---")
            print(event.get("prompt", "")[:400] + "\n... (memories & telemetry summarized)")
            print("-" * 50)
        elif stage == "RAW_COGNITION":
            print("-" * 50)
            print("--- RAW SQUIRREL THOUGHT OUTPUT ---")
            print(event.get("raw_text", "").strip())
            print("-" * 50)
        elif stage == "ACTIONS_PARSED":
            for act in event.get("actions", []):
                print(f"  ⚡ {act.get('action_type')}: {act.get('parameters')}")
    print("\n" + "="*60)
    print("✅ SQUIRREL THINKING & ACTION CYCLE COMPLETED")
    print("="*60 + "\n")

def cmd_reset(args):
    """Reset world, memories, and projects to factory origin."""
    print("🧹 Resetting Lively: clearing memories, world objects, and restoring TreeberryPine...")
    world.reset()
    memory.reset()
    projects.reset()
    print("✅ Reset complete! TreeberryPine spawned at (45, 45). Lively is at (0, 0) with fresh memory.")

def cmd_status(args):
    """Display system status."""
    st = world.get_state()
    sq = st["squirrel"]
    print("==================================================")
    print("🐿️  LIVELY TELEMETRY STATUS")
    print("==================================================")
    print(f"Name:               {sq['name']}")
    print(f"Coordinates:        ({sq['x']}, {sq['y']})")
    print(f"Heading:            {sq['heading']}°")
    print(f"Battery:            {sq['battery']}%")
    print(f"Distance Traveled:  {sq['total_distance_traveled']}m")
    print(f"Total Cycles:       {sq['total_cycles']}")
    print(f"Last Thought:       {sq['last_thought']}")
    print(f"Current Activity:   {sq['current_activity']}")
    print(f"World Objects:      {len(st['objects'])}")
    print(f"Coded Projects:     {len(projects.list_projects())}")
    print(f"Saved Memories:     {len(memory.get_all_journals())}")
    print(f"Gmail Linked:       {'YES' if email_service.is_authenticated() else 'NO'}")
    print("==================================================")

def cmd_auth_gmail(args):
    """Guide the user through Gmail OAuth authorization link."""
    print("==================================================")
    print("🔗 GMAIL OAUTH AUTHORIZATION FOR LIVELY")
    print("==================================================")

    url = email_service.get_authorization_url()
    if url.startswith("#"):
        print(url)
        return

    print("Step 1: Open this authorization link in your browser:")
    print("")
    print(url)
    print("")
    print("Step 2: Sign in and authorize sending emails.")
    print("Step 3: Paste the authorization code below:")
    print("")
    try:
        code = input("Authorization Code > ").strip()
        if not code:
            print("Aborted.")
            return
        res = email_service.exchange_code(code)
        print("✅ Authentication successful! Tokens saved.")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
    except Exception as e:
        print(f"❌ Error exchanging code: {e}")

def cmd_add_object(args):
    """Add an object to the world."""
    obj = world.add_object(
        name=args.name,
        x=args.x,
        y=args.y,
        obj_type=args.type,
        description=args.desc,
        created_by="user"
    )
    print(f"✅ Created object '{obj.name}' at ({obj.x}, {obj.y}) [ID: {obj.id}]")

def main():
    parser = argparse.ArgumentParser(description="Lively: Autonomous Robot Squirrel & 2D World")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # serve
    p_serve = subparsers.add_parser("serve", help="Run the 2D world web server")
    p_serve.add_argument("--host", default=None, help=f"Host address (default: {SERVER_HOST})")
    p_serve.add_argument("--port", type=int, default=None, help=f"Port (default: {SERVER_PORT})")
    p_serve.add_argument("--reload", action="store_true", help="Enable auto-reload")
    p_serve.set_defaults(func=cmd_serve)

    # wake
    p_wake = subparsers.add_parser("wake", help="Trigger a squirrel wake cycle")
    p_wake.set_defaults(func=cmd_wake)

    # think
    p_think = subparsers.add_parser("think", help="Watch the squirrel think in real-time")
    p_think.set_defaults(func=cmd_think)

    # reset
    p_reset = subparsers.add_parser("reset", help="Reset all memories, objects, and restore TreeberryPine")
    p_reset.set_defaults(func=cmd_reset)

    # status
    p_status = subparsers.add_parser("status", help="Show Lively telemetry and status")
    p_status.set_defaults(func=cmd_status)

    # auth-gmail
    p_auth = subparsers.add_parser("auth-gmail", help="Authenticate with Gmail via OAuth link")
    p_auth.set_defaults(func=cmd_auth_gmail)

    # add-object
    p_add = subparsers.add_parser("add-object", help="Add an object to the 2D map")
    p_add.add_argument("name", help="Name of landmark/object")
    p_add.add_argument("x", type=float, help="X coordinate (-1000 to 1000)")
    p_add.add_argument("y", type=float, help="Y coordinate (-1000 to 1000)")
    p_add.add_argument("--type", default="landmark", choices=["tree", "landmark", "cache", "sensor", "contraption", "note"], help="Object type")
    p_add.add_argument("--desc", default="", help="Description")
    p_add.set_defaults(func=cmd_add_object)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

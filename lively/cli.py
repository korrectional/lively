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

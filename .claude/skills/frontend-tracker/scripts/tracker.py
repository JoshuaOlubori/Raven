#!/usr/bin/env python3
"""
Frontend Tracker Script
Manages the markdown issue tracker for frontend spec-driven development.
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Find repo root by looking for the existing work/ directory or .git
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "work").exists() or (parent / ".git").exists():
            return parent
    # Fallback: assume standard layout
    return current.parents[4]

ROOT = find_repo_root()
WORK = ROOT / "work" / "frontend"
TICKETS_DIR = WORK / "tickets"
REVIEWS_DIR = WORK / "reviews"
TRACKER_FILE = WORK / "TRACKER.md"
JOURNAL_FILE = WORK / "JOURNAL.md"

STATUS_ORDER = [
    "todo",
    "in-progress",
    "in-review",
    "awaiting-signoff",
    "changes-requested",
    "blocked",
    "done",
]
VALID_STATUSES = set(STATUS_ORDER)


def ensure_work_dirs():
    """Create work directories if they don't exist."""
    WORK.mkdir(parents=True, exist_ok=True)
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def parse_ticket(path: Path) -> dict:
    """Parse a ticket markdown file, returning front matter and body."""
    content = path.read_text(encoding="utf-8")
    fm = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
    return {"front_matter": fm, "body": content, "path": path}


def load_all_tickets() -> list[dict]:
    """Load all tickets from the tickets directory."""
    tickets = []
    for path in sorted(TICKETS_DIR.glob("FT-*.md")):
        t = parse_ticket(path)
        fm = t["front_matter"]
        if "id" in fm:
            fm["_path"] = path.relative_to(ROOT).as_posix()
            tickets.append(fm)
    return tickets


def load_backend_tickets() -> list[dict]:
    """Load backend ticket front matter for cross-stream blocker checks."""
    backend_tickets: list[dict] = []
    backend_dir = ROOT / "work" / "tickets"
    if not backend_dir.exists():
        return backend_tickets
    for path in sorted(backend_dir.glob("T-*.md")):
        fm = parse_ticket(path)["front_matter"]
        if fm.get("id", "").startswith("T-"):
            backend_tickets.append(fm)
    return backend_tickets


def get_ticket_path(ticket_id: str) -> Path:
    """Find the ticket file by ID."""
    for path in TICKETS_DIR.glob(f"{ticket_id}-*.md"):
        return path
    raise FileNotFoundError(f"Ticket {ticket_id} not found")


def update_ticket_status(ticket_id: str, new_status: str):
    """Update the status field in a ticket file."""
    path = get_ticket_path(ticket_id)
    content = path.read_text(encoding="utf-8")
    # Replace status line
    content = re.sub(r"^status: .*$", f"status: {new_status}", content, flags=re.MULTILINE)
    # Update updated date
    content = re.sub(r"^updated: .*$", f"updated: {datetime.now().strftime('%Y-%m-%d')}", content, flags=re.MULTILINE)
    path.write_text(content, encoding="utf-8")


def log_journal(message: str, phase: str = ""):
    """Append a line to the journal."""
    ensure_work_dirs()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    prefix = f"[{phase}] " if phase else ""
    line = f"{timestamp} {prefix}{message}\n"
    with JOURNAL_FILE.open("a", encoding="utf-8") as f:
        f.write(line)


def generate_board() -> str:
    """Generate the TRACKER.md board content."""
    tickets = load_all_tickets()
    if not tickets:
        return "# Frontend Tracker\n\n_No tickets yet._\n"

    # Sort by numeric ID
    def sort_key(t):
        m = re.match(r"FT-(\d+)", t.get("id", ""))
        return int(m.group(1)) if m else 999

    tickets.sort(key=sort_key)

    lines = [
        "# Frontend Tracker",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} - {len([t for t in tickets if t.get('status') == 'done'])}/{len(tickets)} tickets done._",
        "",
        "| ID | Title | Status | Mode | Blocked by |",
        "|---|---|---|---|---|",
    ]

    for t in tickets:
        tid = t.get("id", "?")
        title = t.get("title", "?")
        status = t.get("status", "?")
        mode = t.get("mode", "?")
        blocked = t.get("blocked_by", "-")
        ticket_path = t.get("_path", f"work/frontend/tickets/{tid}.md")
        relative_path = ticket_path.removeprefix("work/frontend/")
        lines.append(f"| [{tid}]({relative_path}) | {title} | {status} | {mode} | {blocked} |")

    return "\n".join(lines) + "\n"


def write_board():
    """Write the generated board to TRACKER.md."""
    ensure_work_dirs()
    TRACKER_FILE.write_text(generate_board(), encoding="utf-8")


def get_ready_tickets() -> list[dict]:
    """Return tickets whose blockers are all done."""
    tickets = load_all_tickets()
    done_ids = {
        t["id"]
        for t in [*tickets, *load_backend_tickets()]
        if t.get("status") == "done" and "id" in t
    }

    ready = []
    for t in tickets:
        if t.get("status") in ("todo", "blocked"):
            blocked_by = t.get("blocked_by", "").strip()
            if not blocked_by or blocked_by == "-":
                ready.append(t)
            else:
                blockers = [b.strip() for b in blocked_by.split(",")]
                if all(b in done_ids for b in blockers):
                    ready.append(t)
    return ready


def init_tracker():
    """Initialize the tracker structure."""
    ensure_work_dirs()
    if not TRACKER_FILE.exists():
        TRACKER_FILE.write_text("# Frontend Tracker\n\n_No tickets yet._\n", encoding="utf-8")
    if not JOURNAL_FILE.exists():
        JOURNAL_FILE.write_text("# Frontend Journal\n\n", encoding="utf-8")
    write_board()
    print("Frontend tracker initialized.")


def cmd_next(args):
    """Show next ready tickets."""
    ready = get_ready_tickets()
    if not ready:
        print("No ready tickets. Check blockers with 'board'.")
        return
    for t in ready:
        print(f"  {t['id']}: {t['title']} (blocked_by: {t.get('blocked_by', '-')})")


def cmd_set(args):
    """Set ticket status."""
    if args.status not in VALID_STATUSES:
        print(f"Invalid status: {args.status}. Valid: {', '.join(STATUS_ORDER)}")
        sys.exit(1)
    update_ticket_status(args.ticket_id, args.status)
    write_board()
    log_journal(f"{args.ticket_id} → {args.status}", "status")
    print(f"{args.ticket_id} → {args.status}")


def cmd_log(args):
    """Log a journal entry."""
    log_journal(args.message, args.phase)
    print(f"Logged: [{args.phase}] {args.message}")


def cmd_board(args):
    """Show the board."""
    print(generate_board())


def cmd_init(args):
    """Initialize tracker directories and files."""
    init_tracker()


def cmd_validate(args):
    """Validate frontend ticket IDs, dependencies, and dependency cycles."""
    tickets = load_all_tickets()
    backend_tickets = load_backend_tickets()
    by_id = {t.get("id"): t for t in tickets if t.get("id")}
    known_ids = set(by_id) | {t["id"] for t in backend_tickets if t.get("id")}
    errors: list[str] = []

    if len(by_id) != len(tickets):
        errors.append("Ticket IDs are missing or duplicated.")

    graph: dict[str, list[str]] = {}
    for ticket in tickets:
        ticket_id = ticket.get("id", "?")
        graph[ticket_id] = []
        raw_blockers = ticket.get("blocked_by", "").strip()
        blockers = (
            []
            if raw_blockers in ("", "-")
            else [blocker.strip() for blocker in raw_blockers.split(",")]
        )
        for blocker in blockers:
            if blocker not in known_ids:
                errors.append(f"{ticket_id} has unknown blocker {blocker}.")
            elif blocker in by_id:
                graph[ticket_id].append(blocker)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(ticket_id: str) -> None:
        if ticket_id in visiting:
            errors.append(f"Dependency cycle includes {ticket_id}.")
            return
        if ticket_id in visited:
            return
        visiting.add(ticket_id)
        for blocker in graph.get(ticket_id, []):
            visit(blocker)
        visiting.remove(ticket_id)
        visited.add(ticket_id)

    for ticket_id in graph:
        visit(ticket_id)

    if errors:
        print("Frontend tracker validation failed:")
        for error in dict.fromkeys(errors):
            print(f"- {error}")
        sys.exit(1)
    print(f"Frontend tracker valid ({len(tickets)} frontend tickets; backend blockers resolved).")


def main():
    parser = argparse.ArgumentParser(description="Frontend Tracker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize tracker directories and files")
    p_init.set_defaults(func=cmd_init)

    p_next = sub.add_parser("next", help="Show ready tickets")
    p_next.set_defaults(func=cmd_next)

    p_set = sub.add_parser("set", help="Set ticket status")
    p_set.add_argument("ticket_id", help="Ticket ID (e.g., FT-003)")
    p_set.add_argument("status", help=f"Status: {', '.join(STATUS_ORDER)}")
    p_set.set_defaults(func=cmd_set)

    p_log = sub.add_parser("log", help="Append to journal")
    p_log.add_argument("message", help="Journal message")
    p_log.add_argument("--phase", default="", help="Phase label (e.g., spec, tickets, implement)")
    p_log.set_defaults(func=cmd_log)

    p_board = sub.add_parser("board", help="Show tracker board")
    p_board.set_defaults(func=cmd_board)

    p_validate = sub.add_parser("validate", help="Check blocker references and cycles")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

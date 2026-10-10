#!/usr/bin/env python3
"""Markdown issue tracker for spec-driven development. Stdlib only.

Layout (under ./work):
  TRACKER.md   generated board        JOURNAL.md  append-only history
  tickets/T-001-slug.md               reviews/    review reports

Usage:
  tracker.py init
  tracker.py board                    regenerate work/TRACKER.md
  tracker.py list [--status S]
  tracker.py next                     tickets whose blockers are all done
  tracker.py set T-003 in-progress    change status (+ journal line)
  tracker.py log "message" [--phase P] [--ticket T-003]
"""
import argparse
import datetime as dt
import pathlib
import re
import sys

ROOT = pathlib.Path("work")
TICKETS = ROOT / "tickets"
JOURNAL = ROOT / "JOURNAL.md"
BOARD = ROOT / "TRACKER.md"
STATUSES = ["todo", "in-progress", "in-review", "changes-requested", "blocked", "done"]


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    meta["_path"] = path
    meta["blocked_by"] = [b.strip() for b in meta.get("blocked_by", "").split(",")
                          if b.strip() and b.strip() != "-"]
    return meta


def tickets():
    if not TICKETS.exists():
        return []
    return sorted((parse(p) for p in TICKETS.glob("T-*.md")), key=lambda t: t.get("id", ""))


def journal(msg, phase="-", ticket="-"):
    ROOT.mkdir(exist_ok=True)
    if not JOURNAL.exists():
        JOURNAL.write_text(
            "# Journal\n\nAppend-only history. Newest entries at the bottom.\n\n"
            "| When | Phase | Ticket | Entry |\n|---|---|---|---|\n",
            encoding="utf-8",
        )
    with JOURNAL.open("a", encoding="utf-8") as f:
        f.write(f"| {now()} | {phase} | {ticket} | {msg.replace('|', '/')} |\n")


def board():
    ts = tickets()
    done = sum(1 for t in ts if t.get("status") == "done")
    lines = ["# Tracker", "", f"_Generated {now()} - {done}/{len(ts)} tickets done._", "",
             "| ID | Title | Status | Mode | Blocked by |", "|---|---|---|---|---|"]
    for t in ts:
        lines.append(f"| [{t['id']}](tickets/{t['_path'].name}) | {t.get('title', '')} | "
                     f"{t.get('status', 'todo')} | {t.get('mode', 'AFK')} | "
                     f"{', '.join(t['blocked_by']) or '-'} |")
    ROOT.mkdir(exist_ok=True)
    BOARD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ts


def frontier(ts):
    status = {t["id"]: t.get("status", "todo") for t in ts}
    return [t for t in ts
            if t.get("status", "todo") in ("todo", "changes-requested")
            and all(status.get(b) == "done" for b in t["blocked_by"])]


def set_status(tid, new):
    if new not in STATUSES:
        sys.exit(f"status must be one of: {', '.join(STATUSES)}")
    for t in tickets():
        if t["id"] == tid:
            p = t["_path"]
            text = p.read_text(encoding="utf-8")
            text = re.sub(r"^status:.*$", f"status: {new}", text, count=1, flags=re.M)
            text = re.sub(r"^updated:.*$", f"updated: {dt.date.today()}", text, count=1, flags=re.M)
            p.write_text(text, encoding="utf-8")
            journal(f"status -> {new}", ticket=tid)
            board()
            return
    sys.exit(f"ticket {tid} not found")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("board")
    sub.add_parser("next")
    ls = sub.add_parser("list")
    ls.add_argument("--status")
    st = sub.add_parser("set")
    st.add_argument("id")
    st.add_argument("status")
    lg = sub.add_parser("log")
    lg.add_argument("message")
    lg.add_argument("--phase", default="-")
    lg.add_argument("--ticket", default="-")
    a = ap.parse_args()

    if a.cmd == "init":
        for d in (TICKETS, ROOT / "specs", ROOT / "reviews"):
            d.mkdir(parents=True, exist_ok=True)
        if not JOURNAL.exists():
            journal("tracker initialised", phase="setup")
        board()
        print("work/ initialised")
    elif a.cmd == "board":
        board()
        print(BOARD.read_text())
    elif a.cmd == "list":
        for t in tickets():
            if not a.status or t.get("status") == a.status:
                print(f"{t['id']}  [{t.get('status', 'todo')}]  {t.get('title', '')}")
    elif a.cmd == "next":
        f = frontier(tickets())
        if not f:
            print("No ready tickets (everything is done, in progress, or blocked).")
        for t in f:
            print(f"{t['id']}  [{t.get('mode', 'AFK')}]  {t.get('title', '')}")
    elif a.cmd == "set":
        set_status(a.id, a.status)
    elif a.cmd == "log":
        journal(a.message, a.phase, a.ticket)


if __name__ == "__main__":
    main()

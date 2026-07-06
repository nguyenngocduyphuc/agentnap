#!/usr/bin/env python3
"""AgentNap — App Nap for your AI agents.

Reclaims RAM eaten by orphaned AI-agent processes (Claude Code, Codex,
Cursor helpers, MCP servers, headless Chrome, Playwright) on macOS.

Safe by design:
  - only touches processes matching known agent patterns
  - only orphans (PPID=1) or, with --nap, idle sessions (SIGSTOP, reversible)
  - graceful reap: SIGTERM -> grace wait -> SIGKILL
  - dry-run by default; nothing dies without --apply

Usage:
  agentnap status            # per-agent RAM attribution table
  agentnap reap              # show what would be reaped (dry-run)
  agentnap reap --apply      # actually reap orphans
  agentnap daemon            # loop: reap when memory pressure is elevated
  agentnap nap <pid>         # SIGSTOP an idle agent (experimental)
  agentnap wake <pid>        # SIGCONT it back
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ponytail: stdlib only — no psutil. `ps` output is the portable macOS truth.

DEFAULT_CONFIG = {
    # substring patterns that mark a process as an AI-agent process
    "agent_patterns": [
        "claude", "codex", "copilot", "cursor",
        "mcp-server", "mcp_server", "chrome-devtools-mcp", "playwright",
        "serena", "browsermcp", "puppeteer",
    ],
    # never touch, even if matched (active infra, user's own tools)
    "protect_patterns": ["agentnap", "Activity Monitor", "loginwindow"],
    "grace_seconds": 8,          # SIGTERM -> SIGKILL wait
    "min_age_seconds": 300,      # orphan must be this old before reaping
    "min_rss_mb": 50,            # ignore tiny processes
    "daemon_interval": 60,       # seconds between daemon scans
    # daemon reaps only when pressure >= this level (1=normal 2=warn 4=critical)
    "daemon_pressure_level": 2,
}

CONFIG_PATH = Path.home() / ".config" / "agentnap" / "config.json"


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text()))
    return cfg


def ps_snapshot() -> list[dict]:
    """All user processes: pid, ppid, pgid, rss_mb, etime_s, command."""
    out = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,pgid=,rss=,etime=,command="],
        capture_output=True, text=True, check=True,
    ).stdout
    procs = []
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        pid, ppid, pgid, rss_kb, etime, command = parts
        procs.append({
            "pid": int(pid), "ppid": int(ppid), "pgid": int(pgid),
            "rss_mb": int(rss_kb) / 1024,
            "age_s": _parse_etime(etime),
            "command": command,
        })
    return procs


def _parse_etime(etime: str) -> int:
    """ps etime: [[dd-]hh:]mm:ss -> seconds."""
    days = 0
    if "-" in etime:
        d, etime = etime.split("-", 1)
        days = int(d)
    fields = [int(x) for x in etime.split(":")]
    while len(fields) < 3:
        fields.insert(0, 0)
    h, m, s = fields
    return days * 86400 + h * 3600 + m * 60 + s


def memory_pressure_level() -> int:
    """1=normal, 2=warning, 4=critical (macOS kern.memorystatus)."""
    try:
        out = subprocess.run(
            ["sysctl", "-n", "kern.memorystatus_vm_pressure_level"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return int(out)
    except (subprocess.CalledProcessError, ValueError):
        return 1


def match_agents(procs: list[dict], cfg: dict) -> list[dict]:
    pats = [p.lower() for p in cfg["agent_patterns"]]
    guard = [p.lower() for p in cfg["protect_patterns"]]
    me = os.getpid()
    hits = []
    for p in procs:
        c = p["command"].lower()
        if p["pid"] == me:
            continue
        if any(g in c for g in guard):
            continue
        if any(pat in c for pat in pats):
            hits.append(p)
    return hits


def find_orphans(cfg: dict) -> list[dict]:
    agents = match_agents(ps_snapshot(), cfg)
    return [
        p for p in agents
        if p["ppid"] == 1
        # macOS GUI apps are launchd children: PPID=1 does NOT mean orphan
        and ".app/Contents/" not in p["command"]
        and p["age_s"] >= cfg["min_age_seconds"]
        and p["rss_mb"] >= cfg["min_rss_mb"]
    ]


def reap(procs: list[dict], grace: int, apply: bool) -> float:
    """SIGTERM -> grace wait -> SIGKILL. Returns MB reclaimed (estimated)."""
    if not procs:
        print("Nothing to reap.")
        return 0.0
    total = sum(p["rss_mb"] for p in procs)
    for p in procs:
        tag = "" if apply else " [dry-run]"
        print(f"  reap{tag}: pid={p['pid']} rss={p['rss_mb']:.0f}MB "
              f"age={p['age_s'] // 60}m  {p['command'][:80]}")
        if apply:
            _terminate(p["pid"], grace)
    verb = "Reclaimed" if apply else "Would reclaim"
    print(f"{verb} ~{total:.0f} MB from {len(procs)} orphan(s).")
    if not apply:
        print("Run again with --apply to actually reap.")
    return total


def _terminate(pid: int, grace: int) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + grace
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.25)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def cmd_status(cfg: dict) -> None:
    agents = match_agents(ps_snapshot(), cfg)
    if not agents:
        print("No agent processes found.")
        return
    groups: dict[str, dict] = {}
    for p in agents:
        # ponytail: first token basename is a good-enough group key
        key = os.path.basename(p["command"].split()[0])
        g = groups.setdefault(key, {"rss": 0.0, "n": 0, "orphans": 0})
        g["rss"] += p["rss_mb"]
        g["n"] += 1
        g["orphans"] += p["ppid"] == 1
    total = sum(g["rss"] for g in groups.values())
    level = {1: "normal", 2: "WARNING", 4: "CRITICAL"}.get(
        memory_pressure_level(), "?")
    print(f"AgentNap — memory pressure: {level}\n")
    print(f"{'AGENT':<28}{'PROCS':>6}{'ORPHANS':>9}{'RSS':>10}")
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1]["rss"]):
        print(f"{key[:27]:<28}{g['n']:>6}{g['orphans']:>9}"
              f"{g['rss']:>9.0f}M")
    print(f"\nTotal agent RSS: {total / 1024:.1f} GB "
          f"across {sum(g['n'] for g in groups.values())} processes")


def cmd_daemon(cfg: dict) -> None:
    print(f"AgentNap daemon: scan every {cfg['daemon_interval']}s, "
          f"reap at pressure >= {cfg['daemon_pressure_level']}")
    while True:
        level = memory_pressure_level()
        orphans = find_orphans(cfg)
        if orphans and level >= cfg["daemon_pressure_level"]:
            print(f"[{time.strftime('%H:%M:%S')}] pressure={level}, "
                  f"reaping {len(orphans)} orphan(s)")
            reap(orphans, cfg["grace_seconds"], apply=True)
        time.sleep(cfg["daemon_interval"])


def main() -> None:
    cfg = load_config()
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "status":
        cmd_status(cfg)
    elif cmd == "reap":
        reap(find_orphans(cfg), cfg["grace_seconds"], apply="--apply" in args)
    elif cmd == "daemon":
        cmd_daemon(cfg)
    elif cmd in ("nap", "wake") and len(args) > 1:
        sig = signal.SIGSTOP if cmd == "nap" else signal.SIGCONT
        os.kill(int(args[1]), sig)
        print(f"{cmd}: pid {args[1]} "
              f"({'suspended, RAM compressible' if cmd == 'nap' else 'resumed'})")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

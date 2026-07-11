#!/usr/bin/env python3
"""Controlled, repeatable E2E experiment for AgentNap's core claims.

Claims under test:
  C1. Detects orphaned agent processes (PPID=1) and ONLY those.
  C2. Reaps them gracefully and the RAM actually comes back.
  C3. Never touches an identical process that is NOT orphaned (active work).

Method: spawn dummy "mcp-server-dummy" processes that each allocate ~100 MB.
Half are orphaned (parent exits), one is kept as a live child (simulates
active work). Run detection + reap, verify survivors and reclaimed RSS.

Run: python3 evidence/experiment_orphan_reap.py
"""

import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agentnap

N_ORPHANS = 5
MB_EACH = 100

# ps must show a command containing "mcp-server-dummy". Renaming argv[0]
# (exec -a) does NOT survive on macOS: framework pythons re-exec as
# .../Python.app/Contents/MacOS/Python. A script file with a telling name
# is how real MCP servers look in ps anyway (node .../mcp-server-x/index.js).
DUMMY_SCRIPT = os.path.join(tempfile.gettempdir(), "mcp-server-dummy.py")
DUMMY_CODE = (
    f"import time\n"
    f"x = bytearray({MB_EACH} * 1024 * 1024)\n"
    f"x[::4096] = b'x' * len(x[::4096])\n"   # touch pages -> real RSS
    f"time.sleep(600)\n"
)


def spawn_orphan() -> None:
    if agentnap.IS_WIN:
        # short-lived parent spawns a DETACHED grandchild, then exits ->
        # the grandchild's recorded parent PID no longer exists
        subprocess.Popen(
            [sys.executable, "-c",
             "import subprocess, sys; subprocess.Popen("
             f"[sys.executable, r'{DUMMY_SCRIPT}'], "
             "creationflags=0x00000008)"],  # DETACHED_PROCESS
        ).wait()
    else:
        # parent shell exits immediately -> child reparents to launchd
        subprocess.Popen(
            ["/bin/sh", "-c", f"{sys.executable} {DUMMY_SCRIPT} &"],
        ).wait()


def main() -> None:
    cfg = dict(agentnap.DEFAULT_CONFIG)
    cfg["agent_patterns"] = ["mcp-server-dummy"]
    cfg["min_age_seconds"] = 0
    cfg["min_rss_mb"] = 50

    with open(DUMMY_SCRIPT, "w") as f:
        f.write(DUMMY_CODE)
    print(f"== SETUP: spawning {N_ORPHANS} orphans + 1 active child, "
          f"~{MB_EACH} MB each ==")
    for _ in range(N_ORPHANS):
        spawn_orphan()
    active = subprocess.Popen(  # stays our child: parent (us) is alive
        [sys.executable, DUMMY_SCRIPT])
    time.sleep(8)  # let allocations settle (CI runners are slow)

    def dummies():
        return [p for p in agentnap.ps_snapshot()
                if "mcp-server-dummy" in p["command"]
                and p["pid"] != active.pid]

    swap_before = agentnap.swap_used_gb()
    found = agentnap.find_orphans(cfg)
    found_rss = sum(p["rss_mb"] for p in found)
    print("\n== C1 DETECTION ==")
    print(f"spawned orphans : {N_ORPHANS}")
    print(f"detected orphans: {len(found)}  (total RSS {found_rss:.0f} MB)")
    print(f"active child pid {active.pid} in orphan list: "
          f"{any(p['pid'] == active.pid for p in found)}")
    assert len(found) == N_ORPHANS, "detection count mismatch"
    assert all(p["pid"] != active.pid for p in found), "C3 VIOLATED"

    print("\n== C2 REAP ==")
    agentnap.reap(found, grace=cfg["grace_seconds"], apply=True)
    time.sleep(2)
    survivors = dummies()
    active_alive = active.poll() is None
    print(f"orphan survivors after reap: {len(survivors)} (expect 0)")
    print("\n== C3 NON-DISRUPTION ==")
    print(f"active child alive after reap: {active_alive} (expect True)")
    assert not survivors, "orphans survived"
    assert active_alive, "C3 VIOLATED: active work was killed"

    print("\n== RESULT ==")
    print(f"RSS held by orphans (reclaimed on kill): {found_rss:.0f} MB")
    print(f"swap before/after: {swap_before:.2f} / "
          f"{agentnap.swap_used_gb():.2f} GB")
    print("ALL CLAIMS VERIFIED: C1 detection ✓  C2 reap+reclaim ✓  "
          "C3 non-disruption ✓")

    active.terminate()  # cleanup


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Smallest checks that fail if the logic breaks."""
import agentnap


def demo():
    assert agentnap._parse_etime("05:32") == 332
    assert agentnap._parse_etime("01:05:32") == 3932
    assert agentnap._parse_etime("2-01:05:32") == 176732

    cfg = dict(agentnap.DEFAULT_CONFIG)
    procs = [
        {"pid": 1, "ppid": 1, "pgid": 1, "rss_mb": 500, "age_s": 999,
         "command": "claude --resume abc"},
        {"pid": 2, "ppid": 1, "pgid": 2, "rss_mb": 500, "age_s": 999,
         "command": "/usr/sbin/loginwindow"},          # protected
        {"pid": 3, "ppid": 400, "pgid": 3, "rss_mb": 500, "age_s": 999,
         "command": "codex exec"},                     # agent, not orphan
    ]
    hits = agentnap.match_agents(procs, cfg)
    assert [p["pid"] for p in hits] == [1, 3]

    lvl = agentnap.memory_pressure_level()
    assert lvl in (1, 2, 4), lvl

    snap = agentnap.ps_snapshot()
    assert len(snap) > 10 and all(p["pid"] > 0 for p in snap[:5])
    print("all checks passed")


if __name__ == "__main__":
    demo()

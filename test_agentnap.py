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
         "pcpu": 0.0, "command": "claude --resume abc"},
        {"pid": 2, "ppid": 1, "pgid": 2, "rss_mb": 500, "age_s": 999,
         "pcpu": 0.0, "command": "/usr/sbin/loginwindow"},   # protected
        {"pid": 3, "ppid": 400, "pgid": 3, "rss_mb": 500, "age_s": 999,
         "pcpu": 0.0, "command": "codex exec"},              # not orphan
    ]
    hits = agentnap.match_agents(procs, cfg)
    assert [p["pid"] for p in hits] == [1, 3]

    # idle advisor: only non-orphan, old, low-CPU, non-.app processes
    idle_procs = [
        {"pid": 10, "ppid": 400, "pgid": 10, "rss_mb": 800, "age_s": 8000,
         "pcpu": 0.1, "command": "claude"},                  # idle candidate
        {"pid": 11, "ppid": 400, "pgid": 11, "rss_mb": 800, "age_s": 8000,
         "pcpu": 45.0, "command": "claude"},                 # busy → skip
        {"pid": 12, "ppid": 1, "pgid": 12, "rss_mb": 800, "age_s": 8000,
         "pcpu": 0.0, "command": "claude"},                  # orphan → reap's
    ]
    assert [p["pid"] for p in agentnap.find_idle(idle_procs, cfg)] == [10]

    assert agentnap.swap_used_gb() >= 0.0
    report, summary = agentnap.build_advice(cfg)
    assert "AgentNap Advisor" in report and "orphans" in summary

    lvl = agentnap.memory_pressure_level()
    assert lvl in (1, 2, 4), lvl

    snap = agentnap.ps_snapshot()
    assert len(snap) > 10 and all(p["pid"] > 0 for p in snap[:5])
    print("all checks passed")


if __name__ == "__main__":
    demo()

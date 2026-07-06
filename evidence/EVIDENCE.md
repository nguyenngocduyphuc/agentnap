# AgentNap — Evidence & Verification

Every claim this product makes, with how it was verified. Updated 2026-07-06.

## Layer 1 — Unit self-checks (repeatable)

`python3 test_agentnap.py` — pattern matching, protect list, etime parsing,
idle detection, busy-orphan sparing, live ps/pressure probes. Run on every
change; all passing.

## Layer 2 — Controlled E2E experiment (repeatable)

`python3 evidence/experiment_orphan_reap.py` — spawns 5 real orphaned
~100 MB processes plus 1 identical *non*-orphaned process (simulating active
work), then verifies:

- C1 detection: 5/5 orphans found, active process NOT flagged
- C2 reap: 0 survivors, ~561 MB RSS released
- C3 non-disruption: active process still alive afterwards

Captured run: [`experiment_run_2026-07-06.txt`](experiment_run_2026-07-06.txt).

Since v0.4 this experiment also runs in CI on GitHub's clean runners on
every push — verification on independent infrastructure, not just the
author's machine. Since v0.5 the matrix covers **both `macos-latest` and
`windows-latest`**, so the Windows beta's detection/reap/non-disruption
claims are proven on real Windows before every release:
[actions/workflows/test.yml](https://github.com/nguyenngocduyphuc/agentnap/actions/workflows/test.yml).

## Layer 3 — Independent safety audit (external model)

[`safety_audit_deepseek_2026-07-06.md`](safety_audit_deepseek_2026-07-06.md)
— DeepSeek (independent of the authoring model) traced every kill path in
the source. Result: **4/4 safety claims PASS**, 6 findings. Actions taken:

| Audit finding | Action |
|---|---|
| #1 PPID=1 can be nohup'd *active* work (HIGH) | Fixed — busy orphans (CPU > 10%) are never auto-reaped, advisory only |
| #2 substring pattern false positives | Mitigated by #1 fix + min-age + min-RSS stack; documented |
| #3 `.app/Contents/` guard too coarse | Fixed — replaced with LaunchServices (`lsappinfo`) GUI check |
| #4 grace 8 s may be short for big processes | Configurable (`grace_seconds`); documented |
| #5 daemon reaps without confirmation | By design; README states it explicitly + notification on every action |
| #6 default protect list short | Expanded (tmux, sshd, VS Code, iTerm) + user-extensible |
| Guarantee wording too absolute | Rewritten to the precise version in README |

## Layer 4 — Field results (author's machine, 32 GB M-series, 2026-07-06)

One day of real usage on a machine running ~400 agent-related processes
(cmux + Claude Code + Codex + MCP servers + headless Chrome):

| Metric | before (13:57) | after (18:15) |
|---|---|---|
| swap used | 23.8 GB (26.5 GB earlier that morning) | 5.2 GB |
| memory compressor | 9.3 GB | 4.6 GB |
| memory pressure | WARNING | normal |
| sessions killed by tooling | — | 0 |

Honest attribution: the directly measured effect of idle-agent hibernation
was −2.6 GB RSS within 15 minutes; the rest of the swap decline is the
cascade (fewer resident pages → macOS drained swap files 24.5 GB → 6 GB) plus
natural session turnover. The advisor separately identified 5 forgotten
sessions idle 47–90 h holding ~1.7 GB.

## Known limitations (told to users, not hidden)

- Orphan detection is heuristic: pattern + PPID=1 + age + RSS + idle-CPU +
  non-GUI. It fails safe (spares) rather than fails deadly (kills).
- Won't catch leaks *inside* a live process (e.g. one node process growing to
  108 GB) — that's the vendor's bug; AgentNap's advisor will still name the
  culprit.
- Windows is beta: no daemon (no cheap per-process CPU signal to protect
  busy orphans yet), pcpu reads 0.0, GUI detection relies on protect
  patterns. Manual commands are dry-run-first by design.

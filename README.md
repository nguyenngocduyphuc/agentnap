# AgentNap 😴

**App Nap for your AI agents.** Reclaim the gigabytes of RAM that Claude Code,
Codex, Cursor, MCP servers, and headless Chrome quietly leak on your Mac.

## The problem

AI coding agents spawn subagents, MCP servers, and browser daemons. When a
session ends, those children often survive as **orphans** (PPID=1) — 200 MB to
1 GB each. After a day of vibe-coding your Mac is at 30 GB used, 25 GB swap,
and the fans are on. You are not alone:

- [claude-code#23252](https://github.com/anthropics/claude-code/issues/23252) — 12 GB RAM on macOS 15.5
- [claude-code#18859](https://github.com/anthropics/claude-code/issues/18859) — 4 idle sessions → 60 GB
- [claude-code#56960](https://github.com/anthropics/claude-code/issues/56960) — node process at 108 GB
- [claude-code#34568](https://github.com/anthropics/claude-code/issues/34568) — process spawning → system DoS

## What AgentNap does

```
$ agentnap advise
🩺 AgentNap Advisor — 14:22

Memory pressure: WARNING 🟡   swap: 22.3 GB   agent RAM: 8.6 GB

Safe now (zero disruption — these are already dead):
  ✓ Reclaim ~2100 MB from 6 orphaned process(es)  →  agentnap reap --apply

Advisory (your call — may interrupt a session you still want):
  • claude pid=52942 holds 223 MB, idle 89h+ — close its tab, or
    `agentnap nap 52942` (reversible)

AgentNap never kills active work. Automatic = orphans only; the rest is advice.
```

- **`advise`** — plain-language diagnosis: what's eating RAM, what's safe to
  reclaim right now, and what's *your* call. For people who know they have a
  problem, not a process tree.
- **`status`** — live per-agent RAM attribution table.
- **`reap`** — kills *only* orphaned (PPID=1) agent processes, gracefully
  (SIGTERM → 8 s grace → SIGKILL). Dry-run by default.
- **`daemon`** — background watchdog. When macOS reports elevated memory
  pressure it auto-reaps orphans (the only automatic action) and sends one
  native notification with advice — max one per 30 min, no nagging.
- **`nap` / `wake`** — SIGSTOP an idle agent so macOS can compress/swap its
  pages, SIGCONT to resume. Fully reversible. (experimental)

**The non-disruption guarantee:** the only thing AgentNap ever does on its own
is remove processes whose parent is already dead. Anything that could touch a
live session is surfaced as advice and left to you.

New to the problem? Read the [AI-Agent RAM Playbook](PLAYBOOK.md) — five
habits that prevent the mess in the first place.

## Why it's safe

1. Touches **only** processes matching known agent patterns — never your IDE,
   browser, or shell.
2. Reaps **only orphans**: parent already dead, nothing is using them.
3. Graceful two-stage termination — no corrupted SQLite, no locked sockets.
4. **Dry-run by default.** Nothing dies without `--apply`.
5. Never disables swap, never allocates dummy memory "to clean" — the
   anti-patterns that break Macs.

## Install

```bash
git clone https://github.com/<you>/agentnap && cd agentnap
./install.sh        # symlinks agentnap + optional launchd daemon
```

Requires macOS + Python 3.9+ (system Python works). Zero dependencies.

## Configure

Optional `~/.config/agentnap/config.json` — override any default:

```json
{
  "agent_patterns": ["claude", "codex", "my-custom-agent"],
  "min_age_seconds": 300,
  "daemon_pressure_level": 2
}
```

## AgentNap Pro (coming soon)

The CLI stays free and MIT. **Pro** is a native menu-bar app:

- live RAM/swap gauge per agent, one-click reclaim
- event-driven memory-pressure response (GCD `DISPATCH_SOURCE_TYPE_MEMORYPRESSURE`)
- idle-session hibernation policies with auto-resume
- headless-Chrome flag injection (`--js-flags=--max-old-space-size`, renderer caps)
- weekly "RAM saved" report

Join the waitlist: *(link)*

**Windows?** The same leak exists there (WSL2 + node MCP servers). Windows
support is on the Pro roadmap — tell us on the waitlist if you need it first.

## License

MIT — see [LICENSE](LICENSE).

# AgentNap 😴

[![tests](https://github.com/nguyenngocduyphuc/agentnap/actions/workflows/test.yml/badge.svg)](https://github.com/nguyenngocduyphuc/agentnap/actions/workflows/test.yml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20beta-blue)
![deps](https://img.shields.io/badge/dependencies-zero-brightgreen)

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
- **`nap` / `wake`** — SIGSTOP idle agents so macOS can compress/swap their
  pages, SIGCONT to resume. Fully reversible. (experimental)
- **`advise --ai`** — optional: sends the diagnostic report to *your* LLM for
  a personalized plan. Bring your own key, any OpenAI-compatible API
  (DeepSeek, OpenAI, Groq, OpenRouter, local Ollama):

  ```bash
  export AGENTNAP_API_KEY=sk-...
  agentnap advise --ai        # default: DeepSeek (~$0.0002/call)
  ```

  Override `ai_api_base` / `ai_model` in the config for other providers.
  Your process data goes only to the endpoint you chose; without a key,
  everything works fully offline.

**The non-disruption guarantee (precise version):** the only automatic action
is reaping *orphaned agent processes* — parent exited, matches an agent
pattern, idle-CPU, older than 5 minutes, and not a GUI app (verified via
LaunchServices, not path guessing). A `nohup`'d script that is orphaned but
*busy* is deliberately spared and only mentioned in `advise`. Anything that
could touch a live session is surfaced as advice and left to you.
Independently audited — see [`evidence/`](evidence/) for the safety audit and
a repeatable verification experiment.

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

Join the waitlist: **[👍 this issue](https://github.com/nguyenngocduyphuc/agentnap/issues/1)**

**Windows?** A beta shipped: `status` / `advise` / `reap` (+ `stats`) work
today — orphan detection uses parent-liveness (no PID-1 reparenting on
Windows) and reaping goes `taskkill` → grace → `taskkill /F`. The whole E2E
experiment runs in CI on `windows-latest` on every push. The daemon and
`nap`/`wake` stay macOS-only until there is a cheap busy-orphan CPU signal on
Windows — AgentNap refuses loudly rather than guessing quietly. Vote for
full Windows on the waitlist issue.

### How do I know it's working? — receipts

Every applied reap is logged to `~/.agentnap/ledger.jsonl`:

```
$ agentnap stats
AgentNap receipts since 2026-07-07:
  4.2 GB reclaimed  ·  37 orphaned processes reaped  ·  9 cleanups
```

## License

MIT — see [LICENSE](LICENSE).

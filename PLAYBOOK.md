# The AI-Agent RAM Playbook

How to run Claude Code, Codex, Cursor, and MCP servers all day without
melting your Mac. Distilled from Apple documentation, Chromium docs, the MCP
spec, and hundreds of memory-leak reports. Five habits, ranked by impact.

## 1. Close sessions you're done with — the tab is not free

An "idle" agent session still holds 150 MB – 1 GB of RAM, *forever*. Four
forgotten sessions have taken machines to
[60 GB](https://github.com/anthropics/claude-code/issues/18859). Finished a
task? Close the tab/session, don't just switch away.

`agentnap advise` lists sessions idle for hours with their RAM — the ones you
forgot exist.

## 2. Let the daemon reap orphans — never `kill -9` by hand

When an agent session crashes or closes uncleanly, its children (MCP servers,
browser daemons, subagents) survive as **orphans** — macOS has no Linux-style
parent-death signal, so they run until reboot.

- Do: `agentnap daemon` (or `reap --apply` occasionally). It terminates
  gracefully: SIGTERM → 8 s grace → SIGKILL.
- Don't: `kill -9` sprees. Instant SIGKILL skips cleanup — corrupted SQLite,
  locked sockets, leaked file descriptors, and *new* orphaned grandchildren.

## 3. One agent fleet, not five terminals of forgotten agents

Every parallel session multiplies the baseline: agent process + node MCP
servers + a headless Chrome ≈ 1–2 GB per session. Keep a hard personal cap
(e.g. 3 live sessions on 16 GB, 6 on 32 GB) and use a session manager that
hibernates idle agents (cmux's Agent Hibernation, or `agentnap nap <pid>` —
a suspended process consumes zero CPU and macOS compresses its RAM under
pressure, fully reversible with `wake`).

## 4. Starve your headless Chrome

Browser automation (Playwright, Puppeteer, chrome-devtools MCP) is usually
the fattest child. Cap it at launch:

```
--js-flags=--max-old-space-size=512  --renderer-process-limit=2  --disable-gpu
```

and restart the browser instance every ~50–100 tasks — page-level leaks grow
linearly and never come back on their own.

## 5. Don't fight macOS — no swap-off, no "RAM cleaner" apps

- **Never disable swap** to "protect the SSD" — that removes the safety valve
  and converts slowdowns into kernel panics.
- **Skip memory-cleaner apps** that allocate huge dummy buffers to "free" RAM:
  they cause CPU churn and SSD wear while making pressure *worse*.
- A big swap number after a heavy day is fine; macOS reclaims lazily. Judge
  health by **memory pressure** (green/yellow/red), not by "memory used".

---

### The 30-second daily routine

```bash
agentnap advise        # what's wrong, in plain English
agentnap reap --apply  # reclaim the guaranteed-safe part
```

Everything else in the report is advice — you decide what's worth
interrupting.

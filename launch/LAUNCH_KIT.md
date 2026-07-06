# AgentNap Launch Kit

> Drafts for founder review. Post order: GitHub public → Show HN → Reddit →
> dev.to. Each channel links back to the repo; Pro waitlist link in README
> captures emails (Gumroad "coming soon" product or Tally form).

## Monetization ladder

1. **Free CLI (MIT)** — distribution + GitHub stars + trust.
2. **Pro waitlist** — validate willingness to pay before building the app.
3. **AgentNap Pro** — native menu-bar app, $24 one-time launch price
   (anchor: competitors are free scripts; value: GUI + zero-config +
   launchd MCP wrapping + weekly RAM report). Sell via Gumroad; later Setapp.
4. **Content flywheel** — PLAYBOOK.md chapters as dev.to/blog posts ranking
   for "claude code memory leak" queries (high-intent, growing).

## Show HN draft

**Title:** Show HN: AgentNap – reclaim the RAM your AI coding agents leak on
macOS

**Body:**
My 32 GB MacBook was at 30 GB used and 25 GB swap. The culprit wasn't one
app — it was ~400 processes left behind by AI coding agents: orphaned MCP
servers, headless Chromes, and subagents whose parent sessions were long
gone. GitHub is full of the same story (claude-code issues report 12 GB,
60 GB, even 108 GB).

AgentNap is a zero-dependency Python CLI:

- `agentnap advise` — plain-language diagnosis: what's eating RAM, what's
  safe to reclaim, what's your call
- `agentnap reap` — gracefully kills *only* orphans (PPID=1, non-.app),
  SIGTERM → grace → SIGKILL, dry-run by default
- `agentnap daemon` — acts only when macOS reports real memory pressure
  (sysctl memorystatus), not on a timer

Design rule: it never touches active work. The only automatic action is
removing processes whose parent is already dead; everything else is advice.

Gotcha I hit building it: on macOS every GUI app has PPID=1 (launchd), so
naive orphan detection kills the user's running apps. You have to exclude
.app bundles.

Free and MIT. A menu-bar Pro version is on the waitlist.

## Reddit draft (r/ClaudeAI, r/macapps)

**Title:** I built a free tool that reclaimed 4 GB of RAM my AI agents were
leaking

**Body:** Short version of HN post + before/after numbers + screenshot of
`agentnap advise` output. Tone: sharing a fix, not selling. Mention Pro only
if asked.

## dev.to article outline

**Title:** Why AI coding agents eat your Mac's RAM (and the 5 habits that fix it)

1. The anatomy of the leak: sessions → subagents → MCP servers → orphans
2. Real numbers from GitHub issues (12/60/108 GB)
3. The 5 playbook habits (from PLAYBOOK.md)
4. How AgentNap automates the safe part
5. CTA: repo + waitlist

## Assets needed before launch

- [x] GitHub repo public: https://github.com/nguyenngocduyphuc/agentnap
- [x] Release v0.4.0 published with verified-evidence notes
- [x] CI green on clean macOS runners (tests badge in README)
- [x] Waitlist live: pinned issue #1 (👍 = signup; zero cost, public
      social proof). Gumroad/Tally can replace it when Pro is near.
- [x] README badges: tests, license, platform, zero-deps
- [ ] Screenshot/GIF of `agentnap advise` (founder: 1 terminal screenshot)
- [ ] Founder posts Show HN + r/ClaudeAI (drafts above; personal accounts)

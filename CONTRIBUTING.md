# Contributing

## The Python-version contract

AgentNap must run on **stock Apple system Python** (`/usr/bin/python3`,
currently 3.9.6, no Homebrew) — that is what a fresh Mac actually has, and
it is the whole point of "zero dependencies, zero setup". `pyproject.toml`
declares `requires-python = ">=3.9"`; that is not aspirational, it is tested.

This bit us once: a `list[dict] | None` type hint (PEP 604, Python 3.10+)
shipped in v0.5 and crashed the CLI on launch for any 3.9 machine. Two guards
now exist so it can't happen silently again:

### 1. Local pre-push hook (catches it before it leaves your machine)

```bash
git config core.hooksPath .githooks
```

Run this once after cloning. `.githooks/pre-push` then runs
`test_agentnap.py` against `/usr/bin/python3` and your default `python3`
before every push, and blocks the push if either fails. Bypass deliberately
(not by habit) with `git push --no-verify`.

### 2. CI matrix (catches it before merge, regardless of the hook)

`.github/workflows/test.yml` runs on **Python 3.9 and 3.12, on both macOS
and Windows** — 3.9 specifically because it is the version that broke, not
because it is "the oldest we felt like supporting."

### If you need 3.10+ syntax for something

Don't. If it seems unavoidable, gate it behind a `sys.version_info` check
with a 3.9-compatible fallback, and add a case to `test_agentnap.py` that
would have caught the original bug (import the module; that alone would
have failed on 3.9 last time).

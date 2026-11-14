# Agent context files: how to write `AGENTS.md` and `PROGRESS.md`

A practical guide. Read this once, keep it, use it in any project.

---

## 1. The one-sentence version

**`AGENTS.md` holds rules** — how the agent should work and what the project requires.
**`PROGRESS.md` holds state** — where the work stands right now.

Rules change rarely. State changes every session. Do not mix them.

---

## 2. What the agent actually loads

This matters more than any style advice. The rules below are what the harness
really does (`@deepseek-ai/dsh-agent-instructions`, enabled by default).

The agent receives **two chains** on the first request of a session:

| Chain | Files, in order |
|---|---|
| User-global | `$DSH_HOME/AGENTS.md` (`~/.dsh/AGENTS.md`), then `<agentsHome>/AGENTS.md` (`~/.agents/AGENTS.md`) |
| Project | every candidate file from the **project root down to the working directory**, broad to specific |

Inside each directory it looks for, in this order:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `AGENTS.local.md`
4. `CLAUDE.local.md`

Important details:

- **Only these four names are loaded automatically.** No other `.md` is ever read
  on its own. `PROGRESS.md`, `NOTES.md`, `PLAN.md` cost a tool call — the agent
  opens them only if `AGENTS.md` tells it to.
- **The project root is found by a marker**, `.git` by default. If a project has
  no `.git`, discovery climbs upward and may not stop where you expect.
- **Budget:** 64 KB per chain. That is a safety cap, not a target.
- **Duplicates are skipped** — a `CLAUDE.md` identical to `AGENTS.md` is not
  loaded twice.
- **Refresh:** the chain reloads when the working directory changes, and picks
  up a newly relevant nested file after the agent reads or writes in that
  directory. Creating a file mid-session does not always take effect
  immediately; a new session always does.

Practical consequence: **the project `AGENTS.md` is the only reliable place to
put something you want the agent to know without being asked.**

---

## 3. `AGENTS.md` — rules

### Write this

| Category | Example |
|---|---|
| How to run things | `pytest -q` for tests, `python run_evaluation.py --split val` |
| Layout, at a glance | `app/` API, `frontend/` UI, `data/` fixtures — do not edit by hand |
| Conventions that are not obvious | "theme tokens only, never raw hex"; "hooks must be unconditional" |
| Gotchas | "install is a symlink, so try a refresh before reinstalling" |
| Constraints | "never modify `data/`", "do not upgrade the pinned SDK without asking" |
| Pointers to deep docs | "for schema rules see `docs/data_schema.md`" |
| Verification habits | "after editing `client.js` run `node --check`" |

### Do not write this

| Anti-pattern | Why |
|---|---|
| "Write clean, maintainable code" | Not actionable. The model already tries. |
| Anything the code states plainly | It can read `package.json` itself. Duplicating wastes tokens and goes stale. |
| A copy of the README | README is for humans. Link to it instead. |
| Aspirational architecture | Rules about a design that does not exist yet confuse decisions. |
| Every file's purpose | A short directory table beats 40 one-line entries. |
| Secrets, keys, tokens | These files are plain text and often committed. |
| Dates and "current status" | That belongs in `PROGRESS.md`. |

### How much

- **User-global (`~/.dsh/AGENTS.md`): 30–60 lines.** Behaviour only.
- **Project `AGENTS.md`: 60–150 lines.** Above ~200 lines the agent starts
  skimming and you burn context every single session.
- Hard ceiling is 64 KB. Ignore it. Aim for **under 4 KB** — roughly 1,000
  tokens, which is about 1% of a cheap session.

### How to write it

- Bullets, imperative voice: "run `pytest -q`", not "tests can be run by...".
- Exact commands, copy-pasteable.
- Say *when* to read something: "read `docs/x.md` before changing the schema".
- One idea per line. Long paragraphs get skimmed.
- Write for a competent stranger who has never seen the repo.

**Test before saving:** *"Would a new teammate need this to avoid a mistake?"*
If no, cut it.

---

## 4. `PROGRESS.md` — state

Not loaded automatically. Its job is to survive a session boundary.

### The four sections

Keep it to exactly four headings. Each answers a question a fresh session
cannot answer by reading the code.

| Section | Answers |
|---|---|
| `## Now` | what works today |
| `## Decisions` | why the code looks like this |
| `## Unverified` | what looks finished but was never confirmed |
| `## Next` | the single next action |

Why exactly these four: **Now** and **Next** stop a new session from redoing or
re-deciding finished work. **Decisions** stops it from "improving" something you
chose on purpose. **Unverified** is the one everyone forgets — the code looks
complete, so a new session will confidently call it done. Only this section says
otherwise.

### Write this

- **What is built and working** — one or two lines.
- **Decisions and the reason** — "panel uses the black base colour, not the
  overlay grey, because the grey read as a separate window".
- **Known unverified areas** — "the toggle-swap has never been seen rendered".
- **Next steps** — the single next thing.
- **Environment quirks** — ports, credentials needed, how to launch.

### Do not write this

- A diary of every edit — that is what git history is for.
- Code blocks longer than a few lines.
- A repeating changelog. **Rewrite the file; do not append forever.**
- Anything already in `AGENTS.md`. Rules and state must not drift into
  contradiction.

### How much

**20–60 lines.** If it grows past ~80, you are keeping history instead of state.

### How to keep it — and why switching sessions needs no ritual

Update at the **end of every task**, not at the moment you switch sessions.

That one choice removes the handoff ritual completely. If the file is updated as
work finishes, it is always current, so opening a new chat needs nothing special:
no re-pasting old prompts, no "summarise everything for the next session", no
picking out what matters. The handoff already happened.

Updating "before switching sessions" fails for a simple reason: sessions often
just end — the window closes, the token limit hits, you forget. A trigger that
depends on remembering a ritual is a trigger that eventually gets skipped.

- Keep a **Decisions** list, and delete entries that become permanent facts —
  those move into `AGENTS.md`.
- Date the **Next** line if sessions are far apart.
- Check that it actually happened:

```powershell
Get-Item .\PROGRESS.md | Select-Object LastWriteTime
```

If the timestamp did not move, say "update progress" — two words, guaranteed.

---

## 5. Where files go

```
~/.dsh/AGENTS.md              # your personal, cross-project behaviour rules
~/.agents/AGENTS.md           # optional, shared across a machine

<repo>/AGENTS.md              # project rules — the important one
<repo>/PROGRESS.md            # current state
<repo>/AGENTS.local.md        # machine-specific, not committed

<repo>/packages/api/AGENTS.md # only if that area has rules the root file
                              # would make too broad; loaded when working there
```

Rules of thumb:

- **One global file, one file per project.** Most people stop there.
- **One `PROGRESS.md` per project, never a global one.** A global progress file
  would mix unrelated projects, grow forever, and be sent to every session
  everywhere — you would be paying for project A's state while working on
  project B.
- Nested `AGENTS.md` is for monorepos, not for a two-folder project.
- Use `.local.md` for anything you would not commit (paths, credentials
  locations, personal preferences).

---

## 6. Who should write these?

Short answer:

| File | Who writes | Who reviews |
|---|---|---|
| Global `~/.dsh/AGENTS.md` | **You**, once | — |
| Project `AGENTS.md` | **Agent drafts, you approve** | You |
| `PROGRESS.md` | **Agent writes**, you correct | Light |

Reasoning:

- **Global rules are policy.** They change how the agent behaves in every
  project. Letting the agent rewrite its own constraints is a bad loop — it will
  soften them. Write it yourself; ask for a draft if stuck.
- **Project `AGENTS.md` is facts plus hard-won gotchas.** The agent is good at
  extracting commands and layout by reading the repo, and bad at knowing which
  constraints matter to you. So: ask it to draft, then cut and correct by hand.
  Re-draft when the structure changes.
- **`PROGRESS.md` is operational.** The agent knows exactly what it just did and
  what it left unverified; you do not want to type it. Let it maintain the file.
  Say **"update PROGRESS.md"** at the end of a chunk of work, then read it once
  and fix anything wrong.

A workflow that works well:

1. New project → ask the agent to draft `AGENTS.md` from the repo. Edit it.
2. First real chunk of work → create `PROGRESS.md`. The update rule only fires
   once the file exists.
3. Long task → ask in **plan mode** first, then implement.
4. End of each task → the agent updates `PROGRESS.md` on its own, because the
   global rule requires it. If it forgets, say "update progress".
5. New session → `AGENTS.md` loads itself and `PROGRESS.md` is read first, again
   because of the global rule. Nothing to paste, nothing to summarise.

---

## 7. Mistakes that cost the most

| Mistake | Cost |
|---|---|
| Never writing `AGENTS.md` | Every session re-discovers the project; you re-explain the same rules |
| Writing a 500-line `AGENTS.md` | 3–4k tokens every session, and the agent skims it |
| Putting state in `AGENTS.md` | It goes stale and starts contradicting reality |
| Making one more file for every topic | Only `AGENTS.md` is auto-read; the rest are dead weight |
| Writing `PROMPTS.md` | Prompt libraries belong in the prompt box or as skills, not a repo file |
| Letting the agent rewrite global rules | Constraints erode over time |

---

## 8. Template — project `AGENTS.md`

```md
# <Project name>

<One line: what this repo is.>

## Commands
- test: `<command>`
- run: `<command>`
- verify a change: `<command>`

## Layout
| Path | Contents |
|---|---|
| `app/` | ... |

## Conventions
- ...

## Gotchas
- ...

## Do not touch
- ...
```

## 9. Template — `PROGRESS.md`

```md
# Progress

## Now
<one or two lines: what works today>

## Decisions
- <decision> — because <reason>

## Unverified
- ...

## Next
- ...
```

---

## 10. The only two things to remember

1. **`AGENTS.md` is loaded for free; everything else must be pointed at.**
2. **Rules go in `AGENTS.md`, state goes in `PROGRESS.md` — and keep both short.**

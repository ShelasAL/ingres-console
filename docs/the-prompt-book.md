# The Prompt Book

### How to ask so you get what you meant

Ten short chapters. No jargon. Read it in fifteen minutes.

---

## Chapter 1 — A prompt is a brief, not a wish

"Make it look better" is a wish. It points at nothing.

"Move the panel to the right edge, 380px wide, black background, and let me drag
it wider" is a brief. It points at something.

The agent cannot read your frustration. It cannot see your screen unless you
show it. It only knows what you type. So a good prompt does three jobs:

1. **Names the target** — what changes
2. **Sets the scope** — what stays untouched
3. **States the finish line** — how we agree it is done

Miss any one of the three, and you get a confident answer to a slightly
different question.

> **Remember:** a prompt is a work order, not a feeling.

---

## Chapter 2 — The four-part skeleton

Almost every good prompt is built from four parts. You do not need all four
every time, but when something goes wrong, one of them was missing.

| Part | Question it answers | Example |
|---|---|---|
| **Goal** | What do I want to exist? | "The panel should open from a tab on the right edge" |
| **Context** | What do you not know? | "It currently sits under the chat box" |
| **Constraints** | What must not change? | "Don't touch the login flow or the tests" |
| **Done when** | How do we stop? | "Tab exists, panel opens, closes with ×" |

### Weak

> make the panel better

### Strong

> **Goal:** move the build-steps panel out of the composer and onto the right
> edge, opened by a small tab.
> **Context:** right now it renders below the chat box and pushes the page down.
> **Constraints:** don't change the ledger logic or the CSS theme tokens.
> **Done when:** a tab on the right edge opens it, `×` closes it, and the page
> layout is unaffected.

Same request. The second one gets built in one round. The first one gets
interpreted.

> **Remember:** four lines of structure beat forty lines of description.

---

## Chapter 3 — Batch, or pay seven times

This is the single biggest money saver, and almost nobody does it.

Every new message re-sends the entire conversation. So a change split across
seven messages is not "seven small asks" — it is seven full re-reads of
everything so far.

Real example from a real session:

> "shrink it" → "move it to the right edge" → "can't close it" → "make it medium
> size" → "match the black background" → "make it resizable" → "move the tab
> higher"

Seven rounds, **27 million tokens** for what was really one round of work.

The same thing batched:

> Fix all of these in one pass: make it compact, move it to the right edge with a
> launcher tab, add a close button, medium height not full screen, black
> background not grey, resizable, tab at about a third of the way down.

One round. Roughly a tenth of the cost. Same result.

> **Remember:** if you catch yourself sending a second message about the same
> screen, you probably should have finished the first one.

---

## Chapter 4 — Show, don't describe

If the problem is visual, send the picture.

"I can't see it" is not a limitation to work around — it is a fact. Describing a
layout in words is slow and lossy. A screenshot is instant and exact.

**Weak:** "the spacing is off and it looks weird"

**Strong:** "attached — the panel is flush against the bottom edge, and the
header text overflows on the right."

Even better, point at what matters:

> "attached. Ignore the colours — the problem is the tab is hidden behind the
> sidebar."

> **Remember:** one screenshot saves three rounds of guessing.

---

## Chapter 5 — Plan first when the ground is unknown

Ask for a plan when any of these is true:

- it touches more than one file
- you cannot explain the change in one sentence
- you are not sure the pieces fit together
- it is going to take more than a few minutes of work

A plan is cheap. A wrong build is not. Reading a plan takes you thirty seconds
and catches the misunderstanding **before** anything is written.

Shortcut: use plan mode. You get a written plan to approve instead of a surprise.

> **Remember:** plan when the ground is unknown. Just build when the path is obvious.

---

## Chapter 6 — The emergency brake

Agents loop. Not often, but when it happens it is expensive — the same failing
tool called a dozen times, each attempt re-sending the whole conversation.

Three phrases that stop it:

| Say this | When |
|---|---|
| **"You're looping — stop."** | You see the same action twice |
| **"Stop after two failures and try a different approach."** | Before starting anything risky |
| **"Stop and explain what you think is actually wrong."** | The fix did not work twice |

The second one is worth putting in your standing rules, because you will not be
watching every second.

> **Remember:** trying the same thing harder is not a strategy.

---

## Chapter 7 — Recipes by use case

### 1. Build something new

> Build `<thing>`. It lives in `<where>`. It must do `<behaviour>`. Do not change
> `<other things>`. Done when `<check>`.

### 2. Fix a bug

Paste the **error**, not a summary of the error.

> **Error:** `<exact message + stack>`
> **Steps:** `<what you did>`
> **Expected:** `<what should happen>`
> **Actually:** `<what happens>`
> Fix the cause, not the symptom. Explain the cause when done.

### 3. Change the UI

> **Attached:** screenshot.
> Make these changes in one round: `<list>`.
> Keep `<what stays>`. Use existing theme tokens — no new colours.

### 4. Refactor safely

> Refactor `<file/area>` for `<reason>`. Behaviour must not change. Show me the
> diff plan first. Run `<tests>` after.

### 5. Research or explain

> Explain `<topic>` for `<my level>`. Use `<format>`. Skip `<what I already know>`.
> Cite sources. Say when you are unsure.

### 6. Write a document

> Write `<document>` for `<audience>`. Purpose: `<why>`. Length: `<how long>`.
> Tone: `<tone>`. Include `<must-haves>`. Do not include `<off-limits>`.

### 7. Resume work in a new session

> Continue `<project>`. Read `PROGRESS.md` and `AGENTS.md`. Next: `<one line>`.

Do not re-paste old prompts. The files are the handoff.

---

## Chapter 8 — Anti-patterns

| Instead of | Say |
|---|---|
| "make it better" | "make X bigger, darker, and 20px further left" |
| "it's broken" | the exact error message |
| seven small messages | one list |
| "do everything" | "do these three things, ignore the rest" |
| "you know what I mean" | say what you mean |
| re-explaining the project | `PROGRESS.md` |
| switching models mid-session | pick one and stay |
| "why isn't this working" (no detail) | what you expected vs what happened |

---

## Chapter 9 — Templates to copy

**Feature**

```
Goal:
Context:
Constraints:
Done when:
```

**Bug**

```
Error: <paste>
Steps to reproduce:
Expected:
Actually:
```

**Batch UI fix**

```
Attached: <screenshot>
Do all of these in one round:
1.
2.
3.
Keep unchanged:
```

**Handoff**

```
Continue <project>. Read PROGRESS.md. Next: <step>.
```

---

## Chapter 10 — The cheat sheet

1. **Brief, not wish.** Target, scope, finish line.
2. **Batch everything.** One round per screen, not one round per symptom.
3. **Show a screenshot** when it is visual.
4. **Plan before building** when you are unsure.
5. **Two failures = stop.** Change approach, do not repeat.
6. **Hand off with files**, not with re-pasted history.

> Write it down, so you don't have to remember it.

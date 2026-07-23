---
name: squad-up
description: Multi-phase agent pipeline for ANY non-trivial work on an existing codebase — bug fixes, new features, refactors, adding tests, performance work, dependency upgrades, and investigations that may end with no code change. Triggers on "squad up [task]", "squad up ULTIMATE [task]", or "squad up fast [task]". Orchestrates Triage → Direction → Plan → Workers → Critic → Verifier → Code Reviewer → Delivery with two approval gates. Never performs git or remote actions; delivery hands the user a ready-to-run commit and PR block.
---

# SQUAD UP - AGENT TEAM SYSTEM

Activate with any variation of: **"squad up [task]"**
Works for **any task on an existing codebase**: fix a bug, add a feature, refactor,
write missing tests, chase a performance problem, do an upgrade, or just investigate
a question. Paste a ticket, an error, or a sentence — whatever you have.

```
squad up <paste a bug report or stack trace>
squad up add CSV export to the reports endpoint
squad up the checkout list is slow when a tenant has 10k rows
squad up write tests for the notification service
squad up why do we call the settings API twice on load?
```

**"squad up" always triggers the full pipeline. No routing, no complexity checks, no shortcuts.** The full phase sequence runs every time. Use escape hatches (`fast mode`, `solo mode`) only when explicitly requested mid-squad.

Without "squad up", respond normally as a standard Claude session.

---

## Trigger variants

| Trigger | Depth per phase | When |
|---|---|---|
| `squad up [task]` | Planner=deep, Workers=standard, Code Reviewer=deep | Default for most work |
| `squad up ULTIMATE [task]` | Every phase at maximum depth | Safety-critical / cross-system / security |
| `squad up fast [task]` | Plan→Workers→Critic→Verifier once, no re-delegation | Time-pressured |

---

## THE NO-GIT RULE (applies to every phase)

**This pipeline never touches git and never touches a remote.** Not a branch, not a commit, not a push, not a PR, not an issue, not a wiki page. This is enforced mechanically by `permissions.deny` in `.claude/settings.json`, not left to agent judgement.

What the squad does: edits the working tree, verifies its own work, and produces a delivery report containing a **ready-to-run commit and PR block** for the user to execute.

What the user does: reviews the diff, then runs those commands themselves.

Read-only git (`status`, `diff`, `log`, `show`, `blame`, `rev-parse`) is allowed and expected — the Verifier and Code Reviewer both need to diff against the plan's base commit.

Do not attempt to work around this, and do not offer to. If a user asks the squad to commit, tell them the block is in the delivery report and they run it.

---

## PHASE 0 - SETUP CHECK, PROMPT CLINIC, DIRECTION

### Step 0a - Stack profile

Read `.claude/stack-profile.md`. It is the single source of truth for this project's commands, test conventions, project type, high-stakes areas, and graph support level. Every downstream phase depends on it.

If it does not exist, run the `squad-setup` skill first, then continue. Do not guess commands — a wrong test command poisons every DoD in the plan.

### Step 0b - Graph gate

Read the **Graph support** field in the stack profile, then:

| Graph support | Behaviour |
|---|---|
| `full` | **Hard gate.** Run `npx gitnexus status`. If no live index, run `npx gitnexus analyze` and wait for it before planning. The squad does not plan without a graph. Impact analysis is mandatory in Phase 4.5. |
| `partial` | Hard gate for lanes touching indexed languages. Lanes on unindexed languages announce degradation and continue. |
| `none` | Gate disabled. State once, at the top of Phase 0: `[no graph support for <language> — blast radius from Read/Grep only]`. The pipeline runs normally; Phase 4.5 substitutes a widened grep sweep for impact analysis. |

The index built here reflects the code **before** any change. That is correct — planning asks "what currently depends on this". Do not re-index during planning.

### Step 0c - Prompt clinic (AskUserQuestion)

Interrogate the prompt itself. Make ONE AskUserQuestion call (max 4 questions), asking only what genuinely changes the plan: scope boundaries, what "done" means concretely, which surface is in scope, whether a behaviour is intended or is the bug. Skip anything the prompt, the repo, or the stack profile already answers. Zero questions is a fine outcome; never pad to fill the call.

### Step 0d - Strategic brief

Output a strategic brief:

- What are we actually solving?
- What is the riskiest assumption?
- What approach will we take?
- Does any part touch **irreversible actions** (sending messages, deleting data, deploying, external API calls that cannot be undone)?
- Does any part consume **untrusted external content** (URLs, uploaded files, third-party APIs, user-submitted data)?

Then ask:

> **"Approve direction? (yes / adjust: [your feedback])"**

→ **STOP. Wait for a response before continuing.**

---

## PHASE 0.5 - TASK SHAPING

**`squad up` takes any kind of work on an existing codebase** — a bug, a new feature,
a refactor, missing tests, a performance problem, an upgrade, a chore, or a question
that may end with no code change at all. The pipeline is the same every time. What
changes is the *preparation* the Planner needs before it can write a useful plan.

Classify the task, then do the matching prep. Announce which shape you picked.

| Shape | Signals | Prep before Phase 1 |
|---|---|---|
| **Bug / regression** | stack trace, error text, "broken", "failing", "returns 500", "wrong result", "used to work", observed-vs-expected | Dispatch `bug-triager`. Its located root cause **replaces the reported symptom** as the problem statement. |
| **Feature / new capability** | "add", "support", "build", "new endpoint/page/command" | Dispatch `code-explorer` on the area it plugs into: where does this belong, what does it reuse, what conventions must it match? Building beside an existing pattern beats inventing one. |
| **Refactor / rename / move** | "clean up", "extract", "rename", "restructure", behaviour preserved | Graph `impact` on every symbol in scope **first** — here the blast radius *is* the entire risk. Never start a rename from grep. |
| **Tests** | "add tests", "cover", "no tests for X" | `code-explorer` for the untested paths and the project's test conventions (from the stack profile). The DoD is which paths are covered, not a coverage number. |
| **Performance** | "slow", "timeout", "optimise", "N+1" | **Measure first.** A lane that optimises without a before-number cannot prove it helped. If no measurement is possible, say so and make that the first lane. |
| **Upgrade / dependency / config** | "bump", "migrate to", "upgrade", version numbers | `code-explorer` for every call site of the changed API. Prep = the compatibility surface. |
| **Investigation / question** | "why does", "how does", "should we", "find out" | `code-explorer` only. This may legitimately end at Phase 5 with findings and **no code change** — that is a successful outcome, not a failed one. |
| **Chore / docs / formatting** | mechanical, low-risk, no behaviour change | No prep. Straight to Phase 1 with a small plan. |

Two rules that apply to every shape:

- **If the prep contradicts the request, the prep wins and you say so.** The triager finding that the "bug" is intended behaviour, or the explorer finding the feature already exists, changes the task. Surface it before planning rather than building the wrong thing.
- **If prep cannot complete** — cannot reproduce, cannot locate, cannot measure — do not guess. Report it, and let the Planner scope an investigation lane instead of a fix lane.

---

## PHASE 1 - PLANNER

Once direction is approved, dispatch the `squad-planner` subagent.

It reads the stack profile, queries the graph for the symbols in scope, and drafts the plan. It plans; it never implements.

Output TWO things:
1. The full plan content displayed in chat for inline review
2. The same content saved as **`SQUAD_PLAN_[task-slug]_[YYYY-MM-DD].md`**

### Plan file format

````markdown
# SQUAD PLAN
**Task:** [original request]
**Date:** [YYYY-MM-DD]
**Status:** AWAITING APPROVAL
**Mode:** SEQUENTIAL / PARALLEL / MIXED
**Base Commit:** [git SHA at plan creation, for regression diffing]
**Root cause:** [from bug-triager, with file:line — omit for non-bug tasks]

---

## Strategic Direction
[2-3 sentences: what we're solving, why this approach, key constraint]

---

## Execution Overview
| Field | Value |
|-------|-------|
| Total Workers | [N] |
| Global Loop Cap | 8 total agent loops max before escalation |
| Est. Handoff Size per Worker | ~1,000-2,000 tokens |
| Irreversible Actions Present | YES / NO |
| Untrusted External Content | YES / NO |
| Graph support | full / partial / none |

---

## Worker Breakdown

### Worker 1 - [Name]
| Field | Detail |
|-------|--------|
| Persona | [e.g. Senior Backend Engineer] |
| Scope | [exactly what they build or produce] |
| Agent Type | [bug-triager / code-explorer / squad-implementer / squad-critic / squad-verifier / squad-code-reviewer / general-purpose] |
| Depends On | [none / Worker N] |
| Execution | [SEQUENTIAL / PARALLEL] |
| Reversible | YES / NO - [if NO, what action and why it cannot be undone] |
| Touches Untrusted Content | YES / NO |
| High-stakes | YES / NO - [which stack-profile area] |

**Definition of Done:**
- [ ] [specific criterion, naming the EXACT command from the stack profile]
- [ ] [specific criterion]

**Output Contract** (max 2,000 tokens):
- Delivers: [what gets handed off]
- Next worker needs: [specific inputs only - no raw dumps]

---

## Execution Trace
| Worker | Status | Loop # | Notes |
|--------|--------|--------|-------|
| Worker 1 | PENDING | - | - |

---

## Risk Flags
| # | Risk | Decision Made |
|---|------|---------------|
| 1 | [ambiguous requirement] | [assumed X] |

---

## Approval
**Approve:** `yes` or `go`
**Adjust:** `adjust worker [N]: [feedback]` / `add worker: [...]` / `remove worker [N]`
**Restart:** `replan`

> No workers spin up until you explicitly approve.
````

After outputting:

> **"HITL GATE: Plan ready. Review the full plan above.**
> **Reply `yes` to spin up workers, or give me adjustments."**

→ **STOP. Do not execute any workers until approved.**

---

## PHASE 2 - WORKERS

Only after gate approval. Dispatch `squad-implementer` (or the plan's named agent) per lane.

### Default Definition of Done

Every worker's DoD includes these baselines plus its task-specific criteria:

**Code-producing workers:**
- [ ] The project's lint and typecheck commands (from the stack profile) pass with zero new errors
- [ ] The project's test command passes with zero new failures
- [ ] **New code requires new tests**, in the framework and layout the stack profile's *Test conventions* names. Do NOT modify or skip existing tests to make new code pass.
- [ ] For changes touching a **High-stakes area** from the profile, also run the profile's integration/e2e command for that area
- [ ] No unrelated modifications outside the worker's scope

**Non-code workers:**
- [ ] Output matches the requested format
- [ ] No invented file paths, symbols, or APIs — every reference verified to exist

### Context isolation (non-negotiable)

- Each worker receives only its lane instruction plus its dependency's handoff contract. Never the full conversation.
- Handoff contracts are hard-capped at ~2,000 tokens. Compress; never dump raw output forward.
- A worker approaching its context limit STOPS and returns partial with `Context Status: PARTIAL`. Never compact mid-task.
- Untrusted external content must carry a `TRUST FLAG` before passing forward.
- Parallel code-writing workers use `isolation: "worktree"` to avoid file conflicts, with a merge step after.

### Verifier independence (non-negotiable)

The agent that produced an artifact never grades it. Phases 3, 4, and 4.5 always run in agents that did not write the code, and `squad-verifier` re-runs every cited command itself rather than trusting pasted output.

### Blast radius during implementation

Use `gitnexus_detect_changes()` to map the working tree's edits onto the graph. It does not need those edits indexed — which matters here, because the squad never commits, so everything is working-tree state.

### End of Phase 2 - re-index

When all lanes are complete and `Graph support` is `full` or `partial`, run `npx gitnexus analyze` (no `--force` — incremental over changed files only, seconds not minutes). The Code Reviewer needs the newly added symbols in the graph.

Query the refreshed index via the **CLI**, not the MCP tools: the MCP server serves the graph it loaded at startup, so a mid-session re-index is not visible to it until Claude Code restarts.

### Irreversibility gate

If a lane includes an action the plan flagged irreversible:

> **"IRREVERSIBILITY GATE: Worker [N] is about to [action]. This cannot be undone.**
> **Confirm to proceed? (yes / cancel / modify: [instructions])"**

→ **STOP until confirmed.**

### Handoff contract

```
HANDOFF CONTRACT (max 2,000 tokens):
-> Completed: [what was built]
-> Outputs: [files changed with paths, key decisions]
-> Assumptions: [anything not explicit in the plan]
-> DoD self-check: [per criterion: command run + raw output tail; NO pass/fail verdicts]
-> Confidence: [0-100]% (capped at 50% without cited command output)
-> Evidence: [exact commands + output excerpts]
-> Context Status: CLEAN / PARTIAL
-> Trust Flag: CLEAN / UNTRUSTED CONTENT PROCESSED
-> Next Worker Needs: [exact inputs only]
```

Update the plan's Execution Trace as each worker completes — that is the checkpoint for `squad resume`.

---

## PHASE 3 - CRITIC

Dispatch `squad-critic` (read-only, no Bash). Receives handoff contracts, not raw outputs.

Judges quality and intent: did this solve the request or did scope drift; is it the simplest thing that works; what would a senior engineer delete; does it hold at production scale; did any DoD get quietly reworded; is the confidence backed by real output.

> If NEEDS WORK → flag for the Verifier with the specific issue. The Critic never re-runs workers and never fixes anything.

---

## PHASE 4 - VERIFIER

Dispatch `squad-verifier`: an independent refuter that re-runs every cited command itself and treats unreproduced evidence as REFUTED.

**Separation from the Critic:** the Verifier checks against the plan ("did we build what we said?"). The Critic checks against quality ("is what we built good?").

### High-stakes second pass

If a lane touched a **High-stakes area** from the stack profile, run a second independent Verifier pass with a different lens (security, reproducibility, edge cases, blast radius). Both must agree before proceeding.

### Escalation

**Global loop cap: 8.** Track total agent loops across all workers and re-runs.

- First failure → re-delegate to that worker with exact fix instructions and the failed criteria
- Second failure on the same worker → ESCALATE:

> **"ESCALATION: Worker [N] failed twice. Loop count: [N] / 8.**
> **Blocking issue: [precise]. Failed DoD criteria: [list].**
> **I need your input to continue."**

- Cap hit → ESCALATE with options: deliver partial / raise cap by 4 / restart narrower / human takeover.

→ **STOP. Wait for direction.**

---

## PHASE 4.5 - INDEPENDENT CODE REVIEWER

Runs after the Verifier passes, whenever workers produced or modified code. Dispatch `squad-code-reviewer`.

This is not the Critic or the Verifier. Those check against the plan and against quality. This checks against reality: does the code actually work, and what else does it touch?

It applies the safety lens matching the project type in the stack profile, and runs impact analysis on every changed symbol (or, at `Graph support: none`, an explicit widened grep sweep, stated as such).

- **Trivial issues** → fixed in place, each logged
- **Substantive issues** → batched into ONE escalation, so the orchestrator spends one loop, not N

If escalating, re-delegate all fixes to the appropriate worker(s) in a single loop.

---

## PHASE 5 - DELIVERY

Output **`SQUAD_DELIVERY_[task-slug]_[YYYY-MM-DD].md`**:

````markdown
# SQUAD DELIVERY REPORT
**Task:** [original request]
**Date:** [YYYY-MM-DD]
**Status:** COMPLETE
**Base commit:** [SHA from the plan]

## What this was
[Task shape, and the starting point in one or two sentences:
 Bug          -> the root cause with file:line, and why the symptom surfaced elsewhere
 Feature      -> what did not exist before, and where it now plugs in
 Refactor     -> what moved or was renamed, and the blast radius that was checked
 Tests        -> which previously untested paths are now covered
 Performance  -> the before number and the after number, same measurement
 Upgrade      -> old version -> new version, and the call sites adapted
 Investigation-> the question asked, and the answer found (code change may be none)]

## What changed
| File | Lines | Change |
|---|---|---|
| path/to/file | 42-58 | [one line] |

## Verification
| Check | Command | Result |
|---|---|---|
| Lint | [exact command] | [output tail] |
| Tests | [exact command] | [output tail] |
| Impact | [graph impact / grep sweep] | [what it found] |

## Quality scorecard
| Check | Result |
|---|---|
| Workers run | [N] |
| Agent loops used | [N] / 8 |
| Critic issues | [N] |
| Verifier refutations | [N] |
| Code review fixes | [N] trivial, [N] substantive |
| Escalations | [N] |

## Open items
- [ ] [anything needing a human decision, or known gaps]

## Ready to ship — you run these
```bash
git checkout -b [suggested-branch-name]
git add -A
git commit -m "[suggested commit message]"
git push -u origin [suggested-branch-name]
gh pr create --title "[suggested title]" --body-file SQUAD_DELIVERY_[slug]_[date].md
```
````

Close the chat turn with a short summary in this shape:

```
[Done: one line — what was fixed / added / changed / found].
[N] files changed — path/to/file.ext:42, path/to/other.ext:17
Verified: [lint command] clean, [test command] [N] passed.
Review the diff, then run the commit/PR block in SQUAD_DELIVERY_[slug]_[date].md.
```

**The squad does not run those commands.** They are for the user.

### Post-delivery memory capture

After a full squad delivery, prompt once:

> **"Anything surprising or non-obvious worth remembering from this? (skip if nothing)"**

Save a response as a project or feedback memory. Skip silently if none. Full deliveries only, not fast mode.

---

## SOLO MODE CHECKLIST

When responding normally (no "squad up") and the response **modifies code**, before calling it done:

1. Run the project's lint/typecheck command on changed files
2. Confirm the change does what was asked
3. No unrelated modifications

Pure Q&A, read-only, and research tasks skip this entirely.

---

## SYSTEM RULES (never break these)

| # | Rule |
|---|------|
| 1 | "squad up" always triggers the full pipeline. No auto-routing, no skipped phases. |
| 2 | **No git mutations, ever.** No branch, commit, push, PR, or issue. Enforced by `permissions.deny`. |
| 3 | Never skip Phase 0 or Phase 1 |
| 4 | Never start workers without plan approval |
| 5 | Every task gets its Phase 0.5 shaping prep before planning |
| 6 | Commands come from `.claude/stack-profile.md`. Never guess one. |
| 7 | Workers run in isolated context — no full history, no raw dumps forward |
| 8 | Handoff contracts capped at ~2,000 tokens |
| 9 | Never compact mid-task — stop and return partial instead |
| 10 | Irreversible actions trigger a gate before execution |
| 11 | Untrusted content is trust-flagged before passing forward |
| 12 | Workers stay in their lane |
| 13 | Escalate after 2 failures on one worker, or 8 total loops |
| 14 | Critic and Verifier are separate agents with separate concerns |
| 15 | The agent that produced an artifact never grades it |
| 16 | High-stakes lanes require two independent Verifier passes |
| 17 | Confidence must cite evidence. No evidence = capped at 50% |
| 18 | Parallel code-writing workers use worktree isolation |
| 19 | Code Reviewer runs on every squad that produces code |
| 20 | Always output `SQUAD_DELIVERY_[slug]_[date].md`, ending with the commit/PR block |
| 21 | A degraded check (no graph) is acceptable; a silently degraded one is not |

---

## ESCAPE HATCHES

| Command | What it does |
|---|---|
| `squad up again` | Full reset, restart from Phase 0 |
| `fast mode` | Plan → Workers → Critic → Verifier once, no re-delegation |
| `solo mode` | Revert to a normal single-model response immediately |
| `replan` | Redo the plan without re-running the direction check |
| `adjust worker [N]: [feedback]` | Modify a worker before approving |
| `add worker: [description]` / `remove worker [N]` | Edit the plan before approving |
| `raise cap` | Extend the loop cap by 4 for this session |
| `re-verify` / `re-verify worker [N]` | Re-run the Verifier against the original DoD |
| `full check` | Critic + Verifier loop again on all workers |
| `deep check` | Ground-truth pass: go back to raw outputs, actually run the code, execute tests, read artifacts line by line |
| `squad resume` | Read the SQUAD_PLAN, check the Execution Trace for the last completed worker, diff for drift since the base commit, re-run only incomplete workers. Flag drift before continuing. |

`skip HITL` does not exist. The two gates and the no-git rule are not bypassable; the deny list enforces the latter regardless of permission mode. For fewer prompts in a personal workflow, edit `.claude/settings.local.json` (gitignored) — never the team file.

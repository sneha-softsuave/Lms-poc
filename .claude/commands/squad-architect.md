---
description: Route a task to the right agent and the right execution shape (solo, single delegated agent, or the full squad pipeline) using a generic decision matrix. Outputs a recommendation and waits for approval; runs nothing by itself.
argument-hint: "[task description]"
---

# /squad-architect

Classify the task below and recommend the WHO (agent or pipeline) and the HOW (execution shape). Do not start any work until the user approves the recommendation.

Task: $ARGUMENTS

## Step 0: ground yourself

Read `.claude/stack-profile.md` — its **Project type**, **High-stakes areas**, and **Commands** determine both the risk classification and the verification command you will name. Do not guess a verification command; if the profile has no matching entry, say so.

## Step 1: classify the task shape

| Shape | Signals |
|---|---|
| Bug / defect report | a stack trace or error, "broken", "failing", "wrong result", "used to work", observed-vs-expected |
| Question / recon | "how does X work", tracing, no code change intended |
| Small scoped change | one function, one endpoint, one component, obvious blast radius |
| Feature | new capability, multiple files, new tests |
| Refactor / rename | behaviour preserved, blast radius is the whole risk |
| Security / access fix | permissions, ownership checks, input validation, secrets |
| Cross-cutting change | touches many modules, or a High-stakes area from the profile |

## Step 2: apply the matrix

| Shape | WHO | HOW |
|---|---|---|
| Question / recon | `code-explorer`, or the `deep-codebase-explorer` skill for cross-module | single delegated agent |
| Bug, cause obvious and local | main session | solo turn-by-turn, then a `squad-verifier` check before declaring done |
| Bug, cause unknown or spans modules | full squad (Phase 0.5 `bug-triager` locates it first) | squad pipeline |
| Small scoped change | main session | solo, plus `squad-verifier` before done |
| Feature | full squad | squad pipeline; sequential lanes unless they touch disjoint files |
| Refactor / rename | `code-explorer` for blast radius, then `squad-implementer` | delegated pair. Use the graph's `rename`, never find-and-replace |
| Security fix, single surface | `squad-implementer` then `squad-verifier` | delegated pair |
| Anything touching a High-stakes area | full squad ULTIMATE | squad pipeline, two independent verifier passes |
| Cross-cutting change | full squad ULTIMATE | squad pipeline |

**Downgrade rules.** Prefer the lightest shape that still gets independent verification. A solo turn is fine when the change is small *and* obvious *and* outside the high-stakes list — but the verifier check is not optional even then, because the agent that wrote the code never grades it.

**Upgrade rules.** If the blast radius is unknown, treat it as large until the graph says otherwise. "I think it's just this one file" is a hypothesis, not a scope.

## Step 3: output the recommendation

```
SQUAD ARCHITECT:
| Task shape: [classification + why]
| WHO: [agent(s) or full squad]
| HOW: [solo / delegated / squad / squad ULTIMATE]
| High-stakes: [YES - which profile area / NO]
| Verification: [the exact command(s) from the stack profile that prove this work, and who runs them]
| Gates expected: [direction gate, plan gate, irreversible-action gate]
```

Then ask: "Run it this way? (yes / adjust)". STOP and wait.

## Invariants

- Every multi-step shape includes an independent `squad-verifier` check; the agent that produced the work never grades itself.
- Never invent a verification command. Use the project's real commands from `.claude/stack-profile.md`.
- No git or remote actions appear in any recommendation — the pipeline does not perform them, and neither does this command.
- "squad up" said by the user always means the full pipeline, regardless of what this matrix would have chosen.

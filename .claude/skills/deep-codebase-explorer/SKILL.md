---
name: deep-codebase-explorer
description: Use when the user asks any cross-module, debugging, refactoring, blast-radius, or incident question about this codebase. Routes between reading files directly, querying the GitNexus knowledge graph, and dispatching read-only sub-agents — picking the lightest approach that fully answers the question, and escalating only for genuinely high-stakes or cross-cutting work. Manual override prefixes: `vanilla:`, `nexus:`, `RLM:`, `ULTIMATE:`.
---

# Deep Codebase Explorer

Routes a code question through the right combination of two grounding layers — the **GitNexus graph** (structural: who calls what, what breaks) and **sub-agent fan-out** (breadth: many independent areas at once) — on top of the baseline, which is simply reading the code.

## Step 1 - Explicit prefix?

If the question starts with one of these, strip it, **announce the mode on line 1 of your response**, and use it. Do not auto-route.

| Prefix | Mode | Behaviour |
|---|---|---|
| `vanilla:` | vanilla | Read/Grep only. No graph, no sub-agents. |
| `nexus:` / `graph only:` | graph | GitNexus only. |
| `RLM:` | sub-agents | Sub-agent fan-out only. |
| `ULTIMATE:` | ULTIMATE | Graph + sub-agents + direct reads. |

## Step 2 - No prefix? Route by question shape

**Default to the lightest mode that fully answers the question.** Most code prompts — a single-symbol lookup, a localised edit, "where is X", "what does this function do" — are answered best by reading the relevant file directly. That IS the grounding. Reserve heavier modes for questions that genuinely span the codebase.

The failure mode to avoid is **over-grounding** — wrapping a one-line answer in an empty graph call and a sub-agent chain reasoning from second-hand notes — at least as much as under-grounding.

| Question shape | Mode |
|---|---|
| Pure chat, opinion, planning, trivial string/typo lookup | **vanilla** |
| Single-symbol factual lookup, localised edit | **read the file directly** |
| "What depends on X" / "what breaks if I change X" / rename safety | **graph** |
| Multi-module trace, debug across systems, dependency mapping | **ULTIMATE** (or **graph** if no synthesis is needed) |
| Broad survey across many independent areas | **sub-agents** |

**Escalate to ULTIMATE — and do not stop early or skip a layer — when the question touches:**

- Anything listed under **High-stakes areas** in `.claude/stack-profile.md`. That list is per-project and authoritative; a records system and a game engine have entirely different critical paths.
- Incident / outage / regression / production behaviour
- Blast radius: `rename`, `refactor`, `what depends on`, `what breaks`, `every code path`, `all callers`, `safe to change`

If the profile has no High-stakes list, default to: auth and permissions, data integrity, irreversible external effects, and production configuration.

## Step 3 - Check what's actually available

Read the **Graph support** field in `.claude/stack-profile.md`:

| Value | Meaning |
|---|---|
| `full` | Graph covers this codebase. Use it for all structural questions. |
| `partial` | Some languages indexed. Use the graph for those; say which parts fall back. |
| `none` | GitNexus cannot parse this stack. Graph modes are unavailable. |

Then confirm the index is live: `npx gitnexus status` reports this repo, or the MCP `list_repos` returns it non-empty.

**Degradation must be loud.** If the graph was the right tool and you could not use it, say so on line 1 of your answer:

```
[no graph index — answering from Read/Grep only]
```

An answer built on a widened grep is acceptable. An answer that silently *looks* like it came from the graph is not — the reader cannot tell how much to trust it.

## Mode behaviours

### graph

Query GitNexus, read code only to confirm a literal value the graph does not carry (a constant, an enum, a response shape). Deterministic and pre-computed; far cheaper than grep for structural questions.

### sub-agents

Fan out read-only sub-agents. Apply the fan-out discipline below.

### ULTIMATE

Graph for structure, direct reads for the load-bearing files, sub-agents for breadth. Surface any disagreement between what the graph says and what the code says **explicitly** — do not silently pick a side. A graph/code disagreement is itself a finding (usually a stale index or dynamic dispatch the parser could not see).

### vanilla

Read/Grep/Bash. No graph, no sub-agents.

---

## Sub-agent fan-out discipline

When dispatching sub-agents (`Explore` for read-only work, `general-purpose` otherwise):

1. **Delegate for breadth, not depth.** Spawn sub-agents when many independent areas need covering in parallel. For files load-bearing to your answer, Read them yourself — you must see the real code (the exact guard, the sentinel value, the boundary condition) to be correct. Never fan out to read one file you could read yourself.
2. **Narrow question, short answer cap.** One focused question per sub-agent, 1-3 sentence cap. A sub-agent returning more than ~5 sentences means your prompt was too broad.
3. **Keep notes, not content.** Write a one-line note per return. Plan the next step from notes, never from raw file content.
4. **Aim for 5-15 calls.** ULTIMATE usually needs *fewer*, because the graph answers structural questions deterministically.
5. **Hard stop at 20.** Beyond that, stop and report partial findings.
6. **Independence only.** Parallel sub-agents must not share state. Ordered or dependent work runs sequentially.
7. **Synthesise from notes.** Never paste raw sub-agent output into your final answer.

## Tool preference

For structural questions, prefer the graph over grep — it is deterministic and pre-computed, where grep is noisy and misses call edges (aliased re-exports, callbacks, interface dispatch).

- `impact` — what depends on X, blast radius, with confidence scores
- `context` — 360-degree view of a symbol: callers, callees, processes it participates in
- `query` — process-grouped semantic search
- `detect_changes` — maps the current working-tree diff onto the graph
- `cypher` — custom traversals (read the schema resource first)

Available as MCP tools (`mcp__gitnexus__*`) and as CLI (`npx gitnexus <cmd>`). Prefer the CLI when the index was rebuilt this session — the MCP server serves the graph it loaded at startup and will not see a fresh re-index until Claude Code restarts.

Fall back to Read/Grep when: the graph cannot answer (runtime behaviour, deployment specifics, error message text, cross-system reasoning), you need the actual code body to confirm something the graph found, or `Graph support` is `none`.

## Red flags — stop and reconsider

- **Never ignore a HIGH or CRITICAL risk warning from impact analysis.** Stop and address it before any edit.
- **Never rename symbols with find-and-replace.** Use `gitnexus rename`, which understands the call graph. Stop if you catch yourself drafting a rename via `sed`, `Edit replace_all`, or `grep -lr`.
- About to edit a symbol without running `impact` first → stop, run it.
- About to fan out a sub-agent to read one file central to your answer → read it yourself.
- About to dump a 500-line file into reasoning when you need one function → read a line range.
- Sub-agent count past 20 → stop, report partial.
- Reaching for grep before the graph on a structural question, with the graph available → stop.
- Routing to ULTIMATE for a single-symbol lookup → over-escalation. Read the file and answer.
- Answering a high-stakes question from memory or a stale note → under-grounding. Read the code.
- Degraded to grep without saying so → fix before answering.
- Forgot to announce the mode on line 1 → fix before continuing.

## Worked example (ULTIMATE)

Q: `ULTIMATE: Trace what happens when a user submits the form on the settings page.`

1. **Structural map:** `npx gitnexus context submitSettings -f src/settings/` → canonical UID, then callers (incoming) and callees (outgoing). The call graph, deterministically, without reading a file.
2. **Blast radius:** `npx gitnexus impact SettingsService.save` → every dependent caller, with confidence scores.
3. **Confirm in code** only where the graph is silent or where you need a literal (a default value, a validation threshold, a response shape). Sub-agent on one function with a 2-sentence cap, or read it yourself if it is central.
4. **Synthesise from notes.** Surface any graph-vs-code disagreement explicitly.

Typical ULTIMATE counts: 2-4 graph calls, 0-3 sub-agent calls, 0 Bash searches, 0-2 Reads.

## Output format

For ULTIMATE, multi-agent, or high-stakes runs, end with an audit trail so the work is not a black box. For light answers, skip it — a one-line answer should not carry a multi-section ledger.

```
---
**Audit trail**
- Mode: <vanilla / graph / sub-agents / ULTIMATE> (note any fall-forward or degradation)
- Graph support: <full / partial / none>
- Files investigated: <list>
- Sub-agent questions: <numbered list>
- Graph calls: <numbered list with exact tool + args>
- Tool counts: { graph: N, Task: N, Bash: N, Read: N }
```

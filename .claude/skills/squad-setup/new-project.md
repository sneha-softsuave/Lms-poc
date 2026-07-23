# Flow: New project

Fresh or near-empty repo. There is little or no source to index yet, so the goal is to wire the stack now so it grows with the code.

Follow the numbered steps. Stop and report on any failure.

## 1. Ensure a git repo

The stack keys off git. If `git rev-parse --is-inside-work-tree` fails, ask the user to confirm, then `git init`. That is a state change, so it prompts. Do not make an initial commit — the squad never commits.

## 2. Confirm the core skills are present

`.claude/skills/squad-up/` and `.claude/skills/deep-codebase-explorer/` came with the copy. Confirm both `SKILL.md` files exist. If not, the `.claude/` copy is incomplete — stop and tell the user to re-copy it.

## 3. Write starter CLAUDE.md

If a root `CLAUDE.md` already exists, do NOT overwrite it — show what you would add and merge. Otherwise create it:

````markdown
# CLAUDE.md

Conventions and quick-start for working in this repo with Claude Code.

## The stack

1. **deep-codebase-explorer** — routes any code question between reading files,
   the GitNexus graph, and sub-agent fan-out. Ask naturally; force a mode with a
   prefix (`vanilla:`, `nexus:`, `RLM:`, `ULTIMATE:`).
2. **GitNexus** — call-graph of the codebase. CLI: `npx gitnexus <command>`.
3. **squad-up** — multi-phase agent pipeline. Trigger with `squad up [task]`,
   including plain-English bug reports.
4. **stack-profile** — `.claude/stack-profile.md` holds this project's commands,
   conventions, project type, and high-stakes areas. Every agent reads it.

The squad never runs git commands. It edits the working tree and hands you a
ready-to-run commit and PR block at delivery.

## Essential commands

<!-- The squad reads this section to know how to lint/test/build.
     Do not leave it blank once commands exist. -->

```bash
# lint    → e.g. npm run lint
# test    → e.g. npm test
# build   → e.g. npm run build
```

## Conventions

- (Add repo conventions here as the team settles them.)
````

Create `AGENTS.md` as a thin mirror only if the user wants parity with other agent runtimes:

```markdown
# AGENTS.md

Mirrors CLAUDE.md for other agent runtimes. The stack lives under `.claude/`;
the skill files are plain markdown and runtime-agnostic. See CLAUDE.md.
```

## 4. Wire GitNexus

Even a small repo benefits from having the graph wired now, so it is live as code lands.

```bash
npx gitnexus analyze     # index (may find little in a fresh repo — fine)
npx gitnexus setup       # wire the MCP server (idempotent; prompts, edits Claude Code config)
npx gitnexus status      # verify
```

If the repo is truly empty, `analyze` may find nothing. Record `Graph support: none` for now and note in the summary that setup should be re-run once real code exists.

**Restart note:** after first-time `setup`, the MCP tools will not see the index until Claude Code restarts. Mention this once.

## 5. Generate the stack profile

Do **Step 3 of `SKILL.md`** and write `.claude/stack-profile.md`. With little code yet, base it on the *intended* stack — ask the user if it is not obvious — and mark command specifics `TODO:` until the tooling is in place.

Still fill in **Project type** and **High-stakes areas** now if the user can answer: those shape how the Code Reviewer behaves from the very first squad run, and neither can be inferred from an empty repo.

## 6. Hand back

Return to the shared **Verify** step in `SKILL.md` and report results, including which fields are still `TODO:`.

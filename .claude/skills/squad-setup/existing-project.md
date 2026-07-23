# Flow: Existing project

The repo already has a real codebase. Goal: index it, wire the graph, capture the repo's real commands, and write the stack profile that every squad agent reads.

Follow the numbered steps. Stop and report on any failure. **Never clobber files the repo already has — merge, don't overwrite.**

## 1. Confirm the core skills are present

`.claude/skills/squad-up/` and `.claude/skills/deep-codebase-explorer/` came with the copy. Confirm both `SKILL.md` files exist; if not, the copy is incomplete — stop.

## 2. Back up an existing CLAUDE.md

If the repo has a root `CLAUDE.md`, copy it to `CLAUDE.md.bak` before going further.

Reason: `gitnexus analyze` writes into `CLAUDE.md` and `AGENTS.md`. Measured on 1.6.9 it *appends* a block fenced by `<!-- gitnexus:start -->` / `<!-- gitnexus:end -->` and leaves surrounding content byte-identical — but that is version-specific behaviour, and a team's `CLAUDE.md` is expensive to lose and impossible to reconstruct. The backup costs nothing and is what confirmed the append behaviour in the first place.

Note also: `analyze` **overwrites everything under `.claude/skills/gitnexus/`** with its own copies, matched to the installed version. That is why this folder does not ship them. Never hand-edit files there; the next `analyze` reverts them.

Delete the backup at the end of setup, once you have confirmed the original content survived.

## 3. Index with GitNexus — BEFORE writing any docs

Order matters. Index first, so that anything `analyze` generates lands *before* our own content rather than on top of it.

```bash
# Build the index. Skip if an index already exists and is current.
npx gitnexus analyze

# Wire the MCP server (idempotent). This edits Claude Code config, not the repo —
# it will prompt, because it is outside the working tree.
npx gitnexus setup

# Verify
npx gitnexus status
```

Indexing a large repo takes roughly a minute. Subsequent runs are incremental.

If `analyze` fails outright, the pipeline still works without the graph — record `Graph support: none` in step 6, report the failure, and continue.

**Restart note:** the MCP server loads its graph at startup. After a first-time `setup`, the MCP tools will not see the index until Claude Code is restarted. Tell the user this once, at the end. The CLI works immediately either way.

## 4. Measure graph support

This is what keeps the strict-graph rule from becoming a portability ceiling. GitNexus does not document which languages it parses, so measure rather than assume.

After `analyze`, check whether the index actually contains symbols for the repo's primary language(s) — `npx gitnexus status` reports symbol and relationship counts, and the repo `context` resource gives per-repo stats.

| Observation | Record as |
|---|---|
| Symbols found for the primary language(s) | `full` |
| Symbols for some languages, none for others (polyglot repo) | `partial` — name which languages are covered |
| Zero symbols, or `analyze` failed | `none` |

This value is read by `squad-up` (whether to hard-gate before planning), `squad-code-reviewer` (impact analysis vs. widened grep sweep), and `deep-codebase-explorer` (whether graph modes are available at all).

## 5. Capture the repo's real commands

The squad reads these to know how to lint, test, and build. Getting them wrong poisons every downstream lane, because the Verifier re-runs exactly what the plan named.

- **If a root `CLAUDE.md` exists:** read it. If it already lists lint/test/build, keep those. Merge, never overwrite. If `analyze` replaced it, restore from `CLAUDE.md.bak` and merge into the restored copy.
- **If none exists:** create one (template in `new-project.md` step 3), then fill **Essential commands** by inspecting the repo:
  - `package.json` scripts, `Makefile` targets, `pyproject.toml` / `tox.ini`, `Cargo.toml`, `go.mod`, `build.gradle`, `composer.json`, `Gemfile`, `justfile`
  - Package manager from the lockfile (`pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `poetry.lock`, `uv.lock`, `Gemfile.lock`, `go.sum`, `Cargo.lock`)
  - Monorepo: note the per-package command *and* the directory to run it from
- **If a command is not discoverable, write it as a TODO and tell the user.** Never invent one.

## 6. Generate the stack profile

Follow **`.claude/skills/squad-setup/stack-profile.md`** and write `.claude/stack-profile.md`. It must include:

- Languages, frameworks, package manager, monorepo layout
- The Commands table (agreeing with `CLAUDE.md` Essential commands)
- Test conventions — framework, where sibling tests go, in what style
- **Project type** — web service / library / CLI / data pipeline / mobile / other. This selects the Code Reviewer's safety lens. A CLI tool must not be reviewed for tenant scoping.
- **Review lens** — the stack-specific traps from the cheatsheet
- **High-stakes areas** — the paths in *this* project where a mistake is expensive. Ask the user if it is not obvious from the code; this is the one field that cannot be inferred reliably, and the planner, verifier, and explorer all key off it.
- **Graph support** — from step 4

Leave `TODO:` markers rather than guessing.

## 7. Hand back

Return to the **Verify** step in `SKILL.md` and report: what was installed, the graph support level, anything left TODO, and the restart note if the MCP server was newly wired.

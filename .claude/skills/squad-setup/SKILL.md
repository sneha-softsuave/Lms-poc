---
name: squad-setup
description: Plug-and-play installer for the squad pipeline, the codebase explorer, and the GitNexus graph in any repository, in any language. Use when the user wants to set up, install, wire up, or integrate the stack — either a brand-new project or an existing codebase. Triggers on "squad setup", "set up the stack", "install squad up", "integrate gitnexus", "wire up the claude stack", "onboard this repo".
---

# Squad Setup — plug-and-play installer

Installs the stack into whatever repo this `.claude/` folder was dropped into:

1. **squad-up** — multi-phase agent pipeline for bugs, features, and refactors (`.claude/skills/squad-up/`)
2. **deep-codebase-explorer** — router over direct reads, the graph, and sub-agent fan-out (`.claude/skills/deep-codebase-explorer/`)
3. **GitNexus** — pre-computed call-graph, wired as an MCP server + CLI
4. **stack-profile** — the one generated file that makes all of the above speak *this* project's stack

The skills and agents ship inside this `.claude/` folder — copying it in is the "plug". This skill is the "play": it indexes the graph, wires the MCP server, measures what the graph can actually parse, and writes the profile.

**Nothing here is language-specific.** The same folder installs into a TypeScript service, a Python CLI, or a Go library. Everything project-specific lands in `.claude/stack-profile.md` and nowhere else. If installing into a second project ever requires editing an agent file, that is a bug — the fact belongs in the profile.

---

## Step 0 — Pick the flow

| Signal | Flow | File |
|---|---|---|
| Repo is empty / near-empty, or being scaffolded from scratch | **New project** | `.claude/skills/squad-setup/new-project.md` |
| Repo already has a real codebase | **Existing project** | `.claude/skills/squad-setup/existing-project.md` |

**Decide without asking:** count source files, excluding `.claude/`, `node_modules/`, `.git/`, `vendor/`, and build directories. Roughly < 5 real source files → new; otherwise → existing. If genuinely ambiguous, ask once, then read the matching flow file and follow it exactly.

Do NOT run both flows.

---

## Step 1 — Preflight (both flows)

Check before doing anything; report any miss and stop if a hard requirement is absent.

- **`git`** — the repo should be a git repo. If not and the user wants one, offer `git init` (ask first — it is a state change).
- **Node.js / `npx`** — required for GitNexus. Check `npx --version`. If missing, tell the user to install Node.js and stop.
- **`bash`** — required by the lint hook. Present on macOS/Linux; on Windows it ships with Git for Windows. Non-fatal if absent: note that the hook will not run.
- **`.claude/skills/squad-up/` and `.claude/skills/deep-codebase-explorer/` present** — if either is missing, the copy is incomplete; tell the user to re-copy the `.claude/` folder.

---

## Step 1.5 — Provision the toolchain, then PROVE the commands run

A command written into the profile but never executed is a guess. The Verifier will
re-run whatever the plan names, so an untested command becomes a false failure on
every future lane. Setup's job is to leave behind commands that **actually work**.

For each command you resolve (lint, typecheck, test):

1. **Run it.**
2. **Read the failure mode**, because they are not the same thing:
   - `command not found`, `No module named X`, `Cannot find module`, `is not recognized`
     → the toolchain is **not provisioned**. Go to step 3.
   - The tool ran and reported findings (lint errors, failing tests), even with a
     non-zero exit → **this is success.** The command works. Record it and move on.
     Do not try to "fix" the project's existing findings; that is not setup's job.
3. **Install the project's own declared dependencies.** Detect the ecosystem from the
   lockfile and run the matching command:

   | Ecosystem | Detected by | Install command |
   |---|---|---|
   | Python + uv | `uv.lock` | `uv pip install -e ".[dev]"` (or `uv sync --extra dev`) |
   | Python + poetry | `poetry.lock` | `poetry install --with dev` |
   | Python + pip | `requirements*.txt` | `python -m pip install -r requirements-dev.txt` |
   | Node + npm | `package-lock.json` | `npm ci` (fall back to `npm install`) |
   | Node + pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
   | Node + yarn | `yarn.lock` | `yarn install --frozen-lockfile` |
   | Go | `go.mod` | `go mod download` |
   | Rust | `Cargo.lock` | `cargo fetch` |
   | Ruby | `Gemfile.lock` | `bundle install` |
   | PHP | `composer.lock` | `composer install` |

   Check the repo's CI workflow first — whatever CI runs to install is the
   authoritative answer for that project, and beats this table.
4. **Re-run the command.** If it now works, record it. If it still cannot run, write
   it as `TODO:` in the profile, and tell the user the exact command that failed and
   the exact error — never leave a silently broken command in the profile.

**Prefer direct invocations over wrappers.** If the project's commands go through
`make`, `just`, or a task runner that is not installed (very common: `make` is absent
on Windows), record the **underlying** command instead, and note the wrapper as the
human shortcut. A wrapper that only some machines have is not a portable command.

### Provisioning boundaries

Installing dependencies the project **already declares** is provisioning — do it
without asking. It only brings the environment up to what the project says it needs.

Everything below changes the machine rather than the project. **Ask first, always:**

- Installing a system tool (Node.js, Python, `make`, Docker, a database)
- Changing the language runtime version, or recreating a virtualenv on a different one
- Adding a dependency the project does not declare
- Any global (`-g`, `--global`, system-wide) install
- Anything requiring administrator/sudo rights

If one of those is the blocker, **stop and report it in the format below**. Do not
work around it by installing something else, and do not bury it in a summary
paragraph — the user has to act on it, so it has to be impossible to miss.

### Required report when setup cannot fix something itself

Print this for each blocker, at the END of setup where it will be read:

```
⚠️  ACTION NEEDED — <one-line what is missing>

  What failed   : <the exact command that was run>
  Error         : <the exact error text, quoted, not paraphrased>
  Why I stopped : <which boundary this crosses — system tool / version change /
                   undeclared dependency / needs admin / needs a running service>

  Fix (run this yourself):
      <the exact command, copy-pasteable>

  Until then    : <precisely what is degraded, and what still works>
```

Rules for that block:

- **Quote the real error.** Never paraphrase it — the user may need to search it.
- **Give one command, not a discussion.** If there are two ways, pick the one that
  matches this project's ecosystem and mention the alternative in a single trailing line.
- **Name the degradation honestly and narrowly.** "Backend tests cannot run, so the
  Verifier cannot confirm backend lanes; the frontend lane is unaffected" — not a vague
  "some things may not work".
- **Never write a command into the profile as if it works when it does not.** Mark it
  `TODO:` and reference this blocker, so the Verifier does not later report a missing
  tool as a code failure.
- If setup completes with zero blockers, say that explicitly too — "all commands
  verified, no action needed" — so silence is never ambiguous.

---

## Step 2 — Run the matching flow

Open the flow file from Step 0 and follow its steps. Both converge on the same graph wiring plus stack profile; they differ in how they treat existing source (index and measure it) versus a fresh repo (wire it now, measure later).

---

## Step 3 — Generate the stack profile (both flows)

This is what makes the squad adapt to the project. Rather than rewriting each agent per project, setup writes ONE file — `.claude/stack-profile.md` — that every agent reads at the start of a lane.

Follow **`.claude/skills/squad-setup/stack-profile.md`**: detect the languages, frameworks, and package manager; resolve the real lint/format/typecheck/test/build commands from the repo's own config; classify the project type; pick the matching review lens; record graph support; and capture high-stakes areas. Multi-stack repos get one block per stack, tagged by directory.

Leave `TODO:` markers for anything undetermined instead of guessing. A guessed test command is worse than a blank one, because the Verifier will run it and report a false result.

---

## Step 4 — Verify (both flows)

The install is done only when all of these hold. Run them and report pass/fail:

- **Every command in the profile has been executed at least once and is known to run.**
  Not "looks plausible" — actually invoked. This is the check that matters most; a
  profile of untested commands makes every future verification unreliable.
- `npx gitnexus status` returns cleanly, or `Graph support: none` is recorded with the reason.
- `.claude/skills/squad-up/SKILL.md` and `.claude/skills/deep-codebase-explorer/SKILL.md` exist.
- `.claude/stack-profile.md` exists with the Commands table filled, plus **Project type**, **High-stakes areas**, and **Graph support** — no leftover `TODO:` on lint/test/build for a project that has real code.
- The lint hook fires: `bash .claude/hooks/lint-changed.sh` runs the profile's lint
  command(s) rather than exiting silently.
- A root `CLAUDE.md` exists with an **Essential commands** section filled in (or flagged TODO), and any pre-existing content is intact.
- `CLAUDE.md.bak` has been compared and removed (existing-project flow).
- Asking a normal code question routes through the explorer; typing `squad up [task]` starts the pipeline.

Finish with a short summary: what was installed, what was provisioned, the graph
support level, whether a Claude Code restart is needed for the MCP server, and the
next command to try (`squad up [a real task]`).

Then, **always**, one of these two — never neither:

- Every `⚠️ ACTION NEEDED` block from Step 1.5, repeated here at the end, or
- `✅ All commands verified — no action needed from you.`

Separately, surface any **pre-existing findings** the verification run turned up
(lint errors, failing tests, type errors that were already in the codebase). These
are not setup failures and must not be presented as such — but the user should hear
about them, because they will otherwise look like the squad broke something on its
first real run. Report them as: "Your project already has N findings: …".

---

## Boundaries

Setup is autonomous within the working tree. Three things reach beyond it and will prompt:

- `git init`, if the repo is not one yet
- `npx gitnexus setup`, which edits Claude Code's own configuration
- Overwriting a file the user already has — `CLAUDE.md`, `AGENTS.md`, an existing `.claude/settings.json`. Show the diff and merge; never clobber.

Setup performs **no other git operations**. No add, no commit, no branch, no push — consistent with the pipeline's no-git rule, and enforced by `permissions.deny` in `.claude/settings.json`. Committing the installed `.claude/` folder is the user's action.

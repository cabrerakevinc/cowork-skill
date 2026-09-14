---
name: extend
description: Adds one piece to a bootstrapped Cowork OS workspace by convention: a workstation ("create a Jira HQ"), a nested unit, a time-bound project inside a workstation ("start a project for the Q4 migration", "archive this project"), a scoped rule ("add a rule for AWS work"), a delegated agent ("create a tester agent"), a local skill, or a tooling table (root or workstation, prefilled from detected tools and the owner's saved defaults), then wires the table rows, memory bullets, and runtime copies, and runs the doctor. Use when the user says "/cowork:extend", "create a workstation", "make an HQ for", "start a project", "archive this project", "add a rule for", "create an agent", "add a skill to", "add tooling", or "sync agents".
---

# /cowork:extend

One request, one addition, built the same way every time. Procedures live in the project's `00_Resources/cowork-os-conventions.md`.

## Steps

1. **Load context.** Read `AGENTS.md`, `MEMORY.md`, and the project's conventions file. Compare its version line with `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/00_Resources/cowork-os-conventions.md`. If the plugin's is newer, use the plugin's copy for the procedure and, at the end, offer `/cowork:bootstrap upgrade` in one line (do not force it). If the project has no conventions file at all, say it is not bootstrapped and suggest `/cowork:bootstrap` (or `adopt`), then stop. If the addition belongs inside a workstation, read that workstation's `CLAUDE.md` and `MEMORY.md` too.
2. **Classify** as one of: workstation, nested unit, project, project-archive, scoped rule, agent, skill, tooling, sync-agents. If unclear, ask with at least 4 options, recommendation first. Do not classify by keyword: "an agent for DoorDash emails" that needs memory and a workflow is a workstation; a persona to hand tasks to with no memory of its own is an agent; work with an end date inside an existing workstation is a project, not a nested unit.
3. **Gather the domain in one round**, asking only what the procedure needs and the project does not already answer:
   - workstation: what routes here and what does not, the primary task's steps, writing rules on top of the root's
   - project: which workstation owns it, the one-paragraph brief (what, for whom, done-when), start date
   - project-archive: the outcome in one line
   - rule: the domain and the imperative one-liners
   - agent: what it does, what it must never do, which tools it needs
   - tooling: see below
   Prefill from MEMORY.md and the repo.
4. **Build exactly per the conventions procedure**, including every wiring step: the table row in the entrypoint or parent CLAUDE.md; the dated Active Projects bullet (root for a workstation, workstation MEMORY.md for a project); `PROJECT.md` from `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/optional/PROJECT.md` for a project; `python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/sync_agents.py" --root <project>` for an agent. Nothing may point at a file that does not exist.
5. **Check parents before writing rules.** A rule already in the root, or in the parent workstation, is referenced ("also follow the root Rules on X"), never repeated.
6. **Run the doctor** (`python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py" --root <project>`). Fix FAILs before reporting.
7. **Report** in plain language: what was created, the row(s) and bullet(s) added, the doctor result. Two to five lines.

## Tooling

Tooling is content only the owner knows, so extend interviews rather than guesses, but it prefills hard:

1. **Detect** from the project: `.mcp.json`, `.claude/settings*.json`, `.codex/config.toml`, `.cursor/mcp.json`, `Makefile`/`justfile`, `cdk.json`, `serverless.yml`, `terraform/`, `package.json` scripts, `.jira`/Rovo or Linear configs, `n8n`/Supabase references, anything the workstation CLAUDE.md already names. Never open secret-shaped files.
2. **Load the owner's defaults** from `~/.cowork/tooling-defaults.md` if it exists (a table in the same shape as `tooling.md`). For every detected tool that has a row there, prefill that row verbatim.
3. **Ask once**: a table of detected tools with prefilled "use when / do not use when" for each, marked which came from defaults, which are recommendations, plus "add a tool not detected". The owner confirms or edits.
4. **Write** `00_Resources/tooling.md` (or `<Name> HQ Resources/tooling.md` when the request names a workstation, or when the tools are specific to one), from `assets/optional/tooling.md`, at most 40 lines, and the References or Resources row. A workstation table never repeats a root row.
5. **Offer to save** any new or edited rows to `~/.cowork/tooling-defaults.md` so the next project starts prefilled. Write there only on a yes. This file is personal and never part of a project.

## Sync-agents

`/cowork:extend sync-agents` runs only step 4's sync script and reports what was written. Use after hand-editing anything in `00_Agents/`.

## Never

Create a workstation, project, agent, or rule the owner did not ask for. Repeat a parent's rule or a root tooling row. Exceed a cap. Leave a table row without a file or a file without a row. Delete an archived project folder. Write generated deliverables into the workspace.

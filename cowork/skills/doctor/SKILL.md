---
name: doctor
description: Audits a Cowork OS workspace (or a whole folder of them) against its 00_Resources/cowork-os-conventions.md, checking size caps, section shape, map rows that point nowhere, orphan files, duplicated rules, rule-shaped lines in memory, project folders, agent sync drift, loose documents, generated output left inside the workspace, secret-shaped strings, and conventions version drift, then proposes fixes without applying them. Never audits nested git repositories or ignored paths. Use when the user says "/cowork:doctor", "audit the workspace", "audit my CLAUDE.md files", "check for bloat", "is anything drifted", "clean up the workstations", "run the doctor", "check all my projects", or right after a workstation, project, rule, agent, or skill was created.
---

# /cowork:doctor

An independent reviewer for the *structure*, never the content of any domain. It never writes to a workspace. It does not nag about optional slots: a workspace with no rules, agents, tooling, or projects is clean if what it does have is right.

## Steps

1. **Locate the workspace root**: the folder holding `AGENTS.md` (or `CLAUDE.md`) plus `MEMORY.md`. On the user's computer, copy `${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py` and `sync_agents.py` to a scratch location there (never into the workspace) and run from it.
2. **Mechanical pass.** `python3 doctor.py --root <workspace>`. For many workspaces under one folder: `--all <parent>`, or `--roots <file>` with one path per line; the fleet table shows conventions version, workstation count, fails, warns, and status per workspace, then details only for the ones that are not clean.
3. **Placement pass (judgment).** Read the entrypoint, root MEMORY.md, and each workstation CLAUDE.md, outermost first. Flag behavior in memory, changeable facts in an entrypoint, a rule restated in a child that the parent already has, explanations longer than two lines inside a rule.
4. **Map quality pass.** For each table row: from the trigger alone, would an agent know whether to load this? "When relevant" is a finding. A file needed every session belongs inline, not in a map.
5. **Token pass.** Sum what loads every session (entrypoint + shim + root MEMORY.md). Past ~250 lines, propose what to demote to a mapped file.
6. **Advisory hints (never counted).** If the workspace references MCP servers or several tools but has no tooling table, or a workstation MEMORY.md carries dated time-bound bullets that look like projects, mention `/cowork:extend tooling` or `/cowork:extend project` in one line each. Hints are not findings.
7. **Report.** Group by check; each finding names the file, what is wrong, the fix. FAIL breaks a convention; WARN needs a human eye; `note:` lines are informational (a newer minor conventions version, a skipped nested repo). A clean result is a good result: two lines and stop.
8. **Fix only on request.** Propose edits; apply when told. Consolidation moves content into a linked resource with an index pointer. MEMORY.md history is archived, never deleted.

## What the script checks

Entrypoint and shim caps; root MEMORY.md sections and bullet caps; every Routing Map row has a workstation and every workstation a row; nested units listed in their parent; workstation CLAUDE.md sections in order; workstation MEMORY.md sections, cap, index caps, Active Projects cap; `Projects/<slug>/PROJECT.md` present, under cap, with Brief / Status / Log, and listed in the workstation memory; Resources rows resolve and every file in a Resources folder is reachable; 00_Resources and 00_Agents reachability; rule file caps and table header; root and workstation tooling caps; agent frontmatter, caps, near-duplicate descriptions, sync drift; rules repeated across files (siblings from one template reported once); rule-shaped memory lines; loose documents and output folders at root; secret-shaped strings in files the structure owns; conventions version (major mismatch warns, minor mismatch is a note) and cap-table agreement with this script.

## Boundaries

Never crossed: nested git repositories (a folder containing `.git`, other than the root), paths matching a root `.coworkignore` (one glob per line), paths ignored by the root `.gitignore`, output folders, and tool folders (`node_modules`, `.venv`, `.claude`, `.codex`). `--include-nested` lifts only the git-repo boundary.

## Flags

`--all PARENT` / `--roots FILE` fleet mode; `--strict` warnings fail too; `--json`; `--include-nested`. Exit 2: not a workspace; suggest `/cowork:bootstrap`.

## Tuning

Caps live in `CAPS` at the top of `scripts/doctor.py` and mirror the cap table in the conventions asset. Change both, bump `CONVENTIONS_VERSION` and the asset's version line: minor for additive changes, major for cap or shape changes. Never change the header text `sync_agents.py` writes into generated files without a major bump; that alone makes every project with agents report drift.

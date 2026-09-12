---
name: doctor
description: Audits a Cowork OS workspace against its 00_Resources/cowork-os-conventions.md, checking size caps, section shape, map rows that point nowhere, orphan files, duplicated rules, rule-shaped lines in memory, agent sync drift, loose documents, generated output left inside the workspace, secret-shaped strings, and conventions version drift, then proposes fixes without applying them. Use when the user says "/cowork:doctor", "audit the workspace", "audit my CLAUDE.md files", "check for bloat", "is anything drifted", "clean up the workstations", "run the doctor", or right after a workstation, rule, agent, or skill was created.
---

# /cowork:doctor

An independent reviewer for the *structure*, never the content of any domain. It never writes to the workspace.

## Steps

1. **Locate the workspace root**: the folder holding `AGENTS.md` (or `CLAUDE.md`) plus `MEMORY.md`. If the workspace is on the user's computer, copy `${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py` and `sync_agents.py` to a scratch location on that computer (never into the workspace) and run there.
2. **Mechanical pass.** Run `python3 doctor.py --root <workspace>`. It checks: entrypoint and shim caps; root MEMORY.md sections and bullet caps; every Routing Map row has a workstation and every workstation has a row; nested units listed in their parent; each workstation CLAUDE.md has Identity / Resources / Workflow / Editorial Rules in order; each workstation MEMORY.md has Contacts / Key Decisions within cap; Resources rows resolve and every file in a Resources folder is reachable; 00_Resources and 00_Agents reachability; rule file caps; agent frontmatter, caps, near-duplicate descriptions, sync drift; rules repeated across files (siblings from one template are reported once); rule-shaped lines in memory; loose documents and output folders at root; secret-shaped strings; the project's conventions version and cap table versus this doctor.
3. **Placement pass (judgment).** Read the entrypoint, root MEMORY.md, and each workstation CLAUDE.md, outermost first. Flag behavior in memory, changeable facts in an entrypoint, a rule restated in a child that the parent already has, explanations longer than two lines inside a rule.
4. **Map quality pass.** For each table row: from the trigger alone, would an agent know whether to load this? "When relevant" is a finding. A file needed every session belongs inline, not in a map.
5. **Token pass.** Sum what loads every session (entrypoint + shim + root MEMORY.md). Past ~250 lines, propose what to demote to a mapped file.
6. **Report.** Group by check; each finding names the file, what is wrong, the fix. FAIL breaks a convention; WARN needs a human eye. A clean result is a good result: two lines and stop. Never manufacture findings.
7. **Fix only on request.** Propose edits; apply when told. Consolidation moves content into a linked resource with an index pointer. MEMORY.md history is archived, never deleted.

## Arguments

- `--strict`: warnings fail too (CI, pre-commit).
- `--json`: machine-readable.
- Exit 2: not a Cowork OS workspace; suggest `/cowork:bootstrap`.

## Tuning

Caps live in the `CAPS` dict at the top of `scripts/doctor.py` and mirror the cap table in the conventions asset. Change both together and bump `CONVENTIONS_VERSION` plus the version line in `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/00_Resources/cowork-os-conventions.md`.

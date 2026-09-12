---
name: extend
description: Adds one piece to a bootstrapped Cowork OS workspace by convention: a workstation ("create a Jira HQ", "new workstation for X"), a nested unit inside one, a scoped rule file ("add a rule for AWS work"), a delegated agent ("create a tester agent"), a local skill, or a tooling row, then wires the table row, memory bullet, and runtime copies, and runs the doctor. Use when the user says "/cowork:extend", "create a workstation", "make an HQ for", "add a rule for", "create an agent", "add a skill to", "add tooling notes", or "sync agents".
---

# /cowork:extend

One request, one addition, built the same way every time. The procedures are in the project's `00_Resources/cowork-os-conventions.md`; read that file first, and fall back to `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/00_Resources/cowork-os-conventions.md` only if the project has none (then say the project is not bootstrapped and suggest `/cowork:bootstrap`).

## Steps

1. **Load context.** Read `AGENTS.md`, `MEMORY.md`, and the conventions file. If the addition belongs inside an existing workstation (a nested unit, a local skill, a workstation-level rule or agent), read that workstation's `CLAUDE.md` and `MEMORY.md` too.
2. **Classify the request** as one of: workstation, nested unit, scoped rule, agent, skill, tooling, sync-agents. If unclear, ask with at least 4 options, recommendation first. Do not classify by keyword alone: "an agent for DoorDash emails" that needs memory and a workflow is a workstation, not an agent; a persona to hand tasks to with no memory of its own is an agent.
3. **Gather the domain in one round.** Ask only what the procedure needs and the project does not already answer: for a workstation, what routes here and what does not, the primary task's steps, and any writing rules; for a rule, the domain and the imperative one-liners; for an agent, what it does, what it must never do, and which tools it needs; for tooling, the tool list and when each is used. Prefill from MEMORY.md and the repo.
4. **Build exactly per the conventions procedure**, including every wiring step: the table row in the entrypoint (or the parent CLAUDE.md for nested units), the dated Active Projects bullet for a new workstation, `sync_agents.py` for an agent (`python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/sync_agents.py" --root <project>`), and nothing that points at a file that does not exist.
5. **Check against parents before writing rules.** A rule already in the root, or in the parent workstation, is referenced ("also follow the root Rules on X"), never repeated.
6. **Run the doctor** (`/cowork:doctor` steps 1 and 2). Fix FAILs before reporting.
7. **Report** in plain language: what was created, the row(s) added, the doctor result. Two to five lines.

## Sync-agents

`/cowork:extend sync-agents` runs only step 4's sync script and reports what was written. Use after hand-editing anything in `00_Agents/`.

## Never

Create a workstation, agent, or rule the owner did not ask for. Repeat a parent's rule. Exceed a cap. Leave a table row without a file or a file without a row. Write generated deliverables into the workspace.

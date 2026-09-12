# Cowork OS conventions

<!-- cowork-os-conventions v1.0 -->

The rules of the *structure*, not the rules of any project. Read this before creating a workstation, rule, agent, skill, or resource. The doctor (`/cowork:doctor`, shipped in the `cowork` plugin) audits against this file; the version line above lets it tell when a project's copy is behind.

## The one mechanism

Everything in this workspace extends the same way: a **table in an entrypoint with a trigger column** pointing at a **folder or file**, plus a procedure for what goes inside. The root entrypoint (`AGENTS.md`, imported by `CLAUDE.md`) has five slots that use it: Rules (scoped), Routing Map (workstations), References (resources), Agents, and, inside every workstation, its own Resources table. Nothing is loaded unless its trigger fires. That is what keeps sessions cheap.

Slots start empty or absent. Create the folder the first time it is needed, never upfront. Whoever uses this workspace decides which slots ever get filled.

## Layout

```
AGENTS.md                      root entrypoint (cap 100 lines)
CLAUDE.md                      @AGENTS.md shim (cap 15 lines)
MEMORY.md                      Active Projects / Core Memory / Archive
00_Resources/                  shared resources, listed in the References table
  cowork-os-conventions.md     this file (the doctor and extend skills live in the cowork plugin, not here)
  rules/<domain>.md            scoped rules, listed in the Rules table (optional)
  tooling.md                   when to use which tool/MCP, one row per tool (optional)
00_Agents/<name>.md            delegated personas, listed in the Agents table (optional)
<Name> HQ/                     one workstation per recurring kind of work
  CLAUDE.md                    Identity / Resources / Workflow / Editorial Rules
  MEMORY.md                    Contacts / Key Decisions (+ an index section if the domain grows per-topic)
  <Name> HQ Resources/         local files, skills, and nested units, listed in that CLAUDE.md's Resources table
```

Workstation folders may nest (a subject under a study HQ, a workspace under a chat HQ). A nested unit has its own CLAUDE.md and MEMORY.md, is created from a template on first use, and is listed in a table in its parent's CLAUDE.md.

## Placement tests

1. Prescribes behavior ("always", "never", "before X do Y")? Root Rules if it applies everywhere, `00_Resources/rules/<domain>.md` if it applies to one domain, a workstation's Editorial Rules if it applies to one workstation. Never MEMORY.md.
2. Fact that can change (contact, status, decision)? MEMORY.md at the level it belongs: root for the person and cross-cutting work, workstation for that domain.
3. Longer than a screen? A file under a Resources folder with a table row. Never inline.
4. Repeatable procedure with steps or scripts? A skill folder `<name>/SKILL.md` inside the owning Resources folder.
5. A persona meant to be *delegated to* rather than routed into? An agent (below).
6. Already stated in a parent file? Reference it ("also follow the root Rules on X"); do not repeat it. A rule that exists in two places is a bug.

## Creating a workstation

Trigger: a kind of work recurs and has its own vocabulary, contacts, or rules. Create `<Name> HQ/` with:

1. `CLAUDE.md`, sections in this order: **Identity** (one paragraph: who you are here, what routes here, what does not), **Resources** (table with header `Resource | Read when...` and no rows yet; an HTML comment under it saying what will land there is fine), **Workflow** (numbered steps for the primary task, start simple), **Editorial Rules** (first line points at the shared writing guidance if one exists, e.g. "Follow my voice principles in 00_Resources (voice-principles.md)"; otherwise "Follow the root Preferences." Then domain-specific rules that layer on top).
2. `MEMORY.md` with header `# <Name> HQ Memory`, `Last updated:`, sections **Contacts** and **Key Decisions**. If the domain will log one entry per topic (research findings, per-case notes), add an index section that keeps one to two dated lines per topic pointing at a file in the Resources folder, and split detail into those files. Flag the index for pruning past 25-30 entries.
3. `<Name> HQ Resources/`, empty.
4. A row in the root Routing Map, and one dated bullet in the root MEMORY.md Active Projects saying the workstation exists and what it is for. Then run the doctor.

Before writing a rule into a workstation CLAUDE.md, check the root. If it already exists there and applies workspace-wide, reference it instead of repeating it.

## Creating a scoped rule

Trigger: a rule applies only when touching one domain (AWS, git, a database, a client). Create `00_Resources/rules/<domain>.md`: a title and numbered imperative one-liners, under 15 lines, no rule longer than 2 lines. If a rule needs a paragraph of explanation, the explanation goes in a resource and the rule links to it. Add a row to the Rules table in `AGENTS.md`. That table's header is `Rule file | Before I...` and each cell completes it (`...run any AWS CLI or CDK command`), the same shape as every other table; the header carries the "before" because rules are read *before acting*, while resources are read *when relevant*. A workstation may carry its own `rules/` inside its Resources folder, listed in its Resources table with the same "before" trigger.

## Creating an agent

Trigger: a persona should be handed a task and work in its own context (a tester, a reviewer, a copywriter), rather than being a mode the main agent loads. Create `00_Agents/<name>.md`:

```
---
name: kebab-name
description: one line, under 200 chars: what it does and what it will not do
tools: Read, Grep, Glob            # optional runtime allowlist; give write tools only if the persona must produce files, and say in the body what it may write
model: sonnet | opus | haiku       # optional hint
---
Identity paragraph (same shape as a workstation Identity), then numbered instructions. Under 60 lines.
First instruction is always: read AGENTS.md and MEMORY.md.
```

On first agent, replace the one-line Agents section in `AGENTS.md` with an optional one-sentence intro and:

```
| Agent | Delegate when... |
|---|---|
| `name` | ...trigger |
```

`00_Agents/` is canonical. `/cowork:extend sync-agents` (the `sync_agents.py` script in the cowork plugin's doctor skill) generates runtime copies into the project: `.claude/agents/<name>.md` (Claude Code reads these directly) and `.codex/agents/<name>.toml` (Codex reads custom agents from `~/.codex/agents/`, so copy or symlink these there; verify field names against current Codex docs). Never edit generated files; the doctor fails on drift. In a runtime without subagents, the main agent adopts the file as a persona, exactly like loading a workstation. A workstation may carry its own `agents/` inside its Resources folder for personas that only make sense there.

## Creating a skill

Trigger: a procedure with steps, templates, or scripts that will be repeated. Create `<owner> Resources/<skill-name>/SKILL.md` (frontmatter `name` and `description`, then steps), with `scripts/` or `assets/` beside it if needed. Owner is the workstation it serves; `00_Resources/` only for skills that operate on the whole workspace. Add a row to the owner's Resources table. Do not register it as an account-level skill unless asked; local stays local.

## Tooling

Trigger: the project has more than one tool or MCP for the same job, or a tool that must be used carefully. Create `00_Resources/tooling.md` as a table `Tool | Use when... | Do not use when...`, one row per tool, under 40 lines, and add a References row "choosing between tools for infra, tickets, docs, or terminals". Tool-specific *rules* (read-only on prod) go in a scoped rule file, not here.

## Size caps

All caps are inclusive: at most this many.

| File | Cap |
|---|---|
| AGENTS.md | 100 lines |
| CLAUDE.md | 15 lines |
| Root MEMORY.md Core Memory | 30 bullets |
| Root MEMORY.md Active Projects | 15 bullets |
| Workstation CLAUDE.md | 120 lines |
| Workstation MEMORY.md | 100 lines; index sections 30 entries |
| 00_Resources/rules/*.md | 15 lines, 2 per rule |
| 00_Agents/*.md | 60 lines |
| Any SKILL.md | 200 lines |
| tooling.md | 40 lines |
| Any frontmatter description | 1 line, 200 chars |

## Reachability

Every file under `00_Resources/`, `00_Agents/`, and every `<Name> HQ Resources/` must be referenced from a table (root or the owning workstation). Every table row must point at something that exists. Every workstation folder must have a Routing Map row; every nested unit must be listed in its parent CLAUDE.md. Index-pattern rows (`findings/<topic-slug>.md`) cover every file under that folder.

## Hygiene

- Generated deliverables never land in this workspace (root Rules). Logging that they were generated does.
- No secret-shaped strings in any file. Point to the vault or env var name.
- `Last updated:` moves on every MEMORY.md edit.
- Run `/cowork:doctor` after creating anything listed above.

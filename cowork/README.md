# cowork

Cowork OS as a plugin. Install once, then every project or folder you work in gets the same lean instruction structure and four commands to keep it honest.

The idea in one paragraph: an agent should read a short entrypoint, a short memory file, and nothing else until a trigger fires. Everything beyond that (a domain's playbook, a set of rules, a persona, a reference doc) sits behind a table row with a trigger column, loaded only when needed. Workstations ("Jira HQ", "YouTube HQ", "Bitbucket HQ") are folders the owner adds as kinds of work recur, each with its own instructions, memory, and resources. The plugin installs the backbone and enforces the conventions; you decide what to build on it.

| Command | What it does |
|---|---|
| `/cowork:bootstrap` | Installs the backbone into the current project: `AGENTS.md` entrypoint, `CLAUDE.md` shim, three-section `MEMORY.md`, `00_Resources/cowork-os-conventions.md`, plus optional root resources (voice principles, briefing template, tooling). Detects what exists, asks one round of questions, shows the tree, merges an existing CLAUDE.md instead of overwriting. Creates no workstations. `upgrade` refreshes the conventions file (one project or a whole folder of them); `adopt` adds only the conventions file to a hand-built Cowork OS. |
| `/cowork:extend` | Adds one thing by convention: a workstation ("create a Jira HQ"), a nested unit, a time-bound project inside a workstation (and archives it later), a scoped rule, a delegated agent, a local skill, or a tooling table (root or workstation, prefilled from detected tools and your saved defaults). Wires rows, memory bullets, runtime agent copies. |
| `/cowork:doctor` | Read-only audit of the structure against the conventions: caps, shape, broken or missing table rows, orphans, duplicated rules, memory misuse, project folders, agent sync drift, secrets, version drift. Fleet mode audits every workspace under a folder in one table. Never looks inside nested git repos or ignored paths. Proposes fixes, applies only on request. |
| `/cowork:end-session` | End-of-session capture: finds corrections, preferences, decisions, and new context from the conversation, proposes where to save each, then commits and pushes if the workspace is a git repo. |

## Install

**Cowork desktop (Claude app):** open the `.plugin` file and accept it. That is the whole install.

**Claude Code (terminal):**

```
/plugin marketplace add kevincabrera/cowork
/plugin install cowork
```

**Sharing it:** send someone the `.plugin` file, or point them at this repo. Nothing in the plugin is tied to the author's projects; the templates speak in the owner's own first person and fill in from an interview.

**Codex, Cursor, other Agent Skills readers:** the `skills/` folder follows the open Agent Skills layout (`skills/<name>/SKILL.md`). Point your skills installer at this repo, or copy `skills/*` into `~/.codex/skills/` (global) or `.agents/skills/` (per project). Verify the exact command against your tool's current docs.

## What a bootstrapped project contains

```
AGENTS.md                                   entrypoint: memory protocol, preferences, rules, trigger tables
CLAUDE.md                                   @AGENTS.md
MEMORY.md                                   Active Projects / Core Memory / Archive
00_Resources/cowork-os-conventions.md       how to extend, size caps, placement tests (versioned)
```

Everything else is added on demand by the owner. A workstation is `<Name> HQ/` with `CLAUDE.md` (Identity / Resources / Workflow / Editorial Rules), `MEMORY.md` (Contacts / Key Decisions), and `<Name> HQ Resources/`, listed in the Routing Map. Rules go in `00_Resources/rules/`, agents in `00_Agents/`, tooling in `00_Resources/tooling.md`, each reached through a table in the entrypoint with a trigger column. Same mechanism everywhere.

The doctor and the extend procedures live in this plugin, not in projects, so updating the plugin updates every project. The conventions file is copied into each project (an agent without the plugin still needs it) and carries a version line the doctor checks.

## Layout of this plugin

```
.claude-plugin/plugin.json
skills/
  bootstrap/SKILL.md, assets/{AGENTS.md, CLAUDE.md, MEMORY.md, 00_Resources/cowork-os-conventions.md}
  extend/SKILL.md
  doctor/SKILL.md, scripts/{doctor.py, sync_agents.py}
  end-session/SKILL.md
```

## Runtime notes

Claude Code does not read `AGENTS.md` on its own; the `@AGENTS.md` import in `CLAUDE.md` is the documented way to load it. Codex reads `AGENTS.md` natively. Generated agent copies land in `.claude/agents/` (Claude Code) and `.codex/agents/` (copy or symlink into `~/.codex/agents/` for Codex; verify field names against current docs).

## Versioning and upgrades

Two version numbers matter. The **plugin** version (this repo) follows semver: patch = tool fixes, minor = new capability, major = a command changes meaning. The **conventions** version, stamped in every project's `00_Resources/cowork-os-conventions.md`, moves separately: a minor bump (1.0 to 1.1) is additive, nothing in an existing project is wrong, and the doctor prints a one-line note; a major bump changes a cap or a file shape, and the doctor warns until the project runs `/cowork:bootstrap upgrade`. Upgrading a project touches the conventions file only, refuses to overwrite one with local edits, and can run across a whole folder of projects at once.

Projects never contain plugin code, so updating the plugin (`/plugin marketplace update cowork-skill`, then reinstall, or a new `.plugin` file) upgrades the doctor and the procedures for every project immediately, without touching any of them.

## Changelog

See `CHANGELOG.md` at the repository root; each GitHub Release carries its section.

## License

MIT. Use it, change it, share it; keep the copyright line.

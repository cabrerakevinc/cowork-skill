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

**Cowork desktop app:** download `cowork.plugin` from the latest GitHub Release and open it in the Claude desktop app.

**Claude Code:**

```
/plugin marketplace add cabrerakevinc/cowork-skill
/plugin install cowork@cowork-skill
```

Update later with `/plugin marketplace update cowork-skill`, then reinstall.

## The four commands

### `/cowork:bootstrap`

Run once per project or folder, from inside it. Detects what is already there (an existing CLAUDE.md, a README, nested repos), describes the project back to you in one paragraph, asks one round of questions with four options each and its recommendation first (purpose, tone, which starter rules to keep, what to do with existing instruction files, which optional resources to seed), shows the tree it will create, and writes the backbone only after you confirm. An existing CLAUDE.md is merged line by line, not overwritten: rules go to the entrypoint, facts to memory, long text to a resource file. Nothing about workstations is decided here.

Two extra modes: `/cowork:bootstrap upgrade` refreshes a project's conventions file to the plugin's current version (or every project under a folder at once) and never overwrites a copy someone edited by hand. `/cowork:bootstrap adopt` adds only the conventions file to a workspace you built by hand before the plugin existed, touching nothing else.

Say: "bootstrap this project", "set up Cowork OS here", "upgrade conventions for everything under ~/Code", "adopt this workspace".

### `/cowork:extend`

The one command for growing a workspace. Tell it what kind of work has started recurring and it builds the right shape, wires the table row and memory bullet, and runs the doctor. It reads the conventions file, so every addition comes out the same way.

- **Workstation**: "create a Jira HQ for anything about our sprint tickets". You get `Jira HQ/CLAUDE.md` (Identity / Resources / Workflow / Editorial Rules), `MEMORY.md` (Contacts / Key Decisions), an empty `Jira HQ Resources/`, a Routing Map row, and a dated Active Projects bullet.
- **Project** inside a workstation: "start a project in Jira HQ for the Q4 board migration, done when all boards are on the new template". You get `Jira HQ/Projects/q4-board-migration/PROJECT.md` (Brief / Status / Log) and a bullet in the workstation memory. Later: "archive the Q4 board migration project, outcome: shipped Oct 28" moves it to the workstation's Archive and leaves the folder in place.
- **Scoped rule**: "add a rule for AWS work: read-only by default, mutating commands need a go, always state profile and region". You get `00_Resources/rules/aws.md` (at most 15 lines) and a row in the Rules table that agents read before touching AWS.
- **Agent**: "create a tester agent that writes Jest tests and never edits application code". You get `00_Agents/tester.md` and generated copies for Claude Code and Codex.
- **Tooling**: "add tooling". It detects the tools your project already uses (MCP configs, manifests, infra files), prefills a use-when / do-not-use-when table from your saved defaults, asks you to confirm once, and writes `00_Resources/tooling.md`. A workstation with its own tools ("add tooling for Automation Lab: n8n, Supabase") gets its own table.
- **Skill**: "add a skill to Research HQ that exports the last answer as an HTML page". You get `Research HQ Resources/export-to-html/SKILL.md` and a Resources row.

### `/cowork:doctor`

A read-only reviewer of the structure. It never changes anything and never nags about optional pieces you chose not to have. It checks that every table row points at a real file and every file has a row, that nothing is over its size cap, that rules aren't repeated across files, that memory holds facts and not rules, that project folders are listed, that agent copies are in sync, that no secret-shaped string sits in a file the structure owns, and that the conventions file is current. It skips nested git repos and anything in `.coworkignore` or `.gitignore`.

Say: "run the doctor", "audit this workspace", "is anything drifted". For many projects at once, point it at the parent folder: "check all my projects under ~/Code" gives one table with a row per workspace.

### `/cowork:end-session`

Run before you close a session. It scans the conversation for corrections you made, preferences you stated, decisions you took, and new facts, proposes where each should be saved (which file, which section, exact wording), writes only what you approve, then commits and pushes if the workspace is a git repo.

## Example: three workstations, one week

A content creator bootstraps a folder called `Studio`. Day one: "create a YouTube HQ for scripting, thumbnails, and publishing checklists" and "create a Sponsors HQ for brand outreach and rate cards". Day three, an editing gig comes in with a deadline: "start a project in YouTube HQ for the Acme launch video, done when the final cut is delivered". Day five: "add tooling for YouTube HQ: Descript, Notion, YouTube Studio". End of each day: `/cowork:end-session`. Each new session starts with the right HQ loaded and the right project's brief and log in front of it, and nothing from Sponsors HQ leaks into YouTube HQ.

An engineer bootstraps a service repo instead: the existing CLAUDE.md gets merged, "add a rule for AWS work" and "create a tester agent" cover the risky parts, and `/cowork:doctor --all ~/Code` once a week keeps forty repos honest.

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

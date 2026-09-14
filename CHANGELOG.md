# Changelog

All notable changes to the `cowork` plugin. Versions follow semver: patch = tool fixes, minor = new capability, major = a command changes meaning. The conventions file installed into projects has its own version (noted per release); a minor conventions bump is additive and needs no action, a major one asks projects to run `/cowork:bootstrap upgrade`.

## [0.2.0] - 2026-09-14

Conventions 1.1 (additive; existing projects need no action).

### Added
- Time-bound projects inside a workstation: `Projects/<slug>/PROJECT.md` (Brief / Status / Log) with an archive step; the doctor checks shape and listing.
- Workstation-scoped `tooling.md`, alongside the root one.
- `/cowork:extend tooling` prefilled from detected tools (MCP configs, manifests, infra files) and the owner's `~/.cowork/tooling-defaults.md`.
- Optional root resources at bootstrap: `voice-principles.md`, `briefing-template.md`, `tooling.md`.
- `/cowork:bootstrap upgrade`: refreshes a project's conventions file to the plugin's version; refuses to overwrite a locally edited copy; works across a whole folder of projects.
- `/cowork:bootstrap adopt`: adds only the conventions file to a hand-built Cowork OS.
- Doctor fleet mode: `--all <parent>` or `--roots <file>` prints one line per workspace.
- Doctor `--include-nested` flag.

### Changed
- The doctor never crosses nested git repositories, `.coworkignore` globs, `.gitignore`d paths, or output folders. Fixes cloned repos inside a workstation being audited as workstations and having their source scanned for secrets.
- A minor conventions version mismatch is now an informational note, not a warning.
- Loose-file check at the root only considers documents (`.md`, `.txt`, `.csv`, office files), not manifests or dotfiles.
- The plugin ships every prior conventions version under `assets/00_Resources/versions/` so upgrade can prove a copy is untouched.

## [0.1.0] - 2026-09-12

Conventions 1.0.

### Added
- `/cowork:bootstrap`: detect, discover, interview, propose, generate the backbone (AGENTS.md, CLAUDE.md shim, MEMORY.md, conventions file). Merges an existing CLAUDE.md.
- `/cowork:extend`: workstation, nested unit, scoped rule, agent, skill, tooling row, sync-agents.
- `/cowork:doctor`: read-only structure audit with caps, reachability, duplicates, placement, agent sync, secrets, conventions drift.
- `/cowork:end-session`: end-of-session capture and git sync (folded in from the standalone skill).

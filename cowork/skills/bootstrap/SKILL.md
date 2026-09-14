---
name: bootstrap
description: Installs the Cowork OS backbone (AGENTS.md entrypoint, CLAUDE.md shim, three-section MEMORY.md, 00_Resources with the conventions file) into the current project or folder after detecting what exists and interviewing the owner; also "upgrade" (refresh the conventions file to the plugin's version, single project or fleet) and "adopt" (add only the conventions file to an existing Cowork OS). Creates no workstations, rules, or agents. Use when the user says "/cowork:bootstrap", "bootstrap this project", "set up Cowork OS here", "scaffold the backbone", "init this workspace", "upgrade conventions", "adopt this workspace", or asks to give a project the CLAUDE.md / MEMORY.md / workstation structure.
---

# /cowork:bootstrap

Three modes. Pick by the argument, or by what Phase 1 finds:

| Mode | When | Writes |
|---|---|---|
| (default) install | no backbone here yet | the four backbone files |
| `upgrade` | backbone exists, conventions copy is older than the plugin's | `00_Resources/cowork-os-conventions.md` only |
| `adopt` | an existing Cowork-style workspace (CLAUDE.md + MEMORY.md + workstations) that predates the plugin | `00_Resources/cowork-os-conventions.md` only, nothing else touched |

Templates live in `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/`: `AGENTS.md`, `CLAUDE.md`, `MEMORY.md`, `00_Resources/cowork-os-conventions.md`, and `optional/` (voice-principles, briefing-template, tooling, PROJECT). Read the conventions file first; it defines what is being installed. If the project lives on the user's computer, do all reads and writes through the device tools.

## Mode: upgrade

1. Read the project's `00_Resources/cowork-os-conventions.md`. Shipped versions live in the plugin: the current one at `assets/00_Resources/cowork-os-conventions.md`, every earlier one at `assets/00_Resources/versions/cowork-os-conventions-vX.Y.md`. Read the version line (`<!-- cowork-os-conventions vX.Y -->`); a file with no version line is a pre-1.0 copy.
2. Classify the project copy by comparing its text, whitespace-normalized and ignoring the version line, with each shipped version: **shipped** (identical to one of them, including the pre-1.0 text of v1.0) or **edited** (matches none).
3. Shipped and older than current: replace with the plugin's copy. Edited: show the differing lines and ask replace / keep and skip / merge by hand; unattended, skip. Never silently overwrite an edited copy.
4. Run the doctor. Report one line: `<old> → <new>`, or the skip reason.

Print the change summary once, not per project (1.0 to 1.1: projects inside workstations, workstation tooling, boundaries paragraph, keeping-current section, caps for PROJECT.md and workstation Active Projects).

**Fleet upgrade**: given a parent folder (or a list of paths), classify every direct child first, show one table (`workspace | current | action`) with actions `replace`, `skip: local edits`, `skip: no conventions file (run adopt)`, `skip: not a workspace`, `up to date`, ask once, then write. Unattended: proceed with every `replace`, never with an edited copy. Finish with `python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py" --all <parent>` and hand back both tables.

## Mode: adopt

For a workspace that already follows the pattern by hand (root CLAUDE.md as entrypoint, MEMORY.md, workstation folders) but has no conventions file. Copy `00_Resources/cowork-os-conventions.md` into place, creating `00_Resources/` if needed, and add a References row for it in the root entrypoint (whatever file that is; do not rename CLAUDE.md to AGENTS.md or add a shim). Nothing else changes. Run the doctor and report; expect warnings about pre-existing drift, which the owner fixes at their own pace.

## Mode: install

### Phase 1: Detect

Look for, and record, without opening anything secret-shaped (`.env*`, `secret_*`, `*.pem`, `credentials*`):

- Entry files: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`, `GEMINI.md`
- Memory or docs: `MEMORY.md`, `README*`, `docs/`, `CONTRIBUTING*`, ADRs
- Existing structure: `00_Resources/`, `00_Agents/`, folders ending in ` HQ` or ` Resources`, `.claude/`, `.codex/`
- Nested git repositories and large data folders (candidates for `.coworkignore`)

If `00_Resources/cowork-os-conventions.md` exists: switch to `upgrade` if it is older than the plugin's, otherwise run the doctor and stop. If `CLAUDE.md` + `MEMORY.md` + at least one workstation folder exist with no conventions file: offer `adopt` first.

### Phase 2: Discover

One paragraph: purpose, kind (code repo, knowledge workspace, mixed), main tools or MCPs in play, owner. Code repo: manifest and top two folder levels. Workspace: top-level folders and any README. Do not dump the tree.

### Phase 3: Interview (one round, AskUserQuestion)

Every question offers at least 4 alternatives; the first is the recommendation. Prefill from Phase 2. Skip anything the project already answers and say why. Unattended: take the first option everywhere, print the assumptions at the top of the proposal, continue.

1. **Purpose.** One sentence for `{{PURPOSE}}`, plus `{{OWNER}}`.
2. **Entrypoint.** `AGENTS.md` + `CLAUDE.md` shim / `CLAUDE.md` only / `AGENTS.md` only / keep an existing file as entrypoint and add the shim.
3. **Preferences.** Tone: professional-conversational / terse technical / formal / casual. Response cap: 300 words / 200 / 500 / none. Recommendations: one strong / a menu / depends / no preference. Extra preference lines to append.
4. **Rules.** The four starter rules: keep / reword / drop each. Then: add none / owner's lines / lines merged from existing files / both. Cap 10.
5. **Existing instruction files.** Each: merge into the backbone / keep and add a References row / leave untouched / delete after merging (only if the owner says so).
6. **Memory seeding.** One Active Projects bullet describing current work / empty / Core Memory facts from the README / both.
7. **Optional root resources** (multi-select): none / `voice-principles.md` (ask for one short sample of the owner's writing to seed it) / `briefing-template.md` / `tooling.md` (prefilled from detected tools) / `00_Resources/rules/` with one starter rule / `00_Agents/` with one agent. Each chosen item is created from `assets/optional/` with its References row. Workstations and projects are never pre-created.
8. **Boundaries.** If Phase 1 found nested repos or data folders: add a `.coworkignore` listing them / rely on `.gitignore` / nothing. The doctor skips nested git repos regardless.

### Phase 4: Propose

Print the tree marked NEW / MERGE / KEEP. For each MERGE, list every line of the existing file and where it goes, per the placement tests: behavior → `AGENTS.md` Rules; changeable fact → `MEMORY.md` (Active Projects if ongoing work, else Core Memory); longer than a screen → a `00_Resources/` file with a References row; Claude-specific → stays in `CLAUDE.md` under the import (*Claude-specific* means slash commands, hooks, `.claude/` settings, MCP server names, subagent behavior).

Attended: wait for one confirmation. Unattended: the printed proposal is the record; proceed.

### Phase 5: Generate

1. Copy the four asset files (`00_Resources/cowork-os-conventions.md` keeps its folder). Never copy `assets/optional/` wholesale or `assets/00_Resources/versions/` at all; those stay in the plugin. Fill `{{PURPOSE}}`, `{{OWNER}}`, `{{DATE}}`, `{{FIRST_CORE_FACT}}`; edit Preferences and Rules per the interview. Delete every `bootstrap:` comment; keep every `slot:` comment. Create the Q7 items chosen, filling or deleting every placeholder in them.
2. Existing `CLAUDE.md`: Claude-specific lines stay under `@AGENTS.md`; everything else moves per Phase 4; the merged file is at most 15 lines. Other entry files become a one-line pointer to `AGENTS.md`.
3. Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py" --root <project>`. Fix FAILs. For WARNs, fix what the conventions clearly call for and report the rest; never move project files (manifests, source, dotfiles) to satisfy the doctor.
4. Report in plain language: created, merged (line by line), left alone, doctor result, and what to do next: "`/cowork:extend` when a kind of work recurs, `/cowork:doctor` after any structural change, `/cowork:end-session` before closing".

## Never

Open a secret-shaped file. Delete or overwrite without the Phase 4 listing (or, in upgrade, without the local-edits check). Leave a `{{PLACEHOLDER}}` or `bootstrap:` comment behind. Create a workstation or project on the owner's behalf. Exceed a cap on day one. Commit unless asked.

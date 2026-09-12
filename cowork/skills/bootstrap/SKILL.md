---
name: bootstrap
description: Installs the Cowork OS backbone (AGENTS.md entrypoint, CLAUDE.md shim, three-section MEMORY.md, 00_Resources with the conventions file) into the current project or folder after detecting what exists and interviewing the owner. Creates no workstations, rules, or agents. Use when the user says "/cowork:bootstrap", "bootstrap this project", "set up Cowork OS here", "scaffold the backbone", "init this workspace", or asks to give a new or existing project the CLAUDE.md / MEMORY.md / workstation structure.
---

# /cowork:bootstrap

Install the backbone only. The owner adds workstations, rules, agents, skills, and tooling later with `/cowork:extend`; some projects never need any of them.

Templates live in `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/assets/`: `AGENTS.md`, `CLAUDE.md`, `MEMORY.md`, `00_Resources/cowork-os-conventions.md`. Read the conventions file first; it defines what is being installed.

Works for a code repository, a knowledge workspace (a Cowork folder), or a mix. Same backbone, different interview answers. If the project lives on the user's computer, do all reads and writes through the device tools.

## Phase 1: Detect

Look for, and record, without opening anything secret-shaped (`.env*`, `secret_*`, `*.pem`, `credentials*`):

- Entry files: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`, `GEMINI.md`
- Memory or docs: `MEMORY.md`, `README*`, `docs/`, `CONTRIBUTING*`, ADRs
- Existing structure: `00_Resources/`, `00_Agents/`, folders ending in ` HQ` or ` Resources`, `.claude/`, `.codex/`

If `00_Resources/cowork-os-conventions.md` already exists, the project is bootstrapped: say so, run `/cowork:doctor` instead, and stop.

## Phase 2: Discover

Read only enough to describe the project in one paragraph: purpose, kind (code repo, knowledge workspace, mixed), main tools or MCPs in play, owner. Code repo: the manifest and the top two folder levels. Workspace: top-level folders and any README. Do not dump the tree.

## Phase 3: Interview (one round, AskUserQuestion)

Every question offers at least 4 alternatives; the first is the recommendation. Prefill from Phase 2. Skip anything the project already answers and say why. If nobody answers (scheduled or unattended run), take the first option everywhere, print the assumptions at the top of the proposal, and continue.

1. **Purpose.** One sentence for the `{{PURPOSE}}` line at the top of `AGENTS.md`, plus `{{OWNER}}`.
2. **Entrypoint.** `AGENTS.md` + `CLAUDE.md` shim / `CLAUDE.md` only / `AGENTS.md` only / keep an existing file as the entrypoint and add the shim.
3. **Preferences.** Tone: professional-conversational / terse technical / formal / casual. Response cap: 300 words / 200 / 500 / none. Recommendations: one strong recommendation / a menu / depends on the ask / no preference. Extra preference lines to append.
4. **Rules.** Show the four starter rules from the template. Each: keep / reword / drop. Then: add none / add the owner's lines / add lines merged from existing instruction files / both. Cap 10.
5. **Existing instruction files.** Each: merge into the backbone / keep the file and add a References row pointing at it / leave untouched and unreferenced / delete after merging (only if the owner says so).
6. **Memory seeding.** One Active Projects bullet describing current work / empty / Core Memory facts from the README / both.
7. **Optional slots to pre-create.** None / `00_Resources/rules/` with one starter rule / `00_Agents/` with one agent / `00_Resources/tooling.md`. Workstations are never pre-created.

## Phase 4: Propose

Print the tree marked NEW / MERGE / KEEP. For each MERGE, list every line of the existing file and where it goes, using the placement tests in the conventions file: behavior → `AGENTS.md` Rules; changeable fact → `MEMORY.md` (Active Projects if ongoing work, Core Memory otherwise); longer than a screen → a file in `00_Resources/` with a References row; Claude-specific → stays in `CLAUDE.md` under the import. *Claude-specific* means slash commands, hooks, `.claude/` settings, MCP server names, subagent behavior.

Attended: wait for one confirmation. Unattended: the printed proposal is the record; proceed.

## Phase 5: Generate

1. Copy the four asset files into the project root (`00_Resources/cowork-os-conventions.md` keeps its folder). Fill `{{PURPOSE}}`, `{{OWNER}}`, `{{DATE}}`, `{{FIRST_CORE_FACT}}`; edit Preferences and Rules per the interview. Delete every `bootstrap:` comment; keep every `slot:` comment.
2. Existing `CLAUDE.md`: Claude-specific lines stay under `@AGENTS.md`; everything else moves per Phase 4; the merged file is at most 15 lines. Other entry files become a one-line pointer to `AGENTS.md`.
3. Create only what question 7 chose, following the matching "Creating ..." procedure in the conventions file.
4. Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/doctor/scripts/doctor.py" --root <project>`. Fix FAILs. For WARNs, fix what the conventions clearly call for and report the rest; never move project files (manifests, source, dotfiles) to satisfy the doctor.
5. Report in plain language: created, merged (line by line), left alone, doctor result, and what to do next: "`/cowork:extend` when a kind of work recurs, `/cowork:doctor` after any structural change, `/cowork:end-session` before closing".

## Never

Open a secret-shaped file. Delete or overwrite without the Phase 4 listing. Leave a `{{PLACEHOLDER}}` or `bootstrap:` comment behind. Create a workstation on the owner's behalf. Exceed a cap in the conventions file on day one. Commit unless asked.

# AGENTS.md

This workspace: {{PURPOSE}}. Owner: {{OWNER}}.

<!-- Root entrypoint for every agent working here. Keep under 100 lines. -->
<!-- Structure and procedures: 00_Resources/cowork-os-conventions.md. Read it before creating anything new. -->

## Memory System

- At the start of every session, read MEMORY.md before responding. Use what you find to inform your work. Don't announce what you found, just be informed by it.
- MEMORY.md has three sections: **Active Projects** (current work), **Core Memory** (durable facts about me, my work, and my preferences), and **Archive** (finished projects and outdated entries, kept for history instead of deleted).
- "Add this to active projects" adds a bullet under Active Projects. "Archive this" moves the entry to Archive tagged with today's date. "Remember this" writes to Core Memory immediately and confirms.
- Update the "Last updated" date at the top of MEMORY.md any time you edit it.
- **Where things go:** two tests. (1) Does it prescribe behavior ("always", "never", "before X do Y")? Then it belongs in this file or a rules file, never in MEMORY.md. (2) Is it a fact about the world that could change (contacts, status, decisions)? Then MEMORY.md: Active Projects if ongoing, Core Memory if durable. When unsure, suggest a location and ask.
- If Core Memory passes ~20-30 entries, flag it and suggest a pruning pass. Memory is read into every session; keep it lean.

## Preferences

<!-- bootstrap: adjust these from interview Q3, then delete this comment -->
- Write in a professional but conversational tone. If it sounds like a corporate memo, rewrite it.
- Keep responses concise, under 300 words unless I ask for more detail.
- Use bullet points for lists, but write explanations in natural paragraphs.
- Give me one strong recommendation. Don't give me 3 options unless I ask for alternatives.

## Rules

<!-- bootstrap: keep, drop, or add from interview Q4 (cap 10), then delete this comment -->
- Always ask clarifying questions before starting a complex task. When asking, offer at least 4 alternatives I can choose from, with your recommendation first.
- If you're not sure about something, say so. Don't guess.
- Never print, log, or store credentials, tokens, or keys. Do not open paths matching `secret_*`, `.env*`, `*.pem`, or `credentials*`.
- **Never write generated deliverables into this workspace.** It is an instructions/reference workspace, not output storage. Deliver generated files as a chat download; I'll save them where they belong. Original source material I upload stays put; logging what was generated and decided in MEMORY.md still happens.

Scoped rules (read the file before acting in that domain; each file is at most 15 lines):

| Rule file | Before I... |
|---|---|

<!-- slot: add rows as rule files are created under 00_Resources/rules/ -->

## Routing Map

When I start a task, check this table to decide which workstation folder to load. Add a row every time a workstation is created (procedure in cowork-os-conventions.md).

| Workstation | Route here when I... |
|---|---|

<!-- slot: no workstations yet; create the first one when a recurring kind of work shows up -->

## References

Files in 00_Resources. Load only when the trigger fires.

| Resource | Read when... |
|---|---|
| cowork-os-conventions.md | Creating or changing a workstation, rule, agent, skill, or resource; deciding where something belongs |

<!-- slot: typical next rows are voice-principles.md (writing any content on my behalf), briefing-template.md (any status update, research answer, or summary), personal-info.md (bios, forms), tooling.md (choosing between tools/MCPs) -->

## Housekeeping

This workspace follows the Cowork OS conventions (see References). With the `cowork` plugin installed: `/cowork:extend` creates a workstation, rule, agent, skill, or tooling row by convention; `/cowork:doctor` audits the structure, run it after creating anything; `/cowork:end-session` captures what this session taught you and syncs git. Without the plugin, follow the conventions file by hand.

## Agents

No delegated agents yet. Personas meant to be delegated to (a tester, a reviewer, a copywriter) live in `00_Agents/` once created; see "Creating an agent" in the conventions file, which also gives the table that replaces this line.

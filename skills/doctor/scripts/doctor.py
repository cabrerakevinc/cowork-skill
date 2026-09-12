#!/usr/bin/env python3
"""Cowork OS doctor: mechanical checks against 00_Resources/cowork-os-conventions.md.

Shipped in the cowork plugin (skills/doctor/scripts). Run against any bootstrapped project.
Usage: python3 doctor.py [--root PATH] [--json] [--strict]
Exit 0 clean, 1 findings (FAIL, or WARN with --strict), 2 not a Cowork OS workspace.

Only checks what can be counted or matched. Judgment checks live in SKILL.md.
Read-only: never writes to the workspace.
"""
import argparse
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

CAPS = {
    "entry": 100, "shim": 15, "core_bullets": 30, "active_bullets": 15,
    "ws_claude": 120, "ws_memory": 100, "index_entries": 30,
    "rule_lines": 15, "rule_item": 2, "agent_lines": 60, "skill_lines": 200,
    "tooling_lines": 40, "desc_chars": 200,
}
SIMILARITY = 0.85
CONVENTIONS_VERSION = "1.0"  # bump together with assets/00_Resources/cowork-os-conventions.md
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "_to_delete", ".claude", ".codex"}
SKIP_FILES = {".DS_Store", ".gitignore", ".gitattributes"}
TEXT_EXT = {".md", ".toml", ".json", ".yml", ".yaml", ".txt", ".py", ".sh", ".csv", ".html"}
DOC_EXT = {".md", ".txt", ".csv", ".xlsx", ".docx", ".pdf", ".html", ".pptx"}
# conventions cap table row label (lowercased substring) -> CAPS key
CONVENTIONS_ROWS = {
    "agents.md": "entry", "claude.md": "shim", "core memory": "core_bullets", "active projects": "active_bullets",
    "workstation claude.md": "ws_claude", "workstation memory.md": "ws_memory", "rules/*.md": "rule_lines",
    "00_agents/*.md": "agent_lines", "skill.md": "skill_lines", "tooling.md": "tooling_lines", "description": "desc_chars",
}
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "private key"),
    (r"(?i)\bbearer\s+[a-z0-9\-_\.=]{20,}", "bearer token"),
    (r"(?i)\b(password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{6,}", "password literal"),
    (r"(?i)[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s]+@", "credentials in URL"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack token"),
]
BEHAVIOR_RE = re.compile(r"\b(always|never|must not|do not|don't)\b", re.I)


class Report:
    def __init__(self):
        self.findings = []

    def add(self, sev, check, path, msg):
        self.findings.append({"severity": sev, "check": check, "path": str(path), "msg": msg})

    def fail(self, *a):
        self.add("FAIL", *a)

    def warn(self, *a):
        self.add("WARN", *a)


def lines(p: Path):
    return p.read_text(errors="ignore").splitlines()


def rel(root, p):
    try:
        return str(Path(p).resolve().relative_to(root))
    except ValueError:
        return str(p)


def sections(text):
    """Return ordered list of (title, body) for '## ' headings."""
    out, title, buf = [], None, []
    for l in text.splitlines():
        m = re.match(r"^##\s+(.*)", l)
        if m:
            if title is not None:
                out.append((title, "\n".join(buf)))
            title, buf = m.group(1).strip().strip("*"), []
        elif title is not None:
            buf.append(l)
    if title is not None:
        out.append((title, "\n".join(buf)))
    return out


def bullets(body):
    return [l for l in body.splitlines() if re.match(r"\s*[-*]\s+\S", l)]


def table_rows(text):
    """First cell of every markdown table body row, stripped of backticks/bold."""
    rows, pending_header = [], None
    for l in text.splitlines():
        if not l.strip().startswith("|"):
            if pending_header is not None:
                rows.append(pending_header)
            pending_header = None
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            pending_header = None  # separator: the previous row was a header, already dropped
            continue
        if pending_header is not None:
            rows.append(pending_header)
        first = cells[0].strip("`*")
        pending_header = (first, cells[1] if len(cells) > 1 else "") if first else None
    if pending_header is not None:
        rows.append(pending_header)
    return rows


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for l in m.group(1).splitlines():
        if ":" in l:
            k, v = l.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def backtick_paths(text):
    return set(re.findall(r"`([^`\n]+)`", text))


def resolve(row, bases):
    """Resolve a table cell to a path. Returns (path_or_None, pattern_prefix_or_None)."""
    row = re.sub(r"\s*\((?!no folder)[^)]*\)\s*$", "", row).strip()  # drop trailing "(local skill)" style notes
    row = row.rstrip("/")
    pattern = None
    if "<" in row:
        pattern = row.split("<", 1)[0].rstrip("/")
    target = pattern if pattern is not None else row
    for b in bases:
        p = (b / target) if target else b
        if p.exists():
            return p, pattern
    return None, pattern


def is_external(row):
    """Rows that point outside the workspace (originals on disk, URLs) are not checked."""
    return row.startswith(("/", "~", "http://", "https://")) or "(no folder" in row


def is_placeholder(s):
    return s.startswith("[") or s.startswith("{{") or s.lower().startswith("<!--")


def is_outputs_dir(name):
    return "output" in name.lower() or name.lower() in ("_to_delete", "deliverables", "exports")


# ---------------------------------------------------------------- checks

def check_root(root, r, entry):
    n = len(lines(entry))
    if n > CAPS["entry"]:
        r.fail("size", rel(root, entry), f"{n} lines, cap {CAPS['entry']}")
    shim = root / "CLAUDE.md"
    if entry.name == "AGENTS.md":
        if not shim.exists():
            r.warn("layout", "CLAUDE.md", "no CLAUDE.md shim; Claude Code will not load AGENTS.md")
        else:
            t = shim.read_text()
            if "@AGENTS.md" not in t:
                r.fail("layout", "CLAUDE.md", "must import @AGENTS.md when AGENTS.md is the entrypoint")
            if len(t.splitlines()) > CAPS["shim"]:
                r.fail("size", "CLAUDE.md", f"{len(t.splitlines())} lines, cap {CAPS['shim']} for a shim")
    # loose doc-like root files and output dumps (project manifests, source, dotfiles are ignored)
    for p in root.iterdir():
        if p.is_file() and p.suffix.lower() in DOC_EXT and not p.name.startswith(".") and p.name not in ("AGENTS.md", "CLAUDE.md", "MEMORY.md", "README.md", "BOOTSTRAP_PROMPT.md", "CONTRIBUTING.md", "CHANGELOG.md"):
            r.warn("hygiene", p.name, "loose document at root; move to 00_Resources (and map it) or out of the workspace")
        elif p.is_dir() and is_outputs_dir(p.name) and p.name not in SKIP_DIRS:
            n = sum(1 for _ in p.rglob("*") if _.is_file())
            if n:
                r.warn("hygiene", p.name + "/", f"{n} generated file(s) inside the workspace; root Rules say deliverables go out as downloads. Not scanned further.")


def check_memory(root, r, p, level, ws_claude_text=None):
    if not p.exists():
        r.fail("layout", rel(root, p), "MEMORY.md missing")
        return
    text = p.read_text()
    if not re.search(r"^\**Last updated:?\**\s*:?\s*\S", text, re.M | re.I):
        r.warn("hygiene", rel(root, p), "no 'Last updated:' line")
    secs = dict(sections(text))
    if level == "root":
        for key, cap in (("Active Projects", CAPS["active_bullets"]), ("Core Memory", CAPS["core_bullets"])):
            if key not in secs:
                r.fail("layout", rel(root, p), f"section '{key}' missing")
            elif len(bullets(secs[key])) > cap:
                r.fail("size", rel(root, p), f"{key} has {len(bullets(secs[key]))} bullets, cap {cap}")
        if "Archive" not in secs:
            r.fail("layout", rel(root, p), "section 'Archive' missing")
    else:
        n = len(text.splitlines())
        if n > CAPS["ws_memory"]:
            r.fail("size", rel(root, p), f"{n} lines, cap {CAPS['ws_memory']}; split detail into Resources files with an index")
        for key in ("Contacts", "Key Decisions"):
            if key not in secs:
                r.warn("layout", rel(root, p), f"section '{key}' missing")
        for title, body in secs.items():
            if "index" in title.lower() and len(bullets(body)) > CAPS["index_entries"]:
                r.fail("size", rel(root, p), f"'{title}' has {len(bullets(body))} entries, cap {CAPS['index_entries']}; prune")
    # behavior in memory
    for title, body in secs.items():
        if title in ("Key Decisions",):
            continue  # decisions legitimately explain reasoning
        for b in bullets(body):
            if BEHAVIOR_RE.search(b) and not re.search(r"\b(say|tell|when I say)\b", b, re.I):
                r.warn("placement", rel(root, p), f"rule-shaped line in memory, belongs in an entrypoint or rules file: '{b.strip()[:80]}'")


def workstations(root):
    """Every dir (not root) containing CLAUDE.md, with its nearest ancestor that has one."""
    found = []
    for p in root.rglob("CLAUDE.md"):
        d = p.parent
        parts = d.relative_to(root).parts
        if d == root or any(part in SKIP_DIRS for part in parts) or (parts and is_outputs_dir(parts[0])):
            continue
        parent = d.parent
        while parent != root and not (parent / "CLAUDE.md").exists():
            parent = parent.parent
        found.append((d, parent))
    return sorted(found, key=lambda x: str(x[0]))


def check_routing(root, r, entry, wss):
    text = entry.read_text()
    secs = dict(sections(text))
    routing = secs.get("Routing Map", "")
    rows = [(a, b) for a, b in table_rows(routing) if not is_placeholder(a)]
    top_level = {d.name: d for d, parent in wss if parent == root}
    for name, trigger in rows:
        match = top_level.get(name) or next((d for n, d in top_level.items() if n.lower() == name.lower()), None)
        if not match:
            if (root / name).is_dir():
                r.fail("layout", name, "Routing Map row points at a folder with no CLAUDE.md")
            else:
                r.fail("reachability", "Routing Map", f"row '{name}' points at a folder that does not exist")
        if not trigger.strip() or trigger.strip() in ("...", "..."):
            r.warn("map-quality", "Routing Map", f"row '{name}' has an empty trigger")
    listed = {n.lower() for n, _ in rows}
    for name, d in top_level.items():
        if name.lower() not in listed:
            r.fail("reachability", rel(root, d), "workstation folder has no Routing Map row")
    # nested units must be listed in their parent CLAUDE.md
    for d, parent in wss:
        if parent == root:
            continue
        ptext = (parent / "CLAUDE.md").read_text().lower()
        if d.name.lower() not in ptext:
            r.fail("reachability", rel(root, d), f"nested unit not mentioned in {rel(root, parent / 'CLAUDE.md')}")


def check_workstation(root, r, d, parent):
    c = d / "CLAUDE.md"
    text = c.read_text()
    n = len(text.splitlines())
    if n > CAPS["ws_claude"]:
        r.fail("size", rel(root, c), f"{n} lines, cap {CAPS['ws_claude']}; move detail into Resources files")
    titles = [t for t, _ in sections(text)]
    required = ["Identity", "Resources", "Workflow", "Editorial Rules"]
    missing = [t for t in required if not any(t.lower() in x.lower() for x in titles)]
    if missing:
        r.warn("layout", rel(root, c), f"missing section(s): {', '.join(missing)}")
    else:
        idx = [next(i for i, x in enumerate(titles) if t.lower() in x.lower()) for t in required]
        if idx != sorted(idx):
            r.warn("layout", rel(root, c), f"sections out of order; expected {' / '.join(required)}")
    check_memory(root, r, d / "MEMORY.md", "workstation")
    # resources folders
    res_dirs = [x for x in d.iterdir() if x.is_dir() and x.name.lower().endswith("resources")]
    if not res_dirs:
        r.warn("layout", rel(root, d), "no '<Name> Resources/' folder (conventions say create it, even empty)")
    secs = dict(sections(text))
    res_rows = [(a, b) for a, b in table_rows(secs.get("Resources", "")) if not is_placeholder(a)]
    mem_text = (d / "MEMORY.md").read_text() if (d / "MEMORY.md").exists() else ""
    mentioned = backtick_paths(text) | backtick_paths(mem_text) | set(re.findall(r"→\s*`?([^\s`]+)`?", mem_text))
    covered = set()
    bases = res_dirs + [d, root]
    for cell, trig in res_rows:
        if is_external(cell):
            continue
        p, pattern = resolve(cell, bases)
        if p is None:
            if pattern is not None:
                r.warn("reachability", rel(root, c), f"Resources row '{cell}' names a folder that does not exist yet")
            else:
                r.fail("reachability", rel(root, c), f"Resources row '{cell}' points at nothing that exists")
        else:
            covered.add(p.resolve())
            if p.name == "SKILL.md":
                mentioned |= backtick_paths(p.read_text(errors="ignore"))
        if trig and not trig.strip():
            r.warn("map-quality", rel(root, c), f"Resources row '{cell}' has an empty trigger")
    # orphan files inside resources folders
    nested_dirs = {x for x, p in workstations(root) if p == d}
    for rd in res_dirs:
        for f in rd.rglob("*"):
            if not f.is_file() or f.name in SKIP_FILES or f.name == "README.md":
                continue
            if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
                continue
            fr = f.resolve()
            ok = fr in covered or any(str(fr).startswith(str(cv) + "/") or (cv.name == "SKILL.md" and str(fr).startswith(str(cv.parent) + "/")) for cv in covered)
            if not ok:
                relf = str(f.relative_to(rd)).replace("\\", "/")
                ok = any(relf in m or f.name in m for m in mentioned)
            if not ok and any(str(fr).startswith(str(nd.resolve()) + "/") for nd in nested_dirs):
                ok = True
            if not ok:
                r.fail("reachability", rel(root, f), f"orphan: no Resources row or mention in {rel(root, c)} / MEMORY.md")
    # skill caps
    for s in d.rglob("SKILL.md"):
        if len(lines(s)) > CAPS["skill_lines"]:
            r.fail("size", rel(root, s), f"{len(lines(s))} lines, cap {CAPS['skill_lines']}")


def check_shared(root, r, entry):
    text = entry.read_text()
    secs = dict(sections(text))
    res = root / "00_Resources"
    if not res.is_dir():
        r.fail("layout", "00_Resources", "missing")
        return
    ref_rows = [a for a, _ in table_rows(secs.get("References", "")) if not is_placeholder(a)]
    rule_rows = [a for a, _ in table_rows(secs.get("Rules", "")) if not is_placeholder(a)]
    mentioned = backtick_paths(text)
    covered = set()
    for cell in ref_rows + rule_rows:
        p, _ = resolve(cell, [res, res / "rules", root])
        if p is None:
            r.fail("reachability", rel(root, entry), f"table row '{cell}' points at nothing that exists")
        else:
            covered.add(p.resolve())
    for f in res.rglob("*"):
        if not f.is_file() or f.name in SKIP_FILES or f.name == "README.md" or f.name == "cowork-os-conventions.md":
            continue
        if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
            continue
        fr = f.resolve()
        ok = fr in covered or any(str(fr).startswith(str(cv.parent) + "/") for cv in covered if cv.name == "SKILL.md")
        if not ok:
            relf = str(f.relative_to(res))
            ok = any(relf in m or f.name in m for m in mentioned)
        if not ok:
            r.fail("reachability", rel(root, f), "orphan: no References/Rules row in the entrypoint")
    # rules caps
    for p in (res / "rules").glob("*.md") if (res / "rules").is_dir() else []:
        n = len(lines(p))
        if n > CAPS["rule_lines"]:
            r.fail("size", rel(root, p), f"{n} lines, cap {CAPS['rule_lines']}")
        for it in re.split(r"\n(?=\d+\. )", p.read_text()):
            if re.match(r"\d+\. ", it) and len(it.strip().splitlines()) > CAPS["rule_item"]:
                r.warn("size", rel(root, p), f"rule '{it.strip().splitlines()[0][:50]}' spans {len(it.strip().splitlines())} lines, cap {CAPS['rule_item']}")
        if p.resolve() not in covered:
            r.fail("reachability", rel(root, p), "rule file not in the Rules table (rules must be mapped with a 'before' trigger)")
    rules_sec = secs.get("Rules", "")
    if "|" in rules_sec and not re.search(r"^\|[^|\n]*\|\s*before", rules_sec, re.I | re.M):
        r.warn("map-quality", rel(root, entry), "Rules table header should read 'Rule file | Before I...' so every row is read before acting")
    tool = res / "tooling.md"
    if tool.exists() and len(lines(tool)) > CAPS["tooling_lines"]:
        r.fail("size", rel(root, tool), f"{len(lines(tool))} lines, cap {CAPS['tooling_lines']}")
    for s in res.rglob("SKILL.md"):
        if len(lines(s)) > CAPS["skill_lines"]:
            r.fail("size", rel(root, s), f"{len(lines(s))} lines, cap {CAPS['skill_lines']}")


def check_agents(root, r, entry):
    ag = root / "00_Agents"
    text = entry.read_text()
    secs = dict(sections(text))
    rows = {a for a, _ in table_rows(secs.get("Agents", "")) if not is_placeholder(a)}
    if not ag.is_dir():
        if rows:
            r.fail("reachability", rel(root, entry), "Agents table has rows but 00_Agents/ does not exist")
        return
    names = set()
    for p in sorted(ag.glob("*.md")):
        n = len(lines(p))
        if n > CAPS["agent_lines"]:
            r.fail("size", rel(root, p), f"{n} lines, cap {CAPS['agent_lines']}")
        fm = frontmatter(p.read_text())
        if not fm:
            r.fail("layout", rel(root, p), "no YAML frontmatter (name, description)")
            continue
        name = fm.get("name", p.stem)
        names.add(name)
        desc = fm.get("description", "")
        if not desc:
            r.fail("hygiene", rel(root, p), "no description")
        elif len(desc) > CAPS["desc_chars"]:
            r.fail("size", rel(root, p), f"description {len(desc)} chars, cap {CAPS['desc_chars']}")
        if name not in rows and p.stem not in rows:
            r.fail("reachability", rel(root, p), "agent not listed in the Agents table")
    for row in rows:
        if row not in names and not (ag / f"{row}.md").exists():
            r.fail("reachability", rel(root, entry), f"Agents row '{row}' has no file in 00_Agents/")
    # description near-duplicates
    items = [(p, frontmatter(p.read_text()).get("description", "")) for p in ag.glob("*.md")]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][1] and SequenceMatcher(None, items[i][1].lower(), items[j][1].lower()).ratio() >= SIMILARITY:
                r.warn("duplicate", rel(root, items[i][0]), f"description nearly identical to {rel(root, items[j][0])}")
    # sync
    script = Path(__file__).resolve().parent / "sync_agents.py"
    if script.exists() and ((root / ".claude" / "agents").exists() or (root / ".codex" / "agents").exists()):
        res = subprocess.run([sys.executable, str(script), "--root", str(root), "--check"], capture_output=True, text=True)
        if res.returncode != 0:
            for l in res.stdout.splitlines():
                kind, _, path = l.partition(" ")
                r.fail("sync", path, f"{kind.lower()}: run sync_agents.py")


def check_duplicate_rules(root, r, entry, wss):
    """Imperative bullets repeated across entrypoint and workstation CLAUDE.md files."""
    seen = []  # (normalized, path)
    def collect(p, sec_filter):
        for title, body in sections(p.read_text()):
            if not any(s in title for s in sec_filter):
                continue
            for b in bullets(body) + [l for l in body.splitlines() if re.match(r"\s*\d+\.\s", l)]:
                t = re.sub(r"^\s*([-*]|\d+\.)\s*", "", b)
                t = re.sub(r"\*\*|`", "", t)
                key = re.sub(r"[^a-z ]", "", t.lower()).strip()
                if len(key) >= 30:
                    yield key, t
    sources = [(entry, ("Rules", "Preferences"))] + [(d / "CLAUDE.md", ("Editorial Rules", "Workflow")) for d, _ in wss]
    groups = {}  # first occurrence key -> (raw, first path, [other paths])
    for p, filt in sources:
        for key, raw in collect(p, filt):
            hit = None
            for k2, p2 in seen:
                if p2 == p:
                    continue
                short, long_ = sorted((key, k2), key=len)
                if SequenceMatcher(None, key, k2).ratio() >= SIMILARITY or (len(short) >= 40 and long_.startswith(short)):
                    hit = k2
                    break
            if hit is not None:
                groups.setdefault(hit, (raw, dict(seen)[hit], []))[2].append(p)
            seen.append((key, p))
    for key, (raw, first, others) in groups.items():
        others = sorted({rel(root, o) for o in others})
        if len(others) >= 3 and len({Path(o).parent.parent for o in others}) == 1:
            r.warn("duplicate", rel(root, first), f"same rule repeated in {len(others)} sibling files under {Path(others[0]).parent.parent}: '{raw[:60]}'. Promote to the parent CLAUDE.md and reference it.")
        else:
            for o in others:
                r.warn("duplicate", o, f"repeats a rule in {rel(root, first)}: '{raw[:70]}'")


def check_conventions_caps(root, r):
    """The cap table in the conventions file must agree with CAPS here."""
    conv = root / "00_Resources" / "cowork-os-conventions.md"
    if not conv.exists():
        r.warn("layout", "00_Resources/cowork-os-conventions.md", "conventions file missing; the doctor has nothing to audit against")
        return
    ctext = conv.read_text()
    m = re.search(r"cowork-os-conventions v(\d+(?:\.\d+)*)", ctext)
    if not m:
        r.warn("drift", "00_Resources/cowork-os-conventions.md", f"no version line; the plugin ships v{CONVENTIONS_VERSION}. Re-copy it from /cowork:bootstrap assets")
    elif m.group(1) != CONVENTIONS_VERSION:
        r.warn("drift", "00_Resources/cowork-os-conventions.md", f"is v{m.group(1)}, plugin doctor expects v{CONVENTIONS_VERSION}; update the project's copy")
    secs = dict(sections(ctext))
    body = next((b for t, b in secs.items() if "cap" in t.lower()), "")
    for label, capcell in table_rows(body):
        key = next((k for sub, k in sorted(CONVENTIONS_ROWS.items(), key=lambda x: -len(x[0])) if sub in label.lower()), None)
        if not key:
            continue
        nums = [int(n) for n in re.findall(r"\d+", capcell)]
        if nums and CAPS[key] not in nums:
            r.warn("drift", "00_Resources/cowork-os-conventions.md", f"cap for '{label}' says {capcell.strip()} but doctor.py uses {CAPS[key]}; change both together")


def check_secrets(root, r):
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT:
            continue
        parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in parts) or is_outputs_dir(parts[0]):
            continue
        rp = rel(root, p)
        if rp.startswith("00_Resources/rules/"):
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, text):
                r.fail("secrets", rp, f"contains something shaped like a {label}")
                break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    entry = root / "AGENTS.md" if (root / "AGENTS.md").exists() else root / "CLAUDE.md"
    if not entry.exists() or not (root / "MEMORY.md").exists():
        print("not a Cowork OS workspace (need AGENTS.md or CLAUDE.md, plus MEMORY.md). Run /cowork:bootstrap first.")
        return 2
    r = Report()
    wss = workstations(root)
    check_root(root, r, entry)
    check_memory(root, r, root / "MEMORY.md", "root")
    check_routing(root, r, entry, wss)
    for d, parent in wss:
        check_workstation(root, r, d, parent)
    check_shared(root, r, entry)
    check_agents(root, r, entry)
    check_duplicate_rules(root, r, entry, wss)
    check_conventions_caps(root, r)
    check_secrets(root, r)
    if a.json:
        print(json.dumps(r.findings, indent=2))
    else:
        if not r.findings:
            print(f"doctor: clean ({len(wss)} workstation(s), entrypoint {entry.name})")
        for f in sorted(r.findings, key=lambda x: (x["severity"] != "FAIL", x["check"], x["path"])):
            print(f"{f['severity']} [{f['check']}] {f['path']}: {f['msg']}")
        fails = sum(1 for f in r.findings if f["severity"] == "FAIL")
        if r.findings:
            print(f"\n{fails} fail, {len(r.findings) - fails} warn, {len(wss)} workstation(s) scanned")
    bad = any(f["severity"] == "FAIL" or a.strict for f in r.findings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Cowork OS doctor: mechanical checks against 00_Resources/cowork-os-conventions.md.

Shipped in the cowork plugin (skills/doctor/scripts). Read-only: never writes to a workspace.

Usage:
  python3 doctor.py [--root PATH] [--json] [--strict] [--include-nested]
  python3 doctor.py --all PARENT_DIR          fleet: every direct child that is a workspace
  python3 doctor.py --roots LIST_FILE         fleet: one workspace path per line

Exit 0 clean, 1 findings (FAIL, or WARN with --strict), 2 not a Cowork OS workspace.
Fleet mode exits 1 if any workspace has findings.

Boundaries the doctor never crosses: nested git repositories (a folder with .git, other than
the root), paths matched by .coworkignore at the root (one glob per line), paths ignored by the
root .gitignore, output folders, and SKIP_DIRS. --include-nested lifts the git-repo boundary only.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

CONVENTIONS_VERSION = "1.1"  # bump together with assets/00_Resources/cowork-os-conventions.md
CAPS = {
    "entry": 100, "shim": 15, "core_bullets": 30, "active_bullets": 15,
    "ws_claude": 120, "ws_memory": 100, "index_entries": 30, "ws_active_projects": 10,
    "rule_lines": 15, "rule_item": 2, "agent_lines": 60, "skill_lines": 200,
    "tooling_lines": 40, "desc_chars": 200, "project_md": 60,
}
SIMILARITY = 0.85
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "_to_delete", ".claude", ".codex", ".idea", ".vscode"}
SKIP_FILES = {".DS_Store", ".gitignore", ".gitattributes", ".coworkignore"}
TEXT_EXT = {".md", ".toml", ".json", ".yml", ".yaml", ".txt", ".py", ".sh", ".csv", ".html"}
DOC_EXT = {".md", ".txt", ".csv", ".xlsx", ".docx", ".pdf", ".html", ".pptx"}
ROOT_OK_FILES = {"AGENTS.md", "CLAUDE.md", "MEMORY.md", "README.md", "BOOTSTRAP_PROMPT.md", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE", "LICENSE.md"}
CONVENTIONS_ROWS = {  # cap-table row label (lowercased substring) -> CAPS key
    "agents.md": "entry", "claude.md": "shim", "core memory": "core_bullets", "active projects": "active_bullets",
    "workstation claude.md": "ws_claude", "workstation memory.md": "ws_memory", "rules/*.md": "rule_lines",
    "00_agents/*.md": "agent_lines", "skill.md": "skill_lines", "tooling.md": "tooling_lines", "description": "desc_chars",
    "project.md": "project_md", "workstation active projects": "ws_active_projects",
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


# ---------------------------------------------------------------- report

class Report:
    def __init__(self):
        self.findings = []
        self.notes = []  # informational, never counted

    def add(self, sev, check, path, msg):
        self.findings.append({"severity": sev, "check": check, "path": str(path), "msg": msg})

    def fail(self, *a):
        self.add("FAIL", *a)

    def warn(self, *a):
        self.add("WARN", *a)

    def note(self, msg):
        self.notes.append(msg)

    @property
    def fails(self):
        return sum(1 for f in self.findings if f["severity"] == "FAIL")

    @property
    def warns(self):
        return len(self.findings) - self.fails


# ---------------------------------------------------------------- boundaries

class Excluder:
    """Decides which paths the doctor may look at. One instance per workspace."""

    def __init__(self, root: Path, include_nested=False):
        self.root = root
        self.include_nested = include_nested
        self.globs = []
        for name in (".coworkignore", ".gitignore"):
            f = root / name
            if f.exists():
                for line in f.read_text(errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("!"):
                        continue
                    self.globs.append(line)

    def is_nested_repo(self, p: Path) -> bool:
        return p != self.root and p.is_dir() and (p / ".git").exists()

    def ignored_by_globs(self, p: Path) -> bool:
        try:
            relp = p.relative_to(self.root).as_posix()
        except ValueError:
            return False
        is_dir = p.is_dir()
        for g in self.globs:
            dir_only = g.endswith("/")
            g2 = g.rstrip("/")
            if dir_only and not is_dir:
                # a dir-only pattern still covers files inside that dir
                if any(fnmatch.fnmatch(part, g2.lstrip("/")) for part in Path(relp).parts[:-1]):
                    return True
                continue
            if "/" in g2.strip("/"):
                anchored = g2.lstrip("/")
                if fnmatch.fnmatch(relp, anchored) or fnmatch.fnmatch(relp, anchored + "/*") or relp.startswith(anchored.rstrip("*") + "/"):
                    return True
            else:
                if any(fnmatch.fnmatch(part, g2) for part in Path(relp).parts):
                    return True
        return False

    def excluded(self, p: Path) -> bool:
        """True if p (file or dir) must not be inspected or descended into."""
        try:
            parts = p.relative_to(self.root).parts
        except ValueError:
            return True
        if not parts:
            return False
        if any(part in SKIP_DIRS for part in parts):
            return True
        if is_outputs_dir(parts[0]):
            return True
        if not self.include_nested:
            cur = self.root
            for part in parts:
                cur = cur / part
                if self.is_nested_repo(cur):
                    return True
        return self.ignored_by_globs(p)

    def walk(self, start: Path):
        """Yield every file under start that is not excluded, pruning excluded dirs."""
        if self.excluded(start) and start != self.root:
            return
        for dirpath, dirnames, filenames in os.walk(start):
            d = Path(dirpath)
            keep = []
            for name in dirnames:
                if not self.excluded(d / name):
                    keep.append(name)
            dirnames[:] = keep
            for name in filenames:
                f = d / name
                if name in SKIP_FILES or self.excluded(f):
                    continue
                yield f


# ---------------------------------------------------------------- helpers

def lines(p: Path):
    return p.read_text(errors="ignore").splitlines()


def rel(root, p):
    try:
        return str(Path(p).resolve().relative_to(root))
    except ValueError:
        return str(p)


def sections(text):
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
    rows, pending = [], None
    for l in text.splitlines():
        if not l.strip().startswith("|"):
            if pending is not None:
                rows.append(pending)
            pending = None
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            pending = None  # separator: previous row was the header
            continue
        if pending is not None:
            rows.append(pending)
        first = cells[0].strip("`*")
        pending = (first, cells[1] if len(cells) > 1 else "") if first else None
    if pending is not None:
        rows.append(pending)
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
    row = re.sub(r"\s*\((?!no folder)[^)]*\)\s*$", "", row).strip().rstrip("/")
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
    return row.startswith(("/", "~", "http://", "https://")) or "(no folder" in row


def is_placeholder(s):
    return s.startswith("[") or s.startswith("{{") or s.lower().startswith("<!--")


def is_outputs_dir(name):
    return "output" in name.lower() or name.lower() in ("_to_delete", "deliverables", "exports")


def is_workspace(p: Path) -> bool:
    return p.is_dir() and (p / "MEMORY.md").exists() and ((p / "AGENTS.md").exists() or (p / "CLAUDE.md").exists())


# ---------------------------------------------------------------- checks

def check_root(root, r, entry, ex):
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
    for p in root.iterdir():
        if p.is_file() and p.suffix.lower() in DOC_EXT and not p.name.startswith(".") and p.name not in ROOT_OK_FILES and not ex.ignored_by_globs(p):
            r.warn("hygiene", p.name, "loose document at root; move to 00_Resources (and map it) or out of the workspace")
        elif p.is_dir() and is_outputs_dir(p.name) and p.name not in SKIP_DIRS:
            n = sum(1 for _ in p.rglob("*") if _.is_file())
            if n:
                r.warn("hygiene", p.name + "/", f"{n} generated file(s) inside the workspace; root Rules say deliverables go out as downloads. Not scanned further.")
        elif p.is_dir() and ex.is_nested_repo(p) and not ex.include_nested:
            r.note(f"{p.name}/ is its own git repository; skipped (use --include-nested to audit it)")


def check_memory(root, r, p, level):
    if not p.exists():
        r.fail("layout", rel(root, p), "MEMORY.md missing")
        return {}
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
            if title.strip().lower() == "active projects" and len(bullets(body)) > CAPS["ws_active_projects"]:
                r.fail("size", rel(root, p), f"Active Projects has {len(bullets(body))} entries, cap {CAPS['ws_active_projects']}; archive finished ones")
    for title, body in secs.items():
        if title in ("Key Decisions",):
            continue
        for b in bullets(body):
            if BEHAVIOR_RE.search(b) and not re.search(r"\b(say|tell|when I say)\b", b, re.I):
                r.warn("placement", rel(root, p), f"rule-shaped line in memory, belongs in an entrypoint or rules file: '{b.strip()[:80]}'")
    return secs


def workstations(root, ex):
    """Every non-excluded dir (not root) containing CLAUDE.md, with its nearest ancestor that has one."""
    found = []
    for f in ex.walk(root):
        if f.name != "CLAUDE.md" or f.parent == root:
            continue
        d = f.parent
        parent = d.parent
        while parent != root and not (parent / "CLAUDE.md").exists():
            parent = parent.parent
        found.append((d, parent))
    return sorted(found, key=lambda x: str(x[0]))


def check_routing(root, r, entry, wss):
    text = entry.read_text()
    secs = dict(sections(text))
    rows = [(a, b) for a, b in table_rows(secs.get("Routing Map", "")) if not is_placeholder(a)]
    top_level = {d.name: d for d, parent in wss if parent == root}
    for name, trigger in rows:
        match = top_level.get(name) or next((d for n, d in top_level.items() if n.lower() == name.lower()), None)
        if not match:
            if (root / name).is_dir():
                r.fail("layout", name, "Routing Map row points at a folder with no CLAUDE.md")
            else:
                r.fail("reachability", "Routing Map", f"row '{name}' points at a folder that does not exist")
        if not trigger.strip() or trigger.strip() == "...":
            r.warn("map-quality", "Routing Map", f"row '{name}' has an empty trigger")
    listed = {n.lower() for n, _ in rows}
    for name, d in top_level.items():
        if name.lower() not in listed:
            r.fail("reachability", rel(root, d), "workstation folder has no Routing Map row")
    for d, parent in wss:
        if parent == root:
            continue
        if d.name.lower() not in (parent / "CLAUDE.md").read_text().lower():
            r.fail("reachability", rel(root, d), f"nested unit not mentioned in {rel(root, parent / 'CLAUDE.md')}")


def check_projects(root, r, d, mem_secs):
    """<Workstation>/Projects/<slug>/PROJECT.md, each listed in the workstation MEMORY.md (Active Projects or Archive)."""
    pdir = d / "Projects"
    if not pdir.is_dir():
        return
    mem_text = " ".join(mem_secs.get(k, "") for k in ("Active Projects", "Archive")).lower()
    for proj in sorted(x for x in pdir.iterdir() if x.is_dir() and not x.name.startswith(".")):
        pm = proj / "PROJECT.md"
        if not pm.exists():
            r.fail("layout", rel(root, proj), "project folder has no PROJECT.md (Brief / Status / Log)")
        else:
            n = len(lines(pm))
            if n > CAPS["project_md"]:
                r.fail("size", rel(root, pm), f"{n} lines, cap {CAPS['project_md']}; move detail into files beside it")
            t = pm.read_text(errors="ignore")
            for sec in ("Brief", "Status", "Log"):
                if not re.search(rf"^##\s+{sec}", t, re.M):
                    r.warn("layout", rel(root, pm), f"section '{sec}' missing")
        if proj.name.lower() not in mem_text:
            r.fail("reachability", rel(root, proj), f"project not listed in {rel(root, d / 'MEMORY.md')} Active Projects or Archive")
    if "Active Projects" not in mem_secs and any(pdir.iterdir()):
        r.warn("layout", rel(root, d / "MEMORY.md"), "workstation has Projects/ but no 'Active Projects' section")


def check_workstation(root, r, d, parent, wss, ex):
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
    mem_secs = check_memory(root, r, d / "MEMORY.md", "workstation")
    check_projects(root, r, d, mem_secs)

    res_dirs = [x for x in d.iterdir() if x.is_dir() and x.name.lower().endswith("resources") and not ex.excluded(x)]
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
        if trig is not None and not trig.strip():
            r.warn("map-quality", rel(root, c), f"Resources row '{cell}' has an empty trigger")
    # workstation-scoped tooling
    for rd in res_dirs:
        tool = rd / "tooling.md"
        if tool.exists() and len(lines(tool)) > CAPS["tooling_lines"]:
            r.fail("size", rel(root, tool), f"{len(lines(tool))} lines, cap {CAPS['tooling_lines']}")
    nested_dirs = {x for x, p in wss if p == d}
    for rd in res_dirs:
        for f in ex.walk(rd):
            if f.name == "README.md":
                continue
            fr = f.resolve()
            ok = fr in covered or any(str(fr).startswith(str(cv) + "/") or (cv.name == "SKILL.md" and str(fr).startswith(str(cv.parent) + "/")) for cv in covered)
            if not ok:
                relf = f.relative_to(rd).as_posix()
                ok = any(relf in m or f.name in m for m in mentioned)
            if not ok and any(str(fr).startswith(str(nd.resolve()) + "/") for nd in nested_dirs):
                ok = True
            if not ok:
                r.fail("reachability", rel(root, f), f"orphan: no Resources row or mention in {rel(root, c)} / MEMORY.md")
    for f in ex.walk(d):
        if f.name == "SKILL.md" and len(lines(f)) > CAPS["skill_lines"]:
            r.fail("size", rel(root, f), f"{len(lines(f))} lines, cap {CAPS['skill_lines']}")


def check_shared(root, r, entry, ex):
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
        if is_external(cell):
            continue
        p, _ = resolve(cell, [res, res / "rules", root])
        if p is None:
            r.fail("reachability", rel(root, entry), f"table row '{cell}' points at nothing that exists")
        else:
            covered.add(p.resolve())
    for f in ex.walk(res):
        if f.name in ("README.md", "cowork-os-conventions.md"):
            continue
        fr = f.resolve()
        ok = fr in covered or any(str(fr).startswith(str(cv.parent) + "/") for cv in covered if cv.name == "SKILL.md")
        if not ok:
            relf = f.relative_to(res).as_posix()
            ok = any(relf in m or f.name in m for m in mentioned)
        if not ok:
            r.fail("reachability", rel(root, f), "orphan: no References/Rules row in the entrypoint")
    rules_dir = res / "rules"
    for p in (rules_dir.glob("*.md") if rules_dir.is_dir() else []):
        n = len(lines(p))
        if n > CAPS["rule_lines"]:
            r.fail("size", rel(root, p), f"{n} lines, cap {CAPS['rule_lines']}")
        for it in re.split(r"\n(?=\d+\. )", p.read_text()):
            if re.match(r"\d+\. ", it) and len(it.strip().splitlines()) > CAPS["rule_item"]:
                r.warn("size", rel(root, p), f"rule '{it.strip().splitlines()[0][:50]}' spans {len(it.strip().splitlines())} lines, cap {CAPS['rule_item']}")
        if p.resolve() not in covered:
            r.fail("reachability", rel(root, p), "rule file not in the Rules table")
    rules_sec = secs.get("Rules", "")
    if "|" in rules_sec and not re.search(r"^\|[^|\n]*\|\s*before", rules_sec, re.I | re.M):
        r.warn("map-quality", rel(root, entry), "Rules table header should read 'Rule file | Before I...' so every row is read before acting")
    tool = res / "tooling.md"
    if tool.exists() and len(lines(tool)) > CAPS["tooling_lines"]:
        r.fail("size", rel(root, tool), f"{len(lines(tool))} lines, cap {CAPS['tooling_lines']}")
    for f in ex.walk(res):
        if f.name == "SKILL.md" and len(lines(f)) > CAPS["skill_lines"]:
            r.fail("size", rel(root, f), f"{len(lines(f))} lines, cap {CAPS['skill_lines']}")


def check_agents(root, r, entry):
    ag = root / "00_Agents"
    secs = dict(sections(entry.read_text()))
    rows = {a for a, _ in table_rows(secs.get("Agents", "")) if not is_placeholder(a)}
    if not ag.is_dir():
        if rows:
            r.fail("reachability", rel(root, entry), "Agents table has rows but 00_Agents/ does not exist")
        return
    names = set()
    items = []
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
        items.append((p, desc))
        if not desc:
            r.fail("hygiene", rel(root, p), "no description")
        elif len(desc) > CAPS["desc_chars"]:
            r.fail("size", rel(root, p), f"description {len(desc)} chars, cap {CAPS['desc_chars']}")
        if name not in rows and p.stem not in rows:
            r.fail("reachability", rel(root, p), "agent not listed in the Agents table")
    for row in rows:
        if row not in names and not (ag / f"{row}.md").exists():
            r.fail("reachability", rel(root, entry), f"Agents row '{row}' has no file in 00_Agents/")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][1] and SequenceMatcher(None, items[i][1].lower(), items[j][1].lower()).ratio() >= SIMILARITY:
                r.warn("duplicate", rel(root, items[i][0]), f"description nearly identical to {rel(root, items[j][0])}")
    script = Path(__file__).resolve().parent / "sync_agents.py"
    if script.exists() and ((root / ".claude" / "agents").exists() or (root / ".codex" / "agents").exists()):
        res = subprocess.run([sys.executable, str(script), "--root", str(root), "--check"], capture_output=True, text=True)
        if res.returncode != 0:
            for l in res.stdout.splitlines():
                kind, _, path = l.partition(" ")
                r.fail("sync", path, f"{kind.lower()}: run sync_agents.py")


def check_duplicate_rules(root, r, entry, wss):
    seen = []

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
    groups = {}
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


def check_conventions(root, r):
    conv = root / "00_Resources" / "cowork-os-conventions.md"
    if not conv.exists():
        r.warn("layout", "00_Resources/cowork-os-conventions.md", "conventions file missing; run /cowork:bootstrap adopt to add it without touching anything else")
        return None
    ctext = conv.read_text()
    m = re.search(r"cowork-os-conventions v(\d+)(?:\.(\d+))?", ctext)
    ver = None
    if not m:
        r.warn("drift", "00_Resources/cowork-os-conventions.md", f"no version line; the plugin ships v{CONVENTIONS_VERSION}. Run /cowork:bootstrap upgrade")
    else:
        ver = f"{m.group(1)}.{m.group(2) or 0}"
        pmaj, pmin = CONVENTIONS_VERSION.split(".")
        if m.group(1) != pmaj:
            r.warn("drift", "00_Resources/cowork-os-conventions.md", f"is v{ver}; plugin conventions are v{CONVENTIONS_VERSION} (major change: caps or file shape). Run /cowork:bootstrap upgrade")
        elif (m.group(2) or "0") != pmin:
            r.note(f"conventions v{ver} in project, v{CONVENTIONS_VERSION} available (additive, no action required; /cowork:bootstrap upgrade when convenient)")
    secs = dict(sections(ctext))
    body = next((b for t, b in secs.items() if "cap" in t.lower()), "")
    for label, capcell in table_rows(body):
        key = next((k for sub, k in sorted(CONVENTIONS_ROWS.items(), key=lambda x: -len(x[0])) if sub in label.lower()), None)
        if not key:
            continue
        nums = [int(n) for n in re.findall(r"\d+", capcell)]
        if nums and CAPS[key] not in nums:
            r.warn("drift", "00_Resources/cowork-os-conventions.md", f"cap for '{label}' says {capcell.strip()} but doctor.py uses {CAPS[key]}; change both together")
    return ver


def check_secrets(root, r, ex):
    for f in ex.walk(root):
        if f.suffix.lower() not in TEXT_EXT:
            continue
        rp = rel(root, f)
        if rp.startswith("00_Resources/rules/"):
            continue
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        for pat, label in SECRET_PATTERNS:
            if re.search(pat, text):
                r.fail("secrets", rp, f"contains something shaped like a {label}")
                break


# ---------------------------------------------------------------- runners

def audit(root: Path, include_nested=False):
    root = root.resolve()
    entry = root / "AGENTS.md" if (root / "AGENTS.md").exists() else root / "CLAUDE.md"
    r = Report()
    if not entry.exists() or not (root / "MEMORY.md").exists():
        return None, r, entry, 0
    ex = Excluder(root, include_nested)
    wss = workstations(root, ex)
    check_root(root, r, entry, ex)
    check_memory(root, r, root / "MEMORY.md", "root")
    check_routing(root, r, entry, wss)
    for d, parent in wss:
        check_workstation(root, r, d, parent, wss, ex)
    check_shared(root, r, entry, ex)
    check_agents(root, r, entry)
    check_duplicate_rules(root, r, entry, wss)
    ver = check_conventions(root, r)
    check_secrets(root, r, ex)
    return ver, r, entry, len(wss)


def print_report(r, entry_name, n_ws, ver):
    if not r.findings:
        print(f"doctor: clean ({n_ws} workstation(s), entrypoint {entry_name}, conventions v{ver or '?'})")
    for f in sorted(r.findings, key=lambda x: (x["severity"] != "FAIL", x["check"], x["path"])):
        print(f"{f['severity']} [{f['check']}] {f['path']}: {f['msg']}")
    for n in r.notes:
        print(f"note: {n}")
    if r.findings:
        print(f"\n{r.fails} fail, {r.warns} warn, {n_ws} workstation(s) scanned, conventions v{ver or '?'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--all", metavar="PARENT", help="fleet: audit every direct child of PARENT that is a workspace")
    ap.add_argument("--roots", metavar="FILE", help="fleet: file with one workspace path per line")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    ap.add_argument("--include-nested", action="store_true", help="audit nested git repositories too")
    a = ap.parse_args()

    if a.all or a.roots:
        if a.all:
            roots = sorted(p for p in Path(a.all).expanduser().iterdir() if is_workspace(p))
        else:
            roots = [Path(l.strip()).expanduser() for l in Path(a.roots).read_text().splitlines() if l.strip() and not l.startswith("#")]
        results = []
        for root in roots:
            ver, r, entry, n_ws = audit(root, a.include_nested)
            results.append((root, ver, r, entry, n_ws))
        if a.json:
            print(json.dumps([{"root": str(root), "conventions": ver, "workstations": n_ws, "fails": r.fails, "warns": r.warns, "findings": r.findings, "notes": r.notes} for root, ver, r, entry, n_ws in results], indent=2))
        else:
            w = max((len(root.name) for root, *_ in results), default=10)
            print(f"{'workspace':<{w}}  conv   ws  fail  warn  status")
            for root, ver, r, entry, n_ws in results:
                if ver is None and not r.findings and not entry.exists():
                    status = "not a workspace"
                else:
                    status = "clean" if not r.findings else ("FAIL" if r.fails else "warn")
                print(f"{root.name:<{w}}  v{ver or '?':<5} {n_ws:>3}  {r.fails:>4}  {r.warns:>4}  {status}")
            for root, ver, r, entry, n_ws in results:
                if r.findings:
                    print(f"\n== {root}")
                    print_report(r, entry.name, n_ws, ver)
            print(f"\n{len(results)} workspace(s): {sum(1 for *_, r, e, n in results if not r.findings)} clean, {sum(1 for *_, r, e, n in results if r.fails)} with failures")
        bad = any(r.fails or (a.strict and r.findings) for *_, r, e, n in results)
        return 1 if bad else 0

    ver, r, entry, n_ws = audit(Path(a.root), a.include_nested)
    if not entry.exists() or not (Path(a.root).resolve() / "MEMORY.md").exists():
        print("not a Cowork OS workspace (need AGENTS.md or CLAUDE.md, plus MEMORY.md). Run /cowork:bootstrap first.")
        return 2
    if a.json:
        print(json.dumps({"conventions": ver, "workstations": n_ws, "findings": r.findings, "notes": r.notes}, indent=2))
    else:
        print_report(r, entry.name, n_ws, ver)
    return 1 if (r.fails or (a.strict and r.findings)) else 0


if __name__ == "__main__":
    sys.exit(main())

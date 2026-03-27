#!/usr/bin/env python3
"""
poc init — Proof of Contribution quickstart scaffold
Run: python poc_init.py [project-root]

Creates:
  .poc/                     ← provenance store (SQLite by default)
  .poc/config.json          ← project config
  .poc/provenance.db        ← SQLite database (auto-created on first use)
  .github/
    PULL_REQUEST_TEMPLATE.md  ← PR template with AI Provenance section
    workflows/poc-check.yml   ← GitHub Action to enforce attribution
  poc.py                    ← local CLI entry point
"""

import os
import sys
import json
import sqlite3
import textwrap
from pathlib import Path
from datetime import datetime

# ── colour helpers ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✔{RESET}  {msg}")
def info(msg): print(f"  {CYAN}→{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}!{RESET}  {msg}")

# ── database schema ───────────────────────────────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ai_sessions (
  id           TEXT PRIMARY KEY,
  model        TEXT NOT NULL,
  created_at   TEXT,
  prompt_hash  TEXT,
  context      TEXT
);

CREATE TABLE IF NOT EXISTS human_experts (
  id           TEXT PRIMARY KEY,
  name         TEXT,
  handle       TEXT NOT NULL,
  platform     TEXT NOT NULL,
  verified     INTEGER DEFAULT 0,
  created_at   TEXT
);

CREATE TABLE IF NOT EXISTS human_sources (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  url          TEXT UNIQUE NOT NULL,
  platform     TEXT NOT NULL,
  title        TEXT,
  excerpt      TEXT,
  author_id    TEXT REFERENCES human_experts(id),
  source_date  TEXT,
  indexed_at   TEXT
);

CREATE TABLE IF NOT EXISTS code_artifacts (
  id           TEXT PRIMARY KEY,
  filepath     TEXT,
  type         TEXT,
  language     TEXT,
  description  TEXT,
  content_hash TEXT,
  session_id   TEXT REFERENCES ai_sessions(id),
  created_at   TEXT
);

CREATE TABLE IF NOT EXISTS artifact_sources (
  artifact_id      TEXT REFERENCES code_artifacts(id),
  source_id        INTEGER REFERENCES human_sources(id),
  relevance_score  REAL DEFAULT 0.5,
  specific_insight TEXT,
  quoted_excerpt   TEXT,
  confidence       TEXT CHECK(confidence IN ('HIGH','MEDIUM','LOW')),
  PRIMARY KEY (artifact_id, source_id)
);

CREATE TABLE IF NOT EXISTS knowledge_claims (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   TEXT REFERENCES ai_sessions(id),
  claim_text   TEXT NOT NULL,
  confidence   TEXT CHECK(confidence IN ('HIGH','MEDIUM','LOW')),
  source_id    INTEGER REFERENCES human_sources(id),
  verifiable   INTEGER DEFAULT 1
);

CREATE VIEW IF NOT EXISTS v_artifact_humans AS
  SELECT
    ca.filepath,
    ca.description AS artifact_desc,
    he.handle,
    he.platform,
    hs.url AS source_url,
    hs.title AS source_title,
    als.confidence,
    als.specific_insight
  FROM code_artifacts ca
  JOIN artifact_sources als ON als.artifact_id = ca.id
  JOIN human_sources hs     ON hs.id = als.source_id
  LEFT JOIN human_experts he ON he.id = hs.author_id;

CREATE TABLE IF NOT EXISTS structural_units (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  artifact_id TEXT REFERENCES code_artifacts(id),
  unit_type   TEXT NOT NULL,
  unit_name   TEXT,
  line_start  INTEGER,
  line_end    INTEGER,
  verified_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_su_artifact ON structural_units(artifact_id);
"""

# ── config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "version": "1.1.0",
    "project": None,
    "db": ".poc/provenance.db",
    "enforce_on_commit": False,
    "enforce_on_pr": True,
    "confidence_threshold": "MEDIUM",
    "platforms": ["github", "stackoverflow", "discourse", "docs"],
    "created_at": None
}

# ── PR template ───────────────────────────────────────────────────────────────
PR_TEMPLATE = """\
## Summary
<!-- What does this PR do? -->

## Changes
<!-- List key changes -->

---

## 🤖 AI Provenance
<!-- Required if any code in this PR was AI-assisted.
     Delete this section only if 100% human-written. -->

**AI model used:** <!-- e.g. claude-sonnet-4, gpt-4o -->

**Human sources that inspired AI output:**

| # | Author / Handle | Source URL | What came from this person |
|---|----------------|------------|---------------------------|
| 1 |                |            |                           |
| 2 |                |            |                           |

**Knowledge gaps** (where AI synthesized without a traceable human source):
- 

**Confidence level:** <!-- HIGH / MEDIUM / LOW -->

> _"AI should be a pointer to human expertise, not a replacement for it."_
> — Proof of Contribution
"""

# ── GitHub Action ─────────────────────────────────────────────────────────────
GH_ACTION = """\
name: Proof of Contribution Check

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  poc-check:
    name: Verify AI Provenance
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check for AI Provenance section
        id: poc
        run: |
          PR_BODY="${{ github.event.pull_request.body }}"

          if echo "$PR_BODY" | grep -qi "100% human-written"; then
            echo "status=exempt" >> $GITHUB_OUTPUT
            echo "✔ PR marked as 100% human-written — skipping provenance check."
            exit 0
          fi

          if echo "$PR_BODY" | grep -q "## 🤖 AI Provenance"; then
            if echo "$PR_BODY" | grep -qP "\\|\\s+\\d+\\s+\\|\\s+\\S"; then
              echo "status=pass" >> $GITHUB_OUTPUT
              echo "✔ AI Provenance section found and populated."
            else
              echo "status=empty" >> $GITHUB_OUTPUT
              echo "✘ AI Provenance section exists but table appears empty."
              exit 1
            fi
          else
            echo "status=missing" >> $GITHUB_OUTPUT
            echo "✘ No AI Provenance section found in PR description."
            exit 1
          fi

      - name: Post status comment (on failure)
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: [
                "## ⚠️ Proof of Contribution Check Failed",
                "",
                "This PR appears to contain AI-assisted code but is missing an **AI Provenance** section.",
                "",
                "Please add the following to your PR description:",
                "",
                "```",
                "## 🤖 AI Provenance",
                "| # | Author / Handle | Source URL | What came from this person |",
                "|---|----------------|------------|---------------------------|",
                "| 1 | @handle        | https://... | Specific insight used     |",
                "```",
                "",
                "Not sure what to write? Run `python poc.py trace <filepath>` locally.",
                "",
                "> _If this PR is 100% human-written with no AI assistance, add the phrase_",
                "> _`100% human-written` anywhere in your PR description to skip this check._"
              ].join("\\n")
            })
"""

# ── local CLI (poc.py) ────────────────────────────────────────────────────────
# This is written to disk as poc.py in the project root.
# Keep this in sync with the canonical poc.py in the repo.
POC_CLI = r'''
#!/usr/bin/env python3
"""
poc.py — local Proof of Contribution CLI

Commands:
  python poc.py trace <filepath>          Show full human attribution for a file
  python poc.py report                    Summarise provenance health across repo
  python poc.py add <filepath>            Interactively record provenance for a file
  python poc.py experts                   List top human experts in your knowledge graph
  python poc.py import-spec <spec-file>   Seed Knowledge Gaps from a spec-writer output
                [--artifact <filepath>]   Bind gaps to a specific file (optional)
                [--dry-run]               Preview without writing to the database
  python poc.py verify <filepath>         Detect Knowledge Gaps via static analysis
                [--strict]               Flag all uncited structural units as gaps

Workflow with spec-writer:
  1. /spec-writer "export order history as CSV"   → generates spec with assumptions
  2. python poc.py import-spec spec.md \
       --artifact src/utils/csv_exporter.py       → seeds assumptions as Knowledge Gaps
  3. Agent implements the feature
  4. python poc.py verify src/utils/csv_exporter.py → deterministic gap detection
  5. python poc.py trace src/utils/csv_exporter.py  → full attribution + gaps
  6. python poc.py add src/utils/csv_exporter.py    → resolve gaps by adding citations
"""

import ast
import re
import sys
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_PATH = Path(".poc/provenance.db")

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def get_db():
    if not DB_PATH.exists():
        print(f"{RED}✘ No provenance database found. Run: python poc_init.py{RESET}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


# ── trace ──────────────────────────────────────────────────────────────────────

def cmd_trace(filepath):
    db = get_db()
    rows = db.execute("""
        SELECT handle, platform, source_url, source_title,
               confidence, specific_insight
        FROM v_artifact_humans
        WHERE filepath = ?
        ORDER BY confidence DESC
    """, (filepath,)).fetchall()

    if not rows:
        print(f"{YELLOW}No provenance records found for: {filepath}{RESET}")
        print("  Run: python poc.py add <filepath>  to record attribution")
    else:
        print(f"\n{BOLD}Provenance trace: {filepath}{RESET}")
        print("─" * 60)
        for handle, platform, url, title, conf, insight in rows:
            colour = GREEN if conf == "HIGH" else YELLOW if conf == "MEDIUM" else RED
            print(f"  {colour}[{conf}]{RESET}  @{handle} on {platform}")
            print(f"          {title or url}")
            print(f"          {url}")
            if insight:
                print(f"          Insight: {insight}")
            print()

    gaps = db.execute("""
        SELECT DISTINCT kc.claim_text, kc.confidence
        FROM knowledge_claims kc
        JOIN ai_sessions s ON s.id = kc.session_id
        JOIN code_artifacts a ON a.session_id = s.id
        WHERE a.filepath = ? AND kc.source_id IS NULL
        ORDER BY kc.confidence ASC
    """, (filepath,)).fetchall()

    if gaps:
        print(f"{YELLOW}Knowledge gaps (AI-synthesized, no human source):{RESET}")
        for claim, conf in gaps:
            colour = RED if conf == "LOW" else YELLOW if conf == "MEDIUM" else GREEN
            print(f"  {colour}•{RESET} {claim}")
        print()
        print(f"  Resolve gaps: {CYAN}python poc.py add {filepath}{RESET}")

    db.close()


# ── report ─────────────────────────────────────────────────────────────────────

def cmd_report():
    db = get_db()
    total     = db.execute("SELECT COUNT(*) FROM code_artifacts").fetchone()[0]
    with_prov = db.execute("SELECT COUNT(DISTINCT artifact_id) FROM artifact_sources").fetchone()[0]
    gaps      = db.execute("SELECT COUNT(*) FROM knowledge_claims WHERE source_id IS NULL").fetchone()[0]
    resolved  = db.execute("SELECT COUNT(*) FROM knowledge_claims WHERE source_id IS NOT NULL").fetchone()[0]
    experts   = db.execute("SELECT COUNT(*) FROM human_experts").fetchone()[0]

    print(f"\n{BOLD}Proof of Contribution Report{RESET}")
    print("─" * 40)
    print(f"  Artifacts tracked    : {total}")
    print(f"  With provenance      : {with_prov}  ({int(with_prov/total*100) if total else 0}%)")
    print(f"  Unresolved gaps      : {gaps}")
    print(f"  Resolved claims      : {resolved}")
    print(f"  Human experts        : {experts}")

    if total and with_prov / total < 0.5:
        print(f"\n  {YELLOW}⚠ Less than 50% of artifacts have provenance records.{RESET}")
    elif total:
        print(f"\n  {GREEN}✔ Provenance coverage looks healthy.{RESET}")

    if gaps > 0:
        print(f"\n  {YELLOW}⚠ {gaps} unresolved Knowledge Gap(s).")
        print(f"    Run `poc.py trace <filepath>` to locate them.{RESET}")
    db.close()


# ── experts ────────────────────────────────────────────────────────────────────

def cmd_experts():
    db = get_db()
    rows = db.execute("""
        SELECT he.handle, he.platform,
               COUNT(DISTINCT als.artifact_id) AS artifacts_influenced
        FROM human_experts he
        JOIN human_sources hs  ON hs.author_id = he.id
        JOIN artifact_sources als ON als.source_id = hs.id
        GROUP BY he.id
        ORDER BY artifacts_influenced DESC
        LIMIT 20
    """).fetchall()

    print(f"\n{BOLD}Top Human Experts in Knowledge Graph{RESET}")
    print("─" * 50)
    if not rows:
        print(f"  {YELLOW}No experts recorded yet. Run: python poc.py add <filepath>{RESET}")
    else:
        for handle, platform, count in rows:
            print(f"  @{handle:<25} {platform:<15} {count} artifact(s)")
    db.close()


# ── add ────────────────────────────────────────────────────────────────────────

def cmd_add(filepath):
    db = get_db()
    print(f"\n{BOLD}Recording provenance for: {filepath}{RESET}")
    print("(Press Ctrl+C to cancel)\n")

    artifact_id = filepath.replace("/", "_").replace("\\", "_").replace(".", "_")
    db.execute("""
        INSERT OR IGNORE INTO code_artifacts (id, filepath, description)
        VALUES (?, ?, ?)
    """, (artifact_id, filepath, filepath))

    while True:
        url = input("  Human source URL (or Enter to finish): ").strip()
        if not url:
            break
        handle   = input("  Author handle: ").strip()
        platform = input("  Platform (github/stackoverflow/docs/other): ").strip() or "other"
        title    = input("  Source title: ").strip()
        insight  = input("  What specific insight came from this? ").strip()
        conf     = input("  Confidence HIGH/MEDIUM/LOW [MEDIUM]: ").strip().upper() or "MEDIUM"

        expert_id = f"{handle}@{platform}"
        db.execute("INSERT OR IGNORE INTO human_experts (id, handle, platform) VALUES (?,?,?)",
                   (expert_id, handle, platform))
        db.execute("""
            INSERT OR IGNORE INTO human_sources (url, platform, title, author_id)
            VALUES (?,?,?,?)
        """, (url, platform, title, expert_id))
        source_id = db.execute("SELECT id FROM human_sources WHERE url=?", (url,)).fetchone()[0]
        db.execute("""
            INSERT OR IGNORE INTO artifact_sources
              (artifact_id, source_id, specific_insight, confidence)
            VALUES (?,?,?,?)
        """, (artifact_id, source_id, insight, conf))

        resolved = _resolve_gaps(db, artifact_id, source_id, insight)
        db.commit()
        print(f"  {GREEN}✔ Recorded.{RESET}", end="")
        if resolved:
            print(f" {resolved} Knowledge Gap(s) resolved.", end="")
        print("\n")

    db.close()
    print(f"{GREEN}✔ Provenance saved. Run: python poc.py trace {filepath}{RESET}")


def _resolve_gaps(db, artifact_id, source_id, insight):
    """Auto-resolve knowledge_claims where insight overlaps with gap text."""
    gaps = db.execute("""
        SELECT kc.id, kc.claim_text
        FROM knowledge_claims kc
        JOIN ai_sessions s ON s.id = kc.session_id
        JOIN code_artifacts a ON a.session_id = s.id
        WHERE a.id = ? AND kc.source_id IS NULL
    """, (artifact_id,)).fetchall()

    resolved = 0
    insight_words = set(insight.lower().split())
    for gap_id, claim_text in gaps:
        claim_words = set(claim_text.lower().split())
        if len(insight_words & claim_words) >= 2:
            db.execute("UPDATE knowledge_claims SET source_id = ? WHERE id = ?",
                       (source_id, gap_id))
            resolved += 1
    return resolved


# ── import-spec ────────────────────────────────────────────────────────────────

ASSUMPTION_HEADER = re.compile(r"^##\s+Assumptions to review", re.IGNORECASE | re.MULTILINE)
IMPACT_INLINE     = re.compile(r"Impact:\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)
CORRECT_IF        = re.compile(r"^\s+Correct this if:\s*(?P<condition>.+)$",
                                re.IGNORECASE | re.MULTILINE)


def parse_assumptions(spec_text):
    match = ASSUMPTION_HEADER.search(spec_text)
    if not match:
        return []
    section = spec_text[match.end():]
    next_h  = re.search(r"^##\s+", section, re.MULTILINE)
    if next_h:
        section = section[:next_h.start()]

    assumptions = []
    for item in re.split(r"\n(?=\d+\.)", section.strip()):
        item = item.strip()
        if not item:
            continue
        lines      = item.split("\n")
        first_line = re.sub(r"^\d+\.\s*", "", lines[0].strip())
        im         = IMPACT_INLINE.search(first_line)
        impact     = im.group(1).upper() if im else "MEDIUM"
        text       = IMPACT_INLINE.sub("", first_line)
        text       = re.sub(r"\s*[—\-]+\s*$", "", text)
        text       = re.sub(r"^\[ASSUMPTION:\s*", "", text)
        text       = re.sub(r"\]\s*$", "", text).strip()
        if not text:
            continue
        correct_if = None
        for line in lines[1:]:
            ci = CORRECT_IF.match(line)
            if ci:
                correct_if = ci.group("condition").strip()
                break
        assumptions.append({"text": text, "impact": impact, "correct_if": correct_if})
    return assumptions


def cmd_import_spec(spec_file, artifact, dry_run):
    spec_path = Path(spec_file)
    if not spec_path.exists():
        print(f"{RED}✘ File not found: {spec_path}{RESET}")
        sys.exit(1)

    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        spec_text = spec_path.read_text(encoding="utf-16")

    assumptions = parse_assumptions(spec_text)
    if not assumptions:
        print(f"{YELLOW}⚠ No '## Assumptions to review' section found in {spec_path}.{RESET}")
        print("  Make sure this is a spec-writer output file.")
        sys.exit(0)

    if dry_run:
        print(f"\n{BOLD}Dry run — {len(assumptions)} assumption(s) in {spec_path}{RESET}\n")
        for i, a in enumerate(assumptions, 1):
            c = RED if a["impact"] == "HIGH" else YELLOW if a["impact"] == "MEDIUM" else GREEN
            print(f"  {i}. {c}[{a['impact']}]{RESET} {a['text']}")
            if a["correct_if"]:
                print(f"       Correct if: {a['correct_if']}")
        print(f"\n  (Nothing written — remove --dry-run to import)\n")
        return

    db          = get_db()
    session_id  = f"spec-import:{spec_path}:{datetime.now().isoformat()}"
    artifact_id = str(Path(artifact)) if artifact else None
    conf_map    = {"HIGH": "LOW", "MEDIUM": "MEDIUM", "LOW": "HIGH"}

    db.execute("INSERT OR IGNORE INTO ai_sessions (id, model, context) VALUES (?,?,?)",
               (session_id, "spec-writer", f"Imported from {spec_path}"))
    if artifact_id:
        db.execute("""
            INSERT OR IGNORE INTO code_artifacts (id, filepath, session_id, description)
            VALUES (?, ?, ?, ?)
        """, (artifact_id, artifact_id, session_id, f"Artifact for {artifact_id}"))

    inserted = 0
    for a in assumptions:
        claim = a["text"] + (f" [Correct if: {a['correct_if']}]" if a["correct_if"] else "")
        db.execute("""
            INSERT INTO knowledge_claims (session_id, claim_text, confidence, source_id, verifiable)
            VALUES (?, ?, ?, NULL, 1)
        """, (session_id, claim, conf_map.get(a["impact"], "MEDIUM")))
        inserted += 1

    db.commit()
    db.close()

    print(f"\n{BOLD}Spec assumptions imported — {inserted} Knowledge Gap(s) seeded{RESET}")
    print("─" * 55)
    for i, a in enumerate(assumptions, 1):
        c = RED if a["impact"] == "HIGH" else YELLOW if a["impact"] == "MEDIUM" else GREEN
        print(f"  {i}. {c}[{a['impact']}]{RESET} {a['text']}")
        if a["correct_if"]:
            print(f"       Correct if: {a['correct_if']}")
    print()
    if artifact_id:
        print(f"  {CYAN}→{RESET}  Bound to: {artifact_id}")
        print(f"  After the agent builds, run:")
        print(f"  {CYAN}python poc.py verify {artifact_id}{RESET}  — deterministic gap check")
        print(f"  {CYAN}python poc.py trace {artifact_id}{RESET}   — full attribution view")
        print(f"  {CYAN}python poc.py add {artifact_id}{RESET}     — cite sources, close gaps")
    else:
        print(f"  {CYAN}python poc.py report{RESET}  — see overall gap coverage")
    print(f"\n  {YELLOW}Any assumption that ships without a cited human source")
    print(f"  will appear as a Knowledge Gap in `poc.py verify` and `trace`.{RESET}\n")


# ── verify ─────────────────────────────────────────────────────────────────────
# Static analyser — detects Knowledge Gaps without AI self-reporting.
# Uses Python's ast module to extract structural units, then cross-checks
# against seeded knowledge_claims. Zero API calls. Exits 0 (clean) or 1 (gaps).

class ParseError(Exception):
    pass


@dataclass
class StructuralUnit:
    name: str
    unit_type: str      # 'function' | 'branch' | 'return_path'
    line_start: int
    line_end: int

    def __post_init__(self):
        valid = {"function", "branch", "return_path"}
        if self.unit_type not in valid:
            raise ValueError(f"unit_type must be one of {valid}, got '{self.unit_type}'")

    def summary(self):
        return f"{self.unit_type}: {self.name} (lines {self.line_start}–{self.line_end})"


# Parser registry — maps extension to parser function
PARSER_REGISTRY = {
    ".py":  "_parse_python",
    ".pyw": "_parse_python",
}


def _parse_python(filepath):
    """Parse a Python file into StructuralUnits using ast."""
    path = Path(filepath)
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        source = path.read_text(encoding="latin-1")
    except Exception as e:
        raise ParseError(f"Cannot read {filepath}: {e}") from e

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as e:
        raise ParseError(f"Syntax error in {filepath} at line {e.lineno}: {e.msg}") from e

    units = []
    branch_counter = [0]

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            end = getattr(node, "end_lineno", node.lineno)
            units.append(StructuralUnit(node.name, "function", node.lineno, end))
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            end = getattr(node, "end_lineno", node.lineno)
            units.append(StructuralUnit(node.name, "function", node.lineno, end))
            self.generic_visit(node)

        def visit_If(self, node):
            branch_counter[0] += 1
            n = branch_counter[0]
            try:
                cond = ast.unparse(node.test)
            except Exception:
                cond = f"branch_{n}"
            if len(cond) > 60:
                cond = cond[:57] + "..."
            end = getattr(node, "end_lineno", node.lineno)
            units.append(StructuralUnit(f"if {cond}", "branch", node.lineno, end))
            if node.orelse and not isinstance(node.orelse[0], ast.If):
                s = node.orelse[0].lineno
                e = getattr(node.orelse[-1], "end_lineno", node.orelse[-1].lineno)
                units.append(StructuralUnit(f"else (branch_{n})", "branch", s, e))
            self.generic_visit(node)

        def visit_Return(self, node):
            if node.value is not None:
                try:
                    val = ast.unparse(node.value)
                except Exception:
                    val = "value"
                if len(val) > 50:
                    val = val[:47] + "..."
                units.append(StructuralUnit(f"return {val}", "return_path",
                                            node.lineno, node.lineno))
            self.generic_visit(node)

    Visitor().visit(tree)
    units.sort(key=lambda u: u.line_start)
    return units


def _fuzzy_match(unit_name, claim_text, threshold=2):
    u = set(unit_name.lower().split())
    c = set(claim_text.lower().split())
    return len(u & c) >= threshold


def _ensure_structural_units_table(db):
    """Add structural_units table if missing (migration for existing databases)."""
    tables = {r[0] for r in
              db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "structural_units" not in tables:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS structural_units (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              artifact_id TEXT REFERENCES code_artifacts(id),
              unit_type   TEXT NOT NULL,
              unit_name   TEXT,
              line_start  INTEGER,
              line_end    INTEGER,
              verified_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_su_artifact
              ON structural_units(artifact_id);
        """)
        cols = {r[1] for r in
                db.execute("PRAGMA table_info(knowledge_claims)").fetchall()}
        if "structural_unit_id" not in cols:
            db.execute(
                "ALTER TABLE knowledge_claims "
                "ADD COLUMN structural_unit_id INTEGER REFERENCES structural_units(id)"
            )
        db.commit()


def cmd_verify(filepath, strict=False):
    ext = Path(filepath).suffix.lower()
    parser_name = PARSER_REGISTRY.get(ext)

    if parser_name is None:
        print(f"{YELLOW}⚠ No parser available for {ext} files.{RESET}")
        print(f"  Supported: {', '.join(PARSER_REGISTRY.keys())}")
        return 2

    if not Path(filepath).exists():
        print(f"{RED}✘ File not found: {filepath}{RESET}")
        return 2

    try:
        parse_fn = globals()[parser_name]
        units = parse_fn(filepath)
    except ParseError as e:
        print(f"{RED}✘ Parse error: {e}{RESET}")
        return 2

    if not units:
        print(f"{YELLOW}⚠ No structural units found in {filepath}.{RESET}")
        return 0

    db = get_db()
    _ensure_structural_units_table(db)

    # Ensure artifact exists
    artifact_id = filepath.replace("/", "_").replace("\\", "_").replace(".", "_")
    db.execute("""
        INSERT OR IGNORE INTO code_artifacts (id, filepath, description)
        VALUES (?, ?, ?)
    """, (artifact_id, filepath, filepath))

    # Store units
    now = datetime.now().isoformat()
    for unit in units:
        db.execute("""
            INSERT INTO structural_units
              (artifact_id, unit_type, unit_name, line_start, line_end, verified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (artifact_id, unit.unit_type, unit.name,
              unit.line_start, unit.line_end, now))
    db.commit()

    # Fetch seeded claims
    claims = db.execute("""
        SELECT kc.id, kc.claim_text, kc.confidence, kc.source_id
        FROM knowledge_claims kc
        JOIN ai_sessions s ON s.id = kc.session_id
        JOIN code_artifacts a ON a.session_id = s.id
        WHERE a.id = ?
    """, (artifact_id,)).fetchall()
    claims = [{"id": r[0], "text": r[1], "confidence": r[2],
               "resolved": r[3] is not None} for r in claims]
    has_seeded = len(claims) > 0

    # Cross-check
    gaps, covered = [], []
    for unit in units:
        matched = next(
            (c for c in claims if c["resolved"] and _fuzzy_match(unit.name, c["text"])),
            None
        )
        if matched:
            covered.append((unit, matched))
        else:
            if strict:
                gaps.append((unit, None))
            else:
                unresolved = next(
                    (c for c in claims
                     if not c["resolved"] and _fuzzy_match(unit.name, c["text"])),
                    None
                )
                if unresolved or not has_seeded:
                    gaps.append((unit, unresolved))

    db.close()

    # ── Output ─────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}Verify: {filepath}{RESET}")
    print("─" * 60)
    print(f"  Structural units detected : {len(units)}")
    print(f"  Seeded claims             : {len(claims)}")
    print(f"  Covered by cited source   : {len(covered)}")
    print(f"  Deterministic gaps        : {len(gaps)}")
    print()

    if covered:
        print(f"{GREEN}Covered units (human source cited):{RESET}")
        for unit, claim in covered:
            print(f"  {GREEN}✔{RESET} {unit.summary()}")
            print(f"      ← {claim['text'][:70]}")
        print()

    if gaps:
        if not has_seeded:
            print(f"{YELLOW}⚠ No spec imported — showing all uncited structural units.{RESET}")
            print(f"  Run: {CYAN}python poc.py import-spec spec.md --artifact {filepath}{RESET}")
            print(f"  for deterministic gap detection.\n")

        print(f"{YELLOW}Deterministic Knowledge Gaps (no human source):{RESET}")
        for unit, claim in gaps:
            colour = RED if (claim and claim["confidence"] == "LOW") else YELLOW
            print(f"  {colour}•{RESET} {unit.summary()}")
            if claim:
                print(f"      Seeded assumption: {claim['text'][:70]}")
        print()
        print(f"  Resolve: {CYAN}python poc.py add {filepath}{RESET}")
        return 1

    print(f"{GREEN}✔ No Knowledge Gaps — all detected units have cited sources.{RESET}\n")
    return 0


# ── router ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "trace":
        if len(sys.argv) < 3:
            print("Usage: python poc.py trace <filepath>"); sys.exit(1)
        cmd_trace(sys.argv[2])

    elif cmd == "report":
        cmd_report()

    elif cmd == "experts":
        cmd_experts()

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: python poc.py add <filepath>"); sys.exit(1)
        cmd_add(sys.argv[2])

    elif cmd == "import-spec":
        if len(sys.argv) < 3:
            print("Usage: python poc.py import-spec <spec-file> [--artifact <filepath>] [--dry-run]")
            sys.exit(1)
        spec_file = sys.argv[2]
        artifact  = None
        dry_run   = False
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] in ("--artifact", "-a") and i + 1 < len(sys.argv):
                artifact = sys.argv[i + 1]; i += 2
            elif sys.argv[i] == "--dry-run":
                dry_run = True; i += 1
            else:
                i += 1
        cmd_import_spec(spec_file, artifact, dry_run)

    elif cmd == "verify":
        if len(sys.argv) < 3:
            print("Usage: python poc.py verify <filepath> [--strict]"); sys.exit(1)
        fp     = sys.argv[2]
        strict = "--strict" in sys.argv[3:]
        sys.exit(cmd_verify(fp, strict))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
'''

# ── PR template ───────────────────────────────────────────────────────────────
PR_TEMPLATE = """\
## Summary
<!-- What does this PR do? -->

## Changes
<!-- List key changes -->

---

## 🤖 AI Provenance
<!-- Required if any code in this PR was AI-assisted.
     Delete this section only if 100% human-written. -->

**AI model used:** <!-- e.g. claude-sonnet-4, gpt-4o -->

**Human sources that inspired AI output:**

| # | Author / Handle | Source URL | What came from this person |
|---|----------------|------------|---------------------------|
| 1 |                |            |                           |
| 2 |                |            |                           |

**Knowledge gaps** (where AI synthesized without a traceable human source):
- 

**Confidence level:** <!-- HIGH / MEDIUM / LOW -->

> _"AI should be a pointer to human expertise, not a replacement for it."_
> — Proof of Contribution
"""

# ── GitHub Action ─────────────────────────────────────────────────────────────
GH_ACTION = """\
name: Proof of Contribution Check

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  poc-check:
    name: Verify AI Provenance
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check for AI Provenance section
        id: poc
        run: |
          PR_BODY="${{ github.event.pull_request.body }}"

          if echo "$PR_BODY" | grep -qi "100% human-written"; then
            echo "status=exempt" >> $GITHUB_OUTPUT
            echo "✔ PR marked as 100% human-written — skipping provenance check."
            exit 0
          fi

          if echo "$PR_BODY" | grep -q "## 🤖 AI Provenance"; then
            if echo "$PR_BODY" | grep -qP "\\|\\s+\\d+\\s+\\|\\s+\\S"; then
              echo "status=pass" >> $GITHUB_OUTPUT
              echo "✔ AI Provenance section found and populated."
            else
              echo "status=empty" >> $GITHUB_OUTPUT
              echo "✘ AI Provenance section exists but table appears empty."
              exit 1
            fi
          else
            echo "status=missing" >> $GITHUB_OUTPUT
            echo "✘ No AI Provenance section found in PR description."
            exit 1
          fi

      - name: Post status comment (on failure)
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: [
                "## ⚠️ Proof of Contribution Check Failed",
                "",
                "This PR appears to contain AI-assisted code but is missing an **AI Provenance** section.",
                "",
                "Please add the following to your PR description:",
                "",
                "```",
                "## 🤖 AI Provenance",
                "| # | Author / Handle | Source URL | What came from this person |",
                "|---|----------------|------------|---------------------------|",
                "| 1 | @handle        | https://... | Specific insight used     |",
                "```",
                "",
                "Not sure what to write? Run `python poc.py trace <filepath>` locally.",
                "",
                "> _If this PR is 100% human-written with no AI assistance, add the phrase_",
                "> _`100% human-written` anywhere in your PR description to skip this check._"
              ].join("\\n")
            })
"""

# ── main init ─────────────────────────────────────────────────────────────────
def init(root: Path):
    print(f"\n{BOLD}🔗 Proof of Contribution — init{RESET}\n")
    info(f"Project root: {root.resolve()}")

    project_name = root.resolve().name

    # 1. .poc/ directory + config
    poc_dir = root / ".poc"
    poc_dir.mkdir(exist_ok=True)

    config = {**DEFAULT_CONFIG,
              "project": project_name,
              "created_at": datetime.now().isoformat()}
    (poc_dir / "config.json").write_text(json.dumps(config, indent=2))
    ok("Created .poc/config.json")

    (poc_dir / ".gitignore").write_text("provenance.db\n")
    ok("Created .poc/.gitignore  (db excluded from git, config tracked)")

    # 2. SQLite database
    db_path = root / config["db"]
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    ok(f"Created {config['db']}  (SQLite — no extra infra needed)")

    # 3. GitHub PR template
    gh_dir = root / ".github"
    gh_dir.mkdir(exist_ok=True)
    (gh_dir / "PULL_REQUEST_TEMPLATE.md").write_text(PR_TEMPLATE, encoding="utf-8")
    ok("Created .github/PULL_REQUEST_TEMPLATE.md")

    # 4. GitHub Action
    workflows_dir = gh_dir / "workflows"
    workflows_dir.mkdir(exist_ok=True)
    (workflows_dir / "poc-check.yml").write_text(GH_ACTION, encoding="utf-8")
    ok("Created .github/workflows/poc-check.yml")

    # 5. Local CLI
    (root / "poc.py").write_text(POC_CLI, encoding="utf-8")
    ok("Created poc.py  (local CLI — includes import-spec command)")

    # 6. .gitignore hint
    gitignore  = root / ".gitignore"
    poc_entry  = ".poc/provenance.db\n"
    if gitignore.exists():
        if poc_entry.strip() not in gitignore.read_text():
            with open(gitignore, "a") as f:
                f.write(f"\n# Proof of Contribution\n{poc_entry}")
            ok("Updated .gitignore")
    else:
        gitignore.write_text(f"# Proof of Contribution\n{poc_entry}")
        ok("Created .gitignore")

    print(f"""
{GREEN}{BOLD}✔ Proof of Contribution initialised for '{project_name}'{RESET}

{BOLD}Next steps:{RESET}

  Option A — start with a spec (recommended):
    1. Run spec-writer: {CYAN}/spec-writer "your feature description"{RESET}
    2. Save the output: {CYAN}spec.md{RESET}
    3. Seed gaps:       {CYAN}python poc.py import-spec spec.md --artifact <filepath>{RESET}
    4. Build the feature with your agent
    5. Check gaps:      {CYAN}python poc.py trace <filepath>{RESET}
    6. Cite sources:    {CYAN}python poc.py add <filepath>{RESET}

  Option B — record attribution after the fact:
    1. {CYAN}python poc.py add <path/to/ai-generated-file.py>{RESET}
    2. {CYAN}python poc.py trace <path/to/file.py>{RESET}
    3. {CYAN}python poc.py report{RESET}

  Commit to enable PR enforcement:
    {CYAN}git add .github/ .poc/config.json poc.py && git commit -m "chore: add proof-of-contribution"{RESET}

  Provenance database: {CYAN}.poc/provenance.db{RESET} (local only, not committed)
  Config:              {CYAN}.poc/config.json{RESET}  (committed)
""")

if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if not root.exists():
        print(f"Error: {root} does not exist.")
        sys.exit(1)
    init(root)
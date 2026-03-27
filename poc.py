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

Workflow with spec-writer:
  1. /spec-writer "export order history as CSV"   → generates spec with assumptions
  2. python poc.py import-spec spec.md \
       --artifact src/utils/csv_exporter.py       → seeds assumptions as Knowledge Gaps
  3. Agent implements the feature
  4. python poc.py trace src/utils/csv_exporter.py → shows gaps with no human source
  5. python poc.py add src/utils/csv_exporter.py   → resolve gaps by adding citations
"""

import re
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

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
    total    = db.execute("SELECT COUNT(*) FROM code_artifacts").fetchone()[0]
    with_prov= db.execute("SELECT COUNT(DISTINCT artifact_id) FROM artifact_sources").fetchone()[0]
    gaps     = db.execute("SELECT COUNT(*) FROM knowledge_claims WHERE source_id IS NULL").fetchone()[0]
    resolved = db.execute("SELECT COUNT(*) FROM knowledge_claims WHERE source_id IS NOT NULL").fetchone()[0]
    experts  = db.execute("SELECT COUNT(*) FROM human_experts").fetchone()[0]

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

    artifact_id = filepath.replace("/", "_").replace(".", "_")
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

    assumptions = parse_assumptions(spec_path.read_text(encoding="utf-8"))
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
        print(f"  {CYAN}python poc.py trace {artifact_id}{RESET}")
        print(f"  {CYAN}python poc.py add {artifact_id}{RESET}")
    else:
        print(f"  {CYAN}python poc.py report{RESET}  — see overall gap coverage")
    print(f"\n  {YELLOW}Any assumption that ships without a cited human source")
    print(f"  will appear as a Knowledge Gap in `poc.py trace`.{RESET}\n")


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

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

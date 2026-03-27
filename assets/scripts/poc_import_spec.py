#!/usr/bin/env python3
"""
poc_import_spec.py — Import spec-writer assumptions into the provenance database.

Reads the '## Assumptions to review' section from a spec-writer output file,
parses each assumption, and seeds the knowledge_claims table with unresolved
claims. Any assumption that ends up in code without a cited human source will
appear as a Knowledge Gap in `poc.py trace`.

Usage:
    python poc_import_spec.py <spec-file> [--artifact <filepath>]

Examples:
    python poc_import_spec.py .specify/export-csv.md
    python poc_import_spec.py spec.md --artifact src/utils/csv_exporter.py
    python poc_import_spec.py spec.md  # imports without binding to a specific artifact

The spec file must be a spec-writer output containing an '## Assumptions to review'
section in this format:

    ## Assumptions to review

    1. [assumption text] — Impact: HIGH / MEDIUM / LOW
       Correct this if: [condition]

    2. [assumption text] — Impact: MEDIUM
       Correct this if: [condition]
"""

import re
import sys
import sqlite3
import argparse
import textwrap
from pathlib import Path
from datetime import datetime

GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

DB_PATH = Path(".poc/provenance.db")

# ── parser ─────────────────────────────────────────────────────────────────────

ASSUMPTION_HEADER = re.compile(r"^##\s+Assumptions to review", re.IGNORECASE | re.MULTILINE)
ASSUMPTION_ITEM   = re.compile(
    r"^\d+\.\s+(?:\[ASSUMPTION:\s*)?(?P<text>[^\]—\n]+?)(?:\])?"   # numbered item text
    r"(?:\s*[—-]+\s*Impact:\s*(?P<impact>HIGH|MEDIUM|LOW))?"        # optional impact
    r"\s*$",
    re.IGNORECASE | re.MULTILINE
)
CORRECT_IF = re.compile(r"^\s+Correct this if:\s*(?P<condition>.+)$", re.IGNORECASE | re.MULTILINE)
IMPACT_INLINE = re.compile(r"Impact:\s*(HIGH|MEDIUM|LOW)", re.IGNORECASE)


def parse_assumptions(spec_text: str) -> list[dict]:
    """
    Extract assumptions from the '## Assumptions to review' section.

    Returns a list of dicts:
        {
            "text": str,
            "impact": "HIGH" | "MEDIUM" | "LOW",
            "correct_if": str | None,
            "raw": str
        }
    """
    # Find the assumptions section
    match = ASSUMPTION_HEADER.search(spec_text)
    if not match:
        return []

    section = spec_text[match.end():]

    # Stop at the next ## heading
    next_heading = re.search(r"^##\s+", section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]

    assumptions = []
    # Split on numbered items
    items = re.split(r"\n(?=\d+\.)", section.strip())

    for item in items:
        item = item.strip()
        if not item:
            continue

        # Extract the first line (the assumption text + impact)
        lines = item.split("\n")
        first_line = lines[0].strip()

        # Remove leading number + dot
        first_line = re.sub(r"^\d+\.\s*", "", first_line)

        # Pull impact from inline if present
        impact_match = IMPACT_INLINE.search(first_line)
        impact = impact_match.group(1).upper() if impact_match else "MEDIUM"

        # Clean the assumption text
        text = IMPACT_INLINE.sub("", first_line)
        text = re.sub(r"\s*[—\-]+\s*$", "", text)          # trailing dash
        text = re.sub(r"^\[ASSUMPTION:\s*", "", text)        # leading [ASSUMPTION:
        text = re.sub(r"\]\s*$", "", text)                   # trailing ]
        text = text.strip()

        if not text:
            continue

        # Extract "Correct this if:" from subsequent lines
        correct_if = None
        for line in lines[1:]:
            ci_match = CORRECT_IF.match(line)
            if ci_match:
                correct_if = ci_match.group("condition").strip()
                break

        assumptions.append({
            "text": text,
            "impact": impact,
            "correct_if": correct_if,
            "raw": item
        })

    return assumptions


# ── database ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"{RED}✘ No provenance database found. Run: python poc_init.py{RESET}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def ensure_session(db: sqlite3.Connection, spec_file: str) -> str:
    """Create or retrieve an AISession for this spec import."""
    session_id = f"spec-import:{spec_file}:{datetime.now().isoformat()}"
    db.execute("""
        INSERT OR IGNORE INTO ai_sessions (id, model, context)
        VALUES (?, ?, ?)
    """, (session_id, "spec-writer", f"Imported from {spec_file}"))
    db.commit()
    return session_id


def seed_claims(
    db: sqlite3.Connection,
    session_id: str,
    assumptions: list[dict],
    artifact_id: str | None
) -> int:
    """
    Insert assumptions as unresolved knowledge_claims (source_id = NULL).

    Returns the count of newly inserted claims.
    """
    inserted = 0
    for assumption in assumptions:
        # Map impact to our confidence scale (inverted — high impact = LOW confidence)
        confidence_map = {"HIGH": "LOW", "MEDIUM": "MEDIUM", "LOW": "HIGH"}
        confidence = confidence_map.get(assumption["impact"], "MEDIUM")

        claim_text = assumption["text"]
        if assumption["correct_if"]:
            claim_text += f" [Correct if: {assumption['correct_if']}]"

        cursor = db.execute("""
            INSERT INTO knowledge_claims
                (session_id, claim_text, confidence, source_id, verifiable)
            VALUES (?, ?, ?, NULL, 1)
        """, (session_id, claim_text, confidence))

        claim_id = cursor.lastrowid

        # If an artifact is specified, bind the claim to it via a session link
        if artifact_id:
            # Ensure artifact exists (minimal record — user can enrich with poc.py add)
            db.execute("""
                INSERT OR IGNORE INTO code_artifacts
                    (id, filepath, session_id, description)
                VALUES (?, ?, ?, ?)
            """, (artifact_id, artifact_id, session_id, f"Artifact for {artifact_id}"))

        inserted += 1

    db.commit()
    return inserted


# ── report ─────────────────────────────────────────────────────────────────────

def print_summary(assumptions: list[dict], inserted: int, artifact_id: str | None):
    print(f"\n{BOLD}Spec assumptions imported{RESET}")
    print("─" * 50)

    for i, a in enumerate(assumptions, 1):
        impact_colour = RED if a["impact"] == "HIGH" else YELLOW if a["impact"] == "MEDIUM" else GREEN
        print(f"  {i}. {impact_colour}[{a['impact']}]{RESET} {a['text']}")
        if a["correct_if"]:
            print(f"       Correct if: {a['correct_if']}")

    print()
    print(f"  {GREEN}✔{RESET} {inserted} claim(s) seeded as unresolved Knowledge Gaps")

    if artifact_id:
        print(f"  {CYAN}→{RESET}  Bound to artifact: {artifact_id}")
        print(f"\n  Run {CYAN}python poc.py trace {artifact_id}{RESET} to see gaps after code ships.")
    else:
        print(f"\n  Run {CYAN}python poc.py report{RESET} to see overall gap coverage.")
        print(f"  To bind these to a specific file later:")
        print(f"  {CYAN}python poc.py add <filepath>{RESET}")

    print()
    print(f"  {YELLOW}Any assumption that ships in code without a cited human source")
    print(f"  will appear as a Knowledge Gap in `poc.py trace`.{RESET}\n")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import spec-writer assumptions into the provenance database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python poc_import_spec.py spec.md
              python poc_import_spec.py .specify/export-csv.md --artifact src/utils/csv_exporter.py
        """)
    )
    parser.add_argument("spec_file", help="Path to spec-writer output file")
    parser.add_argument(
        "--artifact", "-a",
        help="Filepath of the artifact this spec will generate (optional — can be added later)",
        default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print assumptions without writing to the database"
    )
    args = parser.parse_args()

    spec_path = Path(args.spec_file)
    if not spec_path.exists():
        print(f"{RED}✘ File not found: {spec_path}{RESET}")
        sys.exit(1)

    spec_text = spec_path.read_text(encoding="utf-8")
    assumptions = parse_assumptions(spec_text)

    if not assumptions:
        print(f"{YELLOW}⚠ No '## Assumptions to review' section found in {spec_path}.{RESET}")
        print("  Make sure the file is a spec-writer output containing that section.")
        sys.exit(0)

    if args.dry_run:
        print(f"\n{BOLD}Dry run — {len(assumptions)} assumption(s) found in {spec_path}{RESET}\n")
        for i, a in enumerate(assumptions, 1):
            impact_colour = RED if a["impact"] == "HIGH" else YELLOW if a["impact"] == "MEDIUM" else GREEN
            print(f"  {i}. {impact_colour}[{a['impact']}]{RESET} {a['text']}")
            if a["correct_if"]:
                print(f"       Correct if: {a['correct_if']}")
        print(f"\n  (Nothing written to database)\n")
        return

    db = get_db()
    session_id = ensure_session(db, str(spec_path))

    artifact_id = args.artifact
    if artifact_id:
        # Normalize to relative path
        artifact_id = str(Path(artifact_id))

    inserted = seed_claims(db, session_id, assumptions, artifact_id)
    db.close()

    print_summary(assumptions, inserted, artifact_id)


if __name__ == "__main__":
    main()
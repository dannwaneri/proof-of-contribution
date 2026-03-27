---
name: proof-of-contribution
description: >
  Use this skill whenever a developer wants to build Proof-of-Contribution systems,
  Knowledge Graphs that link AI-generated code back to human sources, or Human-in-the-Loop
  (HITL) indexing architectures. Trigger this skill when users mention: attribution of
  AI-generated code, provenance tracking, knowledge graphs for code, crediting human experts,
  preventing AI from "summarizing humans into oblivion", linking code to GitHub discussions
  or documentation, building indexing systems that surface human authors rather than AI
  summaries, contribution graphs, or any system where AI output needs to point back to its
  human inspiration. Also trigger for phrases like "proof of contribution", "human-in-the-loop
  indexing", "AI attribution", "source tracing", "knowledge provenance", "contribution
  transparency", "import-spec", "seed knowledge gaps", or "spec-writer integration".
  Use even if the user only describes the concept without using these exact terms.
---

# Proof-of-Contribution Skill

## Purpose

This skill helps Claude build systems where **AI-generated artifacts remain tethered to the
human knowledge that inspired them**. The core philosophy: AI should be a pointer to human
expertise, not a replacement for it.

Three things this skill enables:

1. **Provenance Blocks** — Structured attribution metadata attached to any AI output
2. **Knowledge Graphs** — Graph schemas linking code ↔ human sources ↔ expert authors
3. **HITL Indexing Systems** — Architectures where AI surfaces human experts rather than summarizing them

The spec-writer integration is the mechanism that makes Knowledge Gaps **deterministic**
rather than relying on AI self-reporting. See Mode 1 and the Day One section for how
`import-spec` wires the two skills together.

---

## When to Apply Which Mode

| User says... | Mode to use |
|---|---|
| "Write this code / generate this output" | **Provenance Block** — attach attribution to the output |
| "Help me design a system / architecture" | **Knowledge Graph Schema** — design the graph structure |
| "Build an indexing system / search" | **HITL Indexer** — full system design with human-surfacing |
| "I want to track contributions across a codebase" | **Knowledge Graph** + **Provenance Block** combined |
| "Seed gaps from my spec" / "import-spec" | **import-spec command** — see Day One section |

---

## Mode 1: Provenance Block

When generating any code, documentation, architecture, or explanation, append a structured
provenance block that traces what human knowledge the output draws from.

### Format

```
╔══════════════════════════════════════════════════════╗
║  PROOF OF CONTRIBUTION                               ║
╠══════════════════════════════════════════════════════╣
║  Generated artifact: <short description>             ║
║  Confidence: HIGH / MEDIUM / LOW                     ║
╠══════════════════════════════════════════════════════╣
║  HUMAN SOURCES THAT INSPIRED THIS                    ║
║                                                      ║
║  [1] <Author Name or Handle>                         ║
║      Source type: GitHub Discussion / Docs / Forum   ║
║      URL: <url if known, or describe location>       ║
║      Contribution: <what specific insight came from  ║
║                     this person / document>          ║
║                                                      ║
║  [2] ...                                             ║
╠══════════════════════════════════════════════════════╣
║  KNOWLEDGE GAPS (where AI filled in, no human cited) ║
║  - <gap 1>                                           ║
╠══════════════════════════════════════════════════════╣
║  RECOMMENDED HUMAN EXPERTS TO CONSULT                ║
║  - <name/community> for <topic>                      ║
╚══════════════════════════════════════════════════════╝
```

### How Knowledge Gaps are detected

The obvious assumption — that AI introspects and reports what it doesn't know — is wrong.
LLMs hallucinate confidently. An AI that could reliably detect its own knowledge gaps
wouldn't produce them in the first place.

The detection mechanism is a **comparison, not introspection**:

1. Before building, run `/spec-writer` — it generates a structured spec with an explicit
   `## Assumptions to review` section listing every decision the AI is making that you
   didn't specify, each one impact-rated.
2. Import those assumptions: `python poc.py import-spec spec.md --artifact <filepath>`
   This seeds them into the `knowledge_claims` table as unresolved gaps (`source_id = NULL`).
3. After the agent builds, `poc.py trace` cross-checks the artifact's session against
   those seeded claims. Any claim still unresolved surfaces as a Knowledge Gap.

The AI isn't grading its own exam. The spec is the answer key. The boundary holds because
it comes from the spec, not from the model's confidence.

### Rules for Provenance Blocks

- **Never omit the block** when this skill is active — even if sources are uncertain, show the gaps
- **Distinguish clearly** between "I know this came from X" vs "this pattern commonly appears in X"
- **Knowledge Gaps section is mandatory** — where AI admits it synthesized without a human source
- If the user provided URLs or context in their message, those ALWAYS go in the block as primary sources
- Confidence levels:
  - HIGH = user provided the source directly, or it's a well-known named pattern with a clear origin
  - MEDIUM = AI recognizes the approach from training but can't pinpoint exact source
  - LOW = AI synthesized this; human review strongly recommended

---

## Mode 2: Knowledge Graph Schema

When a user wants to build a system to track contributions, generate a graph schema.

### Core Node Types

```yaml
nodes:
  CodeArtifact:
    fields: [id, type, language, created_at, content_hash, description]
    examples: [function, module, PR, commit, config file]

  HumanSource:
    fields: [id, url, author_handle, platform, created_at, title, excerpt]
    platforms: [github_issue, github_discussion, docs_page, stackoverflow,
                blog_post, rfc, chat_transcript, forum_thread]

  HumanExpert:
    fields: [id, name, handle, platform_profiles, expertise_tags, verified]
    note: "This is the person, not the document. Link sources to experts."

  AISession:
    fields: [id, model, timestamp, prompt_hash, session_context]
    note: "Tracks which AI session generated what — for audit trails"

  KnowledgeClaim:
    fields: [id, claim_text, confidence, verifiable, source_id]
    note: "source_id = NULL means unresolved gap. Populated by import-spec."
```

### Core Edge Types

```yaml
edges:
  INSPIRED_BY:
    from: CodeArtifact
    to: HumanSource
    properties: [relevance_score, specific_insight, quoted_excerpt]

  AUTHORED_BY:
    from: HumanSource
    to: HumanExpert
    properties: [role]  # author, contributor, commenter

  GENERATED_IN:
    from: CodeArtifact
    to: AISession
    properties: [generation_order]

  CLAIMS:
    from: AISession
    to: KnowledgeClaim
    properties: [confidence_level]

  SOURCED_FROM:
    from: KnowledgeClaim
    to: HumanSource
    properties: [exact_quote, paraphrase]

  EXPERT_ON:
    from: HumanExpert
    to: topic_tag
    properties: [evidence_count, last_active]
```

### Implementation Targets

Generate schema implementations for whichever the user needs. Reference the appropriate
file in `references/`:

- **Neo4j (Cypher)** → see `references/neo4j-implementation.md`
- **JSON-LD / RDF** → see `references/jsonld-schema.md`
- **SQLite / Postgres (relational fallback)** → see `references/relational-schema.md`
- **In-memory (JavaScript/Python prototype)** → generate inline, no reference file needed

---

## Mode 3: HITL Indexing System

When the user wants to build an indexing system where AI **points to humans** rather than
replacing them, follow this architecture.

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    HITL INDEXER                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  INGESTION LAYER                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  GitHub  │  │   Docs   │  │  Forums  │  ...        │
│  │  Crawler │  │  Parser  │  │  Scraper │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       └─────────────┴─────────────┘                    │
│                      │                                  │
│  ATTRIBUTION LAYER   ▼                                  │
│  ┌─────────────────────────────────┐                   │
│  │  Entity Extractor               │                   │
│  │  - Identifies human authors     │                   │
│  │  - Extracts discrete claims     │                   │
│  │  - Scores expertise signals     │                   │
│  └────────────────┬────────────────┘                   │
│                   │                                     │
│  GRAPH LAYER      ▼                                     │
│  ┌─────────────────────────────────┐                   │
│  │  Knowledge Graph Store          │                   │
│  │  (Neo4j / JSON-LD / Postgres)   │                   │
│  └────────────────┬────────────────┘                   │
│                   │                                     │
│  QUERY LAYER      ▼                                     │
│  ┌─────────────────────────────────┐                   │
│  │  AI Query Interface             │                   │
│  │  Input: "How do I do X?"        │                   │
│  │  Output: Answer + Human Expert  │                   │
│  │          Cards (not summaries)  │                   │
│  └─────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### The "Expert Card" Output Pattern

```
Answer to your question: <concise AI-synthesized answer>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HUMAN EXPERTS ON THIS TOPIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 @username  (GitHub / Stack Overflow / Forum)
   Expertise signal: 47 posts on this topic, last active 2 weeks ago
   Key contribution: [link to their most relevant post]
   Quote: "..." (their words, not AI paraphrase)

👤 @username2  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORIGINAL SOURCES
  • [Title of doc/discussion] — <url>
  • [Title of doc/discussion] — <url>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Key Design Principles for HITL Systems

1. **Humans are nodes, not footnotes** — Expert entities are first-class citizens in the graph
2. **Preserve original voice** — Store verbatim excerpts; never store only AI paraphrases
3. **Expertise is earned, not assigned** — Score from activity signals, not AI judgment
4. **Decay and freshness** — Human contributions have timestamps; surface recency alongside authority
5. **Contribution loops** — The system should notify humans when their work is cited

---

## Composing Outputs

When generating any substantial output with this skill active:

1. **First**, deliver the artifact the user asked for (code, architecture, explanation)
2. **Then**, append the appropriate Provenance Block
3. **If** the user seems to be building a system, offer to generate the Knowledge Graph schema
   or HITL architecture as a follow-up
4. **If** the user has a spec-writer output, suggest running `import-spec` before the agent
   builds — this makes Knowledge Gaps deterministic rather than inferred

Do not ask permission to add the Provenance Block — just add it.
Do ask before generating full schemas or system architectures.

---

## Day One — Getting Another Developer Started

When a developer is starting fresh, lead with this quickstart sequence.

### Step 1 — Scaffold the project (30 seconds)

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/dannwaneri/proof-of-contribution.git \
  ~/.claude/skills/proof-of-contribution

python ~/.claude/skills/proof-of-contribution/assets/scripts/poc_init.py
```

This creates:
```
your-project/
├── .poc/
│   ├── config.json              ← project settings (commit this)
│   ├── provenance.db            ← SQLite store (local only, gitignored)
│   └── .gitignore
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── poc-check.yml        ← GitHub Action — fails PRs missing attribution
└── poc.py                       ← local CLI (trace, report, add, experts, import-spec)
```

### Step 2 — If using spec-writer, import assumptions before building

This is the recommended path. It makes Knowledge Gaps deterministic.

```bash
# 1. Generate a spec
/spec-writer "export order history as CSV"
# Save output to spec.md

# 2. Seed the gaps into the database
python poc.py import-spec spec.md --artifact src/utils/csv_exporter.py

# 3. Preview without writing (optional)
python poc.py import-spec spec.md --dry-run
```

Output:
```
Spec assumptions imported — 4 Knowledge Gap(s) seeded
───────────────────────────────────────────────────────
  1. [HIGH] async vs sync export — no human source cited
       Correct if: your order volumes require background processing
  2. [MEDIUM] CSV column ordering — AI chose this arbitrarily
  ...

  → Bound to: src/utils/csv_exporter.py
  After the agent builds, run:
  python poc.py trace src/utils/csv_exporter.py
```

### Step 3 — Build the feature with your agent

The agent implements the code. The seeded gaps sit in the database, waiting.

### Step 4 — Verify gaps after the build

```bash
python poc.py trace src/utils/csv_exporter.py
```

Output shows which seeded assumptions made it into code with no human source:
```
Knowledge gaps (AI-synthesized, no human source):
  • async vs sync export [Correct if: your order volumes require background processing]
  • CSV column ordering — AI chose this arbitrarily

  Resolve gaps: python poc.py add src/utils/csv_exporter.py
```

### Step 5 — Cite sources and close gaps

```bash
python poc.py add src/utils/csv_exporter.py
# Interactive: enter URL, author handle, platform, insight, confidence
# Gap auto-closes when insight text overlaps with the gap claim
```

### Step 6 — Enable PR enforcement (after the tool has saved you real hours)

```bash
git add .github/ .poc/config.json poc.py
git commit -m "chore: add proof-of-contribution"
git push
```

Once pushed, every PR is checked for an `## 🤖 AI Provenance` section. Add it after
the tool has already proven its value — not before.

### Upgrade paths (when SQLite isn't enough)

- **Team with shared DB** → migrate to Postgres using `references/relational-schema.md`
- **Graph queries needed** → migrate to Neo4j using `references/neo4j-implementation.md`
- **Semantic web / interop** → export to JSON-LD using `references/jsonld-schema.md`

---

## Example Trigger Prompts

- "Write a Python function to parse GitHub discussions"
- "How should I architect a system that credits human contributors?"
- "I want AI to point to experts instead of replacing them"
- "Build me a knowledge graph that links my codebase to its documentation sources"
- "How do I make sure AI output is traceable back to human knowledge?"
- "I want to build a 2026 indexing system with human-in-the-loop"
- "Seed my knowledge gaps from this spec"
- "I just ran spec-writer, how do I import the assumptions?"
- "Show me what gaps exist after the agent built this feature"

---

## Reference Files

**References (load when needed):**
- `references/neo4j-implementation.md` — Cypher queries and schema for Neo4j
- `references/jsonld-schema.md` — JSON-LD / RDF schema for semantic web compatibility
- `references/relational-schema.md` — SQL schema for teams without a graph DB
- `references/expertise-scoring.md` — Algorithms for scoring human expertise from signals

**Assets (output directly to user when requested):**
- `assets/scripts/poc_init.py` — Full quickstart scaffold script. Output the entire file
  contents when a developer says "how do I get started" or "give me the init script".
  The init script embeds the full `poc.py` CLI including the `import-spec` command.
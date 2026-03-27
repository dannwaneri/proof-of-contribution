# proof-of-contribution

A Claude Code skill that keeps human experts visible inside AI-assisted codebases — by linking every AI-generated artifact back to the human knowledge that inspired it.

---

## The problem it solves

Every day, developers ask AI to write code. The AI delivers. The code ships.

Somewhere in that exchange, a GitHub discussion where three engineers spent two hours debating the right tradeoff got silently consumed. The Stack Overflow answer that solved the exact same problem in 2019 — written by someone who spent a week diagnosing it — became invisible. The RFC that established why the team chose this pattern over that one stopped being findable.

The humans who built the knowledge that AI runs on receive no credit. Their work isn't cited, isn't surfaced, isn't preserved in the codebase. Over time, they stop contributing — because there's no signal that their contribution mattered.

This is the quiet cost of AI-assisted development that nobody is measuring yet.

proof-of-contribution is the counter-move. It keeps the human knowledge chain intact — inside every file, every PR, every session.

---

## How it works

### Option A — with spec-writer (recommended)

This is the path that makes Knowledge Gaps **deterministic** rather than inferred.

```
/spec-writer "export order history as CSV"
    → Generates spec with explicit assumptions list

python poc.py import-spec spec.md --artifact src/utils/csv_exporter.py
    → Seeds assumptions as unresolved Knowledge Gaps in the database

Agent implements the feature

python poc.py trace src/utils/csv_exporter.py
    → Shows exactly which assumptions shipped with no human source cited

python poc.py add src/utils/csv_exporter.py
    → Cite sources, close gaps interactively
```

The AI isn't grading its own exam. The spec is the answer key. Any assumption that makes it into code without a cited human source appears as a Knowledge Gap — not because the AI admitted uncertainty, but because the spec said it was an assumption and no citation ever resolved it.

### Option B — Provenance Blocks (after the fact)

Invoke the skill and Claude automatically appends a **Provenance Block** to every generated artifact:

```
╔══════════════════════════════════════════════════════╗
║  PROOF OF CONTRIBUTION                               ║
╠══════════════════════════════════════════════════════╣
║  Generated artifact: fetch_github_discussions()      ║
║  Confidence: MEDIUM                                  ║
╠══════════════════════════════════════════════════════╣
║  HUMAN SOURCES THAT INSPIRED THIS                    ║
║                                                      ║
║  [1] GitHub GraphQL API Documentation Team           ║
║      Source type: Official Docs                      ║
║      URL: docs.github.com/en/graphql                 ║
║      Contribution: cursor-based pagination pattern   ║
║                                                      ║
║  [2] GitHub Community (multiple contributors)        ║
║      Source type: GitHub Discussions                 ║
║      URL: github.com/community/community             ║
║      Contribution: "ghost" fallback for deleted      ║
║                    accounts — surfaced in bug reports║
╠══════════════════════════════════════════════════════╣
║  KNOWLEDGE GAPS (AI synthesized, no human cited)     ║
║  - Error handling / retry logic                      ║
║  - Rate limit strategy                               ║
╠══════════════════════════════════════════════════════╣
║  RECOMMENDED HUMAN EXPERTS TO CONSULT                ║
║  - github.com/octokit community for pagination       ║
╚══════════════════════════════════════════════════════╝
```

---

## Three modes

**1. Provenance Blocks** — attached automatically to any AI-generated code, doc, or architecture output. No prompt needed. Always there.

**2. Knowledge Graphs** — when you're building a system to track contributions at scale. Claude generates a complete graph schema (nodes, edges, query patterns) for Neo4j, Postgres, or JSON-LD.

**3. HITL Indexing Architecture** — when you want AI to surface human experts instead of summarizing them. Claude designs the full system: ingestion layer, attribution layer, graph store, and a query interface that returns **Expert Cards** pointing to real people, not AI paraphrases.

```
Answer: Use cursor-based pagination with GraphQL endCursor.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HUMAN EXPERTS ON THIS TOPIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 @tannerlinsley  (GitHub)
   Expertise signal: 23 contributions on pagination patterns
   Key contribution: github.com/TanStack/query/discussions/123
   Quote: "Cursor beats offset when rows can be inserted mid-page"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Quickstart

**1. Install the skill**

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/dannwaneri/proof-of-contribution.git ~/.claude/skills/proof-of-contribution
```

**2. Scaffold your project** (one-time, per repo)

```bash
python ~/.claude/skills/proof-of-contribution/assets/scripts/poc_init.py
```

This creates:

```
your-project/
├── .poc/
│   ├── config.json           ← project settings (commit this)
│   ├── provenance.db         ← SQLite store (local only, gitignored)
│   └── .gitignore
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md   ← PR template with AI Provenance section
│   └── workflows/
│       └── poc-check.yml          ← GitHub Action — fails PRs missing attribution
└── poc.py                    ← local CLI
```

No database to install. No service to run. SQLite works out of the box.

**3. Use the CLI**

```bash
# Core commands
python poc.py add src/utils/parser.py         # record attribution for a file interactively
python poc.py trace src/utils/parser.py       # show full human attribution chain
python poc.py report                          # repo-wide provenance health
python poc.py experts                         # top human experts in your knowledge graph

# spec-writer integration
python poc.py import-spec spec.md             # seed assumptions as Knowledge Gaps
python poc.py import-spec spec.md \
  --artifact src/utils/parser.py             # bind gaps to a specific file
python poc.py import-spec spec.md --dry-run  # preview without writing to the database
```

**4. Enable PR enforcement** (after the tool has already saved you real hours)

```bash
git add .github/ .poc/config.json poc.py
git commit -m "chore: add proof-of-contribution"
git push
```

Once pushed, the GitHub Action checks every PR for an `## 🤖 AI Provenance` section. Developers opt out by writing `100% human-written` in the PR body.

---

## What you get from `poc.py trace`

```
Provenance trace: src/utils/csv_exporter.py
────────────────────────────────────────────────────────────
  [HIGH]  @juliandeangelis on github
          Spec Driven Development at MercadoLibre
          https://github.com/mercadolibre/sdd-docs
          Insight: separate functional from technical spec

  [MEDIUM] @tannerlinsley on github
           Cursor pagination discussion
           https://github.com/TanStack/query/discussions/123
           Insight: cursor beats offset for live-updating datasets

Knowledge gaps (AI-synthesized, no human source):
  • Error retry strategy — no human source cited
  • CSV column ordering — AI chose this arbitrarily

  Resolve gaps: python poc.py add src/utils/csv_exporter.py
```

When `import-spec` was run before building, the gaps are seeded from the spec's assumption list — not inferred by the AI. That distinction is what makes them auditable.

---

## Why this matters in 2026

AI coding assistants are now standard. The question isn't whether AI writes code — it's whether the humans whose knowledge powers that AI remain visible and citable.

proof-of-contribution takes a position: **AI should be a pointer to human expertise, not a replacement for it.**

Three concrete payoffs:

**Auditability** — teams adopting AI-assisted development face pressure to explain where code comes from. A provenance record answers that with evidence, not assumptions.

**Onboarding** — a new developer tracing a complex module gets pointed to the original discussion where the decision was made and the person who made it. Faster than archaeology through git blame.

**Attribution** — the engineers, writers, and community members whose work trains and informs AI systems get credited in the artifacts those systems produce. That's a feedback loop worth closing.

---

## Works with spec-writer

proof-of-contribution pairs with [spec-writer](https://github.com/dannwaneri/spec-writer) to make Knowledge Gaps deterministic.

spec-writer eliminates ambiguity *before* the agent builds. proof-of-contribution preserves human attribution *after* the agent builds. The `import-spec` command bridges them:

```
/spec-writer "export order history as CSV"
    → Spec + Plan + Tasks + Assumptions (with sources)
    → python poc.py import-spec spec.md --artifact src/utils/csv_exporter.py
    → Agent implements
    → python poc.py trace src/utils/csv_exporter.py
    → Shows: which assumptions shipped with no human source
    → python poc.py add src/utils/csv_exporter.py
    → Full chain: feature request → spec decision → human source → code
```

Every assumption spec-writer flags can be resolved with a citation. Every citation becomes a node in the knowledge graph. The full chain — from idea to implementation to the humans who shaped it — stays intact.

---

## Upgrade paths

The default setup uses SQLite — no infra required. When you outgrow it:

| Need | Upgrade to |
|------|-----------|
| Team sharing a provenance DB | Postgres — see `references/relational-schema.md` |
| Graph traversal queries | Neo4j — see `references/neo4j-implementation.md` |
| Semantic web / interoperability | JSON-LD — see `references/jsonld-schema.md` |
| Scoring human expertise from signals | `references/expertise-scoring.md` |

---

## Install

**Claude Code:**
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/dannwaneri/proof-of-contribution.git ~/.claude/skills/proof-of-contribution
```

Works across Claude Code, Cursor, Gemini CLI, and any agent that supports the Agent Skills standard.

---

## Related

- [spec-writer](https://github.com/dannwaneri/spec-writer) — turns vague feature requests into structured specs before the agent starts building. The `import-spec` command consumes its output directly.
- [voice-humanizer](https://github.com/dannwaneri/voice-humanizer) — checks your writing against your own voice fingerprint, not generic AI-pattern rules
- [Foundation](https://github.com/dannwaneri/chat-knowledge) — captures what proved true across AI sessions so the understanding doesn't disappear when the context window closes

---

Built by [Daniel Nwaneri](https://dev.to/dannwaneri).

The core idea — that AI systems should point to human experts rather than replace them — is the 2026 version of a problem the open source community has always cared about: credit, attribution, and the humans behind the work.
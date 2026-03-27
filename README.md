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
## PROOF OF CONTRIBUTION
Generated artifact: fetch_github_discussions()
Confidence: MEDIUM

## HUMAN SOURCES THAT INSPIRED THIS

[1] GitHub GraphQL API Documentation Team
    Source type: Official Docs
    URL: docs.github.com/en/graphql
    Contribution: cursor-based pagination pattern

[2] GitHub Community (multiple contributors)
    Source type: GitHub Discussions
    URL: github.com/community/community
    Contribution: "ghost" fallback for deleted accounts
                  surfaced in bug reports

## KNOWLEDGE GAPS (AI synthesized, no human cited)
- Error handling / retry logic
- Rate limit strategy

## RECOMMENDED HUMAN EXPERTS TO CONSULT
- github.com/octokit community for pagination
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

# static analysis
python poc.py verify src/utils/parser.py        # deterministic gap detection — zero API calls
python poc.py verify src/utils/parser.py --strict  # flag all uncited structural units
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
    → python poc.py verify src/utils/csv_exporter.py
    → Deterministic: which structural units have no human source (zero API calls)
    → python poc.py trace src/utils/csv_exporter.py
    → Shows: full attribution + all remaining gaps
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

---

## FAQ

**Does this consume extra API tokens?**

Almost none. The `import-spec`, `trace`, `report`, `add`, and `experts` commands are pure local operations — SQLite reads and writes, zero API calls, zero tokens.

The only token cost is the Provenance Block itself. When the skill is active, Claude appends attribution metadata to generated output. A Provenance Block runs roughly 150-250 tokens. At current Sonnet pricing that's a fraction of a cent per generation — the same category of cost as asking Claude to add inline comments to code.

The spec-writer call that feeds `import-spec` is a token cost you were already paying before proof-of-contribution existed. The `import-spec` command just parses that output locally. No new LLM calls introduced.

**Does it work on Windows?**

Yes. The CLI is pure Python with no platform-specific dependencies. One gotcha: if you create spec files using PowerShell's `echo`, they save as UTF-16. Create them with `python -c "open('spec.md', 'w', encoding='utf-8').write(...)"` or any text editor set to UTF-8 to avoid encoding errors.

**Do I need to run `import-spec` before every build?**

Only when you've used spec-writer first. If you're generating code without a spec, run `poc.py verify` directly — it detects gaps via static analysis without any AI involvement. `import-spec` makes gaps more precise by tying them to named spec assumptions. Without it, `verify` still surfaces all uncited structural units as a baseline.

**What happens when I run `poc.py add` after seeding gaps?**

When you record a human source with `poc.py add`, the tool fuzzy-matches your insight text against open gap claims. If the words overlap meaningfully, the gap auto-closes and `source_id` gets populated. Run `poc.py trace` after adding to confirm which gaps remain open.

**Can I use this without Claude Code?**

Yes. The skill file (`SKILL.md`) works with any agent that supports the Agent Skills standard — Cursor, Gemini CLI, and others. The CLI (`poc.py`) and `import-spec` command are standalone Python and work regardless of which agent generated the code.

**Does `verify` work without spec-writer?**

Yes. Without a seeded spec, `verify` parses the file's structure and surfaces all functions, branches, and return paths as uncited units. It's less precise than the spec-writer path — every structural unit shows as a gap rather than only the ones tied to assumptions — but it requires no prior setup and makes zero API calls. Run `import-spec` first for deterministic gaps tied to your spec assumptions. Run `verify` alone for a structural baseline on any file.

**When should I turn on the GitHub Action?**

After `poc.py trace` has already saved you real time — not before. The enforcement works because by then the team understands the value and fills in the provenance section willingly. Turning it on day one frames it as overhead. Turning it on after it's proven useful frames it as a standard.
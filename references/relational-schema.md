# Relational Schema — Proof of Contribution

For teams without a graph DB. Uses PostgreSQL syntax (compatible with SQLite with minor changes).

## Tables

```sql
-- Human experts (the people)
CREATE TABLE human_experts (
  id          TEXT PRIMARY KEY,  -- handle@platform e.g. "torvalds@github"
  name        TEXT,
  handle      TEXT NOT NULL,
  platform    TEXT NOT NULL,     -- github, stackoverflow, discourse, etc.
  verified    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- Human sources (the documents/posts)
CREATE TABLE human_sources (
  id          SERIAL PRIMARY KEY,
  url         TEXT UNIQUE NOT NULL,
  platform    TEXT NOT NULL,
  title       TEXT,
  excerpt     TEXT,              -- verbatim quote, never AI paraphrase
  author_id   TEXT REFERENCES human_experts(id),
  created_at  TIMESTAMP,
  indexed_at  TIMESTAMP DEFAULT NOW()
);

-- AI sessions
CREATE TABLE ai_sessions (
  id          TEXT PRIMARY KEY,
  model       TEXT NOT NULL,
  timestamp   TIMESTAMP DEFAULT NOW(),
  prompt_hash TEXT,
  context     TEXT
);

-- Code artifacts
CREATE TABLE code_artifacts (
  id           TEXT PRIMARY KEY,
  type         TEXT,             -- function, module, PR, config, etc.
  language     TEXT,
  description  TEXT,
  content_hash TEXT,
  session_id   TEXT REFERENCES ai_sessions(id),
  created_at   TIMESTAMP DEFAULT NOW()
);

-- The core attribution link: artifact → source
CREATE TABLE artifact_sources (
  artifact_id      TEXT REFERENCES code_artifacts(id),
  source_id        INTEGER REFERENCES human_sources(id),
  relevance_score  FLOAT DEFAULT 0.5,
  specific_insight TEXT,
  quoted_excerpt   TEXT,
  confidence       TEXT CHECK (confidence IN ('HIGH','MEDIUM','LOW')),
  PRIMARY KEY (artifact_id, source_id)
);

-- Expertise scores (derived/maintained)
CREATE TABLE expertise_scores (
  expert_id      TEXT REFERENCES human_experts(id),
  topic_tag      TEXT,
  evidence_count INTEGER DEFAULT 0,
  last_active    TIMESTAMP,
  PRIMARY KEY (expert_id, topic_tag)
);

-- Knowledge claims (discrete facts AI used, with traceability)
CREATE TABLE knowledge_claims (
  id           SERIAL PRIMARY KEY,
  session_id   TEXT REFERENCES ai_sessions(id),
  claim_text   TEXT NOT NULL,
  confidence   TEXT CHECK (confidence IN ('HIGH','MEDIUM','LOW')),
  source_id    INTEGER REFERENCES human_sources(id),  -- NULL = AI synthesized
  verifiable   BOOLEAN DEFAULT TRUE
);
```

## Key Queries

```sql
-- Who are the humans behind an artifact?
SELECT e.handle, e.name, s.url, s.platform, s.title, as2.quoted_excerpt
FROM artifact_sources as2
JOIN human_sources s ON s.id = as2.source_id
JOIN human_experts e ON e.id = s.author_id
WHERE as2.artifact_id = $artifact_id
ORDER BY as2.relevance_score DESC;

-- What are the knowledge gaps (AI-synthesized claims)?
SELECT kc.claim_text, kc.confidence, ca.description AS artifact
FROM knowledge_claims kc
JOIN ai_sessions sess ON sess.id = kc.session_id
JOIN code_artifacts ca ON ca.session_id = sess.id
WHERE kc.source_id IS NULL
ORDER BY ca.created_at DESC;

-- Top experts for a topic
SELECT e.handle, e.name, es.evidence_count, es.last_active
FROM expertise_scores es
JOIN human_experts e ON e.id = es.expert_id
WHERE es.topic_tag = $topic
ORDER BY es.evidence_count DESC
LIMIT 10;
```
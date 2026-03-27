# Neo4j Implementation — Proof of Contribution Graph

## Schema Constraints & Indexes

```cypher
// Uniqueness constraints
CREATE CONSTRAINT ON (c:CodeArtifact) ASSERT c.id IS UNIQUE;
CREATE CONSTRAINT ON (s:HumanSource) ASSERT s.url IS UNIQUE;
CREATE CONSTRAINT ON (e:HumanExpert) ASSERT e.id IS UNIQUE;
CREATE CONSTRAINT ON (session:AISession) ASSERT session.id IS UNIQUE;

// Indexes for frequent lookups
CREATE INDEX ON :HumanSource(platform);
CREATE INDEX ON :HumanExpert(handle);
CREATE INDEX ON :CodeArtifact(language);
CREATE INDEX ON :HumanSource(created_at);
```

## Node Creation Patterns

```cypher
// Create a code artifact
MERGE (c:CodeArtifact {id: $id})
SET c.type = $type,
    c.language = $language,
    c.created_at = datetime(),
    c.content_hash = $hash,
    c.description = $description;

// Create a human source
MERGE (s:HumanSource {url: $url})
SET s.author_handle = $handle,
    s.platform = $platform,
    s.title = $title,
    s.excerpt = $excerpt,
    s.created_at = datetime($created_at);

// Create a human expert
MERGE (e:HumanExpert {id: $handle + '@' + $platform})
SET e.name = $name,
    e.handle = $handle,
    e.verified = false;

// Link expert to source they authored
MATCH (e:HumanExpert {id: $expert_id})
MATCH (s:HumanSource {url: $source_url})
MERGE (s)-[:AUTHORED_BY {role: 'author'}]->(e);
```

## Edge Creation Patterns

```cypher
// Link code artifact to human source
MATCH (c:CodeArtifact {id: $artifact_id})
MATCH (s:HumanSource {url: $source_url})
MERGE (c)-[r:INSPIRED_BY]->(s)
SET r.relevance_score = $score,
    r.specific_insight = $insight,
    r.quoted_excerpt = $excerpt;

// Link AI session to artifact
MATCH (a:AISession {id: $session_id})
MATCH (c:CodeArtifact {id: $artifact_id})
MERGE (c)-[:GENERATED_IN]->(a);
```

## Query Patterns

```cypher
// "Who are the human experts behind this code?"
MATCH (c:CodeArtifact {id: $artifact_id})
      -[:INSPIRED_BY]->(s:HumanSource)
      -[:AUTHORED_BY]->(e:HumanExpert)
RETURN e.name, e.handle, s.url, s.platform,
       s.title, collect(s.excerpt) AS quotes
ORDER BY count(s) DESC;

// "What did @username contribute to this codebase?"
MATCH (e:HumanExpert {handle: $handle})
      <-[:AUTHORED_BY]-(s:HumanSource)
      <-[:INSPIRED_BY]-(c:CodeArtifact)
RETURN c.description, c.type, s.url, s.title
ORDER BY c.created_at DESC;

// "Find all code with low-confidence provenance (AI-synthesized)"
MATCH (session:AISession)-[r:CLAIMS]->(k:KnowledgeClaim)
WHERE r.confidence_level = 'LOW'
MATCH (c:CodeArtifact)-[:GENERATED_IN]->(session)
RETURN c.id, c.description, collect(k.claim_text) AS unverified_claims;

// "Who are the top experts on a topic tag?"
MATCH (e:HumanExpert)-[r:EXPERT_ON]->(t:TopicTag {name: $topic})
RETURN e.handle, e.name, r.evidence_count, r.last_active
ORDER BY r.evidence_count DESC
LIMIT 10;
```

## Full Provenance Trail Query

```cypher
// Given an AI session, show full human attribution chain
MATCH path = (c:CodeArtifact)-[:GENERATED_IN]->(s:AISession),
             (c)-[:INSPIRED_BY]->(src:HumanSource)-[:AUTHORED_BY]->(e:HumanExpert)
WHERE s.id = $session_id
RETURN c.description AS artifact,
       src.title AS source_title,
       src.url AS source_url,
       src.platform AS platform,
       e.handle AS expert_handle,
       e.name AS expert_name
ORDER BY src.created_at ASC;
```
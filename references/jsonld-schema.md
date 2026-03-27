# JSON-LD Schema — Proof of Contribution

For semantic web / RDF compatibility. Enables interoperability with other knowledge graphs.

## Context Definition

```json
{
  "@context": {
    "@vocab": "https://proofofcontribution.dev/schema/",
    "schema": "https://schema.org/",
    "poc": "https://proofofcontribution.dev/schema/",

    "CodeArtifact": "poc:CodeArtifact",
    "HumanSource": "poc:HumanSource",
    "HumanExpert": "poc:HumanExpert",
    "AISession": "poc:AISession",
    "KnowledgeClaim": "poc:KnowledgeClaim",

    "inspiredBy": {"@id": "poc:inspiredBy", "@type": "@id"},
    "authoredBy": {"@id": "poc:authoredBy", "@type": "@id"},
    "generatedIn": {"@id": "poc:generatedIn", "@type": "@id"},
    "sourcedFrom": {"@id": "poc:sourcedFrom", "@type": "@id"},

    "confidenceLevel": "poc:confidenceLevel",
    "relevanceScore": "poc:relevanceScore",
    "quotedExcerpt": "poc:quotedExcerpt",
    "expertiseTag": "poc:expertiseTag",
    "evidenceCount": "poc:evidenceCount",
    "contentHash": "poc:contentHash",
    "platformHandle": "poc:platformHandle"
  }
}
```

## Example Document — Full Attribution Record

```json
{
  "@context": "https://proofofcontribution.dev/context.json",
  "@type": "CodeArtifact",
  "@id": "urn:poc:artifact:sha256:abc123",
  "schema:name": "parse_github_discussions()",
  "schema:programmingLanguage": "Python",
  "contentHash": "sha256:abc123",
  "schema:dateCreated": "2026-03-15T10:22:00Z",

  "generatedIn": {
    "@type": "AISession",
    "@id": "urn:poc:session:uuid:xyz789",
    "schema:softwareVersion": "claude-sonnet-4",
    "schema:dateCreated": "2026-03-15T10:20:00Z"
  },

  "inspiredBy": [
    {
      "@type": "HumanSource",
      "@id": "https://github.com/org/repo/discussions/42",
      "schema:name": "Best approach for parsing GraphQL responses",
      "poc:platform": "github_discussion",
      "quotedExcerpt": "We found that streaming the cursor yields 10x lower memory...",
      "relevanceScore": 0.92,
      "confidenceLevel": "HIGH",

      "authoredBy": {
        "@type": "HumanExpert",
        "@id": "urn:poc:expert:torvalds@github",
        "schema:name": "Example Author",
        "platformHandle": "exampleuser",
        "poc:platform": "github",
        "expertiseTag": ["parsing", "GraphQL", "Python"]
      }
    }
  ]
}
```

## Provenance Bundle (for export / sharing)

```json
{
  "@context": "https://proofofcontribution.dev/context.json",
  "@graph": [
    { "...artifact node..." },
    { "...session node..." },
    { "...source node 1..." },
    { "...source node 2..." },
    { "...expert node 1..." }
  ]
}
```

This bundle format is what gets stored, transmitted, or published alongside code artifacts.
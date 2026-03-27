# Expertise Scoring — Human Signal Algorithms

## Philosophy

Expertise scores must be **earned from evidence**, never assigned by AI judgment alone.
The system observes human behavior signals and aggregates them — AI only reads the score,
never sets it directly.

## Signal Sources by Platform

### GitHub
| Signal | Weight | Notes |
|--------|--------|-------|
| PR merged to main/master | 3.0 | Strong contribution signal |
| Issue opened (closed as fixed) | 1.5 | Problem identification |
| Comment on closed issue | 0.5 | Participation |
| Discussion reply (marked answer) | 2.5 | Knowledge transfer |
| Doc commit (`.md`, `.rst`, `.txt`) | 2.0 | Explicit documentation |
| Stars on authored repo for topic | 0.1 per star | Community validation |

### Stack Overflow / Stack Exchange
| Signal | Weight |
|--------|--------|
| Accepted answer | 3.0 |
| Answer upvote | 0.3 |
| Question upvote | 0.1 |
| Tag badge (gold) | 5.0 |
| Tag badge (silver) | 2.0 |

### Discourse / Forum
| Signal | Weight |
|--------|--------|
| Post marked "solution" | 2.5 |
| Post likes | 0.2 each |
| Trust level 3+ | 1.0 bonus |

## Scoring Formula

```python
def compute_expertise_score(signals: list[Signal], topic: str, now: datetime) -> float:
    """
    Decay-weighted expertise score for a human expert on a topic.
    """
    HALF_LIFE_DAYS = 365  # score halves every year of inactivity

    total = 0.0
    for signal in signals:
        if topic not in signal.tags:
            continue

        age_days = (now - signal.created_at).days
        decay = 0.5 ** (age_days / HALF_LIFE_DAYS)
        total += signal.weight * decay

    return round(total, 3)
```

## Expertise Tiers

| Score Range | Tier | Label |
|-------------|------|-------|
| 0 – 2 | 1 | Contributor |
| 2 – 8 | 2 | Active contributor |
| 8 – 20 | 3 | Domain participant |
| 20 – 50 | 4 | Subject matter expert |
| 50+ | 5 | Core maintainer / authority |

## Freshness Score (separate from expertise)

A human expert can be highly expert but inactive. Surface both:

```python
def freshness_label(last_active: datetime, now: datetime) -> str:
    days = (now - last_active).days
    if days < 30:   return "Active"
    if days < 180:  return "Recent"
    if days < 365:  return "Dormant"
    return "Inactive"
```

## Anti-Gaming Rules

1. **Self-citation penalty**: If an AI session's provenance chain loops back to content
   the same author generated in response to AI output, apply a 0.5x penalty
2. **Recency cap**: No single burst of activity in 7 days can contribute more than 20%
   of total score (prevents spam contributions)
3. **Diversity bonus**: Experts cited across 3+ independent codebases get a 1.2x multiplier
   (cross-project validation)
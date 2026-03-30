---
description: Multi-agent debate to make better technical decisions
---

# Technical Debate: $ARGUMENTS

Run a structured debate to reach a well-reasoned decision on `$ARGUMENTS`.

## Round 1 — Positions (parallel)

Launch these agents simultaneously with the question:

- `architect` — technical design perspective
- `pragmatist` — simplicity and shipping speed perspective
- `security-ops` — enterprise security and data sovereignty perspective
- `ml-engineer` — AI/ML quality and performance perspective (if relevant)

Prompt each:
```
DEBATE QUESTION: $ARGUMENTS

State your position clearly. Max 200 words.
What do you recommend and why?
What are the risks of your approach?
```

## Round 2 — Rebuttals (parallel)

Share all Round 1 positions with each agent, ask them to respond:
```
The other positions were:
[architect's position]
[pragmatist's position]
[security-ops's position]

What do they get wrong? What are they missing?
Max 150 words.
```

Then launch `devils-advocate`:
```
All positions so far: [all positions]

What is everyone missing? What assumption is everyone making that might be wrong?
```

## Synthesis

After all rounds, synthesize:

```markdown
## Decision: [question]

### Consensus
[what everyone agreed on]

### Key Trade-off
[the central tension between positions]

### Recommendation
[clear decision with reasoning]

### What We're Accepting
[the risks/downsides we're consciously accepting]

### Trigger to Revisit
[what would cause us to change this decision]
```

Present synthesis to user for final approval.

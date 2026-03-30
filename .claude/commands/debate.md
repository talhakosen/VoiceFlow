---
description: Multi-agent debate to make better technical decisions
---

# Technical Debate: $ARGUMENTS

Run a structured debate to reach a well-reasoned decision on `$ARGUMENTS`.

## Round 1 — Positions (parallel)

Launch these agents simultaneously:

- `architect` — technical design + layer/tenant implications
- `pragmatist` — simplicity, shipping speed, YAGNI
- `security-ops` — enterprise security, KVKK/BDDK, data sovereignty
- `ml-engineer` — AI/ML quality and performance (if ML-relevant)

Prompt each:
```
DEBATE QUESTION: $ARGUMENTS
KATMAN CONTEXT: [current katman being worked on]

State your position clearly. Max 200 words.
What do you recommend and why?
What are the risks of your approach?
```

## Round 2 — Rebuttals (parallel)

Share all Round 1 positions, ask each agent:
```
The other positions were:
[architect's position]
[pragmatist's position]
[security-ops's position]
[ml-engineer's position if applicable]

What do they get wrong? What are they missing?
Max 150 words.
```

Then launch `devils-advocate`:
```
All positions: [all positions]
Katman context: [1/2/3]

What is everyone missing? What assumption might be wrong?
Especially consider: Turkish enterprise procurement reality, Wispr Flow competitive dynamics, and first-customer demo failure scenarios.
```

## Synthesis

```markdown
## Decision: [question]

### Consensus
[what everyone agreed on]

### Key Trade-off
[the central tension]

### Recommendation
[clear decision with reasoning]

### Wispr Flow Competitive Impact
[does this widen or narrow our moat?]

### What We're Accepting
[risks we're consciously taking]

### Trigger to Revisit
[what would cause us to change this decision]
```

Present synthesis to user for final approval.

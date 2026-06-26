---
name: plan-with-team
description: Use when creating a plan that benefits from multiple independent agent perspectives — requirements analysis, architecture, risk review, and task breakdown done in parallel before synthesis.
---

# Plan With Team

## Overview

Fan out planning work to specialized agents in parallel, then synthesize their outputs into a unified plan. Each agent focuses on one dimension without being influenced by the others.

## When to Use

- Starting a non-trivial feature or project
- When a plan needs multiple perspectives (requirements, architecture, risks, tasks)
- Before executing any implementation work

## Process

### 1. Define the Goal

State clearly what needs to be planned. Include context: constraints, stack, team size, deadline if any.

### 2. Fan Out to Agent Panel

Dispatch these agents **in parallel**:

| Agent | Prompt Focus |
|-------|-------------|
| **Requirements Agent** | What must this do? What are the acceptance criteria? What edge cases matter? |
| **Architecture Agent** | How should this be structured? What components, data flow, interfaces? |
| **Risk Agent** | What could go wrong? What assumptions are dangerous? What's the biggest unknown? |
| **Task Agent** | Break this into concrete, independently-executable tasks. Estimate rough effort per task. |

Each agent receives only the goal — not each other's output.

### 3. Synthesize

After all agents complete, produce a unified plan with these sections:

```
## Goal
[one sentence]

## Requirements
[from Requirements Agent — edited for clarity]

## Architecture
[from Architecture Agent — diagrams welcome]

## Risks & Mitigations
[from Risk Agent — each risk paired with a mitigation]

## Task Breakdown
[from Task Agent — ordered by dependency, with effort estimates]

## Open Questions
[unresolved items that need human input before work begins]
```

### 4. Present for Approval

Show the synthesized plan to the user. Do not begin implementation until the plan is approved.

## Example Dispatch

```
Goal: Build a REST API for user authentication with JWT tokens.
Stack: Node.js, PostgreSQL, Express.
Constraint: Must support refresh token rotation.

→ Requirements Agent: What endpoints, payloads, and behaviors are required?
→ Architecture Agent: How should the auth service be structured?
→ Risk Agent: What are the security and operational risks?
→ Task Agent: Break this into implementation tasks with estimates.
```

## Common Mistakes

- **Letting agents see each other's output** — this causes anchoring; keep them blind to each other
- **Skipping the synthesis step** — raw agent outputs are inputs, not the plan
- **Starting implementation before approval** — the plan exists to get alignment, not to be skipped

---
name: epics
description: Use when a large feature or goal needs to be broken down into smaller, actionable user stories and tasks before work begins.
---

# Epics

## Overview

An epic is a large feature too big to build in one go. This skill breaks an epic down into user stories, then breaks each story into concrete tasks.

## Structure

```
Epic
  └── User Story 1 (a slice of value for the user)
        └── Task 1.1 (concrete implementation step)
        └── Task 1.2
  └── User Story 2
        └── Task 2.1
        └── Task 2.2
```

## Process

### 1. Define the Epic

State the epic in one sentence:
> "As a [user], I want to [goal] so that [benefit]."

### 2. Break Into User Stories

Each story should:
- Deliver a small, testable slice of value
- Be completable in 1–2 days
- Follow the format: `As a [user], I want to [action] so that [benefit].`

### 3. Break Each Story Into Tasks

Each task should:
- Be a single, concrete action (write a function, create a UI component, add a migration)
- Be completable in a few hours
- Have a clear "done" definition

### 4. Output Format

```
## Epic: [Name]
[One-sentence description]

### Story 1: [Name]
As a [user], I want to [action] so that [benefit].
Acceptance criteria:
- [ ] criterion 1
- [ ] criterion 2

Tasks:
- [ ] Task 1.1 — [description]
- [ ] Task 1.2 — [description]

### Story 2: [Name]
...
```

## Example

```
## Epic: User Authentication

### Story 1: Register an account
As a visitor, I want to create an account so that I can access the app.
Acceptance criteria:
- [ ] User can submit email and password
- [ ] Duplicate emails are rejected

Tasks:
- [ ] Task 1.1 — Create POST /auth/register endpoint
- [ ] Task 1.2 — Add users table migration
- [ ] Task 1.3 — Validate email format and password length

### Story 2: Log in
As a user, I want to log in so that I can access my data.
Acceptance criteria:
- [ ] User receives a JWT on success
- [ ] Invalid credentials return a 401

Tasks:
- [ ] Task 2.1 — Create POST /auth/login endpoint
- [ ] Task 2.2 — Implement JWT generation
```

## Common Mistakes

- **Stories too large** — if a story takes more than 2 days, split it
- **Tasks too vague** — "implement auth" is not a task; "create POST /auth/login" is
- **Skipping acceptance criteria** — without them, you don't know when a story is done

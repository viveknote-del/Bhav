# Feature — Interactive feature intake

Guides the user through defining a new feature, asks clarifying questions,
and writes it into plans/forward.md as a new step ready for `/next` or `/pipeline`.

## Instructions

### Step 1 — Understand the feature

If the user provided a description with the command, use it as a starting point.
If not, ask: "What feature do you want to build? One sentence is fine."

### Step 2 — Ask clarifying questions (one round only)

After hearing the feature idea, ask these questions in a single message.
Only ask questions that aren't already answered by the initial description:

1. **Who uses this?** — Which user type (host, attendee, admin, external system)?
2. **What's the trigger?** — What action or event starts this feature?
3. **What does success look like?** — What does the user see when it works?
4. **What platforms?** — Web only, mobile only, or both? Backend only?
5. **Any integrations?** — External APIs, payment processors, email, etc.?
6. **Priority vs existing work?** — Is this more urgent than what's already planned?

Skip any question the user already answered. Keep it conversational, not a form.

### Step 3 — Confirm understanding

After the user answers, summarize in one paragraph:
```
Got it. Here's what I'll add to the plan:

**[Feature Name]** — [one paragraph description covering who, what, why, and how]
- Platforms: [web/mobile/backend]
- Integrations: [any external services]
- Dependencies: [which existing steps must be done first]

Does this look right? I'll assign it as Step N in the forward plan.
```

Wait for user confirmation before proceeding.

### Step 4 — Write to forward plan

1. Read `plans/forward.md`
2. Find the next available step number
3. Append a new step section:

```markdown
## Step {N} — {Feature Name}

**Depends on:** {dependencies}
**Goal:** {one sentence goal}
**Added:** {YYYY-MM-DD} via /feature

- {bullet point for each key deliverable}
- {bullet point}
```

4. Update `DOCS/BACKLOG.md` — add a one-line entry:
```markdown
- **Step {N}: {Feature Name}** — {one sentence} — added {YYYY-MM-DD}
```

### Step 5 — Confirm to user

```
Feature added as Step {N} in plans/forward.md.

To build it:
  /pipeline "Step {N} — {Feature Name}"

Or run /next to see it alongside bugs and other pending work.
```

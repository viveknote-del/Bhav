---
name: design-extract
description: Extract design language from any URL — generates Tailwind config, design tokens, CSS variables, and component stubs
allowed-tools: Bash, Read, Write, Glob
---

# Design Extract

Extract the complete design language from any website URL and generate ready-to-use config files.

## Usage

```
/design-extract https://example.com
/design-extract https://competitor.com --screenshots
```

## What it generates

- AI-optimized design language markdown
- W3C design tokens (JSON)
- Tailwind config (`tailwind.config.js`)
- CSS custom properties (`variables.css`)
- shadcn/ui theme CSS
- React theme object
- Figma variables (JSON)
- WCAG accessibility score

## How to run

```bash
npx designlang <url>
# or with screenshots:
npx designlang <url> --screenshots
# Custom output dir:
npx designlang <url> --out ./design-tokens
```

## Integration with /kickoff

During `/kickoff` Phase 2 (Architecture Design), if the user says
"I want it to look like [competitor URL]", run:

```bash
npx designlang <url> --out ./design-tokens
```

Then read `./design-tokens/*-tailwind.config.js` and merge into
`apps/web/tailwind.config.ts`. Read `*-variables.css` and merge
into `apps/web/src/app/globals.css`.

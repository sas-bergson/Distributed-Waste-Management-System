# DWMS Documentation Style Guide

This guide defines the writing, formatting, and review standards for all Markdown documentation in the Distributed Waste Management System (DWMS) repository.

## Structure and Headings

- Start every document with a single `# H1` title.
- Increment heading levels by one (`H1` to `H2` to `H3`); never skip levels.
- Use ATX headings (`# Heading`) rather than underline headings.
- Leave one blank line before and after every heading, list, table, and code block.
- Do not put trailing punctuation (`:` or `.`) at the end of a heading.

## Code Blocks and Commands

- Always use fenced code blocks (triple backticks) instead of indented blocks.
- Always specify a language tag (`bash`, `yaml`, `python`, `json`, `text`, or `mermaid`).
- Use `docker compose` (Compose v2), never `docker-compose`.
- Verify every command and file path against the repository before opening a PR.

## Lists, Tables, and Links

- Use `-` for unordered lists and `1.` for ordered steps, with 2-space indentation for nested items.
- Use relative links (for example, `[README](../../README.md)`) for files inside the repository so the docs portal and link-checker can verify them.
- Never leave bare URLs in prose; wrap them as `[label](https://example.org)` or `<https://example.org>`.

## DWMS Ubiquitous Language

Use the exact service, store, and header names defined in the project specification:

- **Services:** `gateway`, `locations`, `map`, `requests`, `realtime`, `notifications`
- **Data stores & broker:** `postgis` (`postgis/postgis`), `redis`, `mosquitto`
- **Trusted gateway headers:** `X-Tenant-Id`, `X-User-Id`, `X-Request-Id`
- **Health endpoint:** `GET /healthz`

## Architecture Decision Records (ADRs)

Every ADR must be immutable once merged and include all six sections:

1. **Title:** `ADR-NNNN: <imperative decision>`
2. **Status:** `Proposed`, `Accepted`, `Deprecated`, or `Superseded by ADR-XXXX`
3. **Context:** 3 to 5 neutral sentences describing the forces and constraints
4. **Decision:** Active voice (`We, the <team>, will ...`) naming the scope
5. **Consequences:** At least one positive, one negative, and one neutral effect
6. **Alternatives Considered:** At least two rejected options with specific numbers or thresholds

## Pre-Merge Hygiene

- Remove all `TODO`, `XXX`, and `FIXME` markers before marking a PR ready for review.
- Never commit `.env` files, API keys, tokens, or real citizen data.
- End every Markdown file with a single trailing newline and zero trailing spaces.

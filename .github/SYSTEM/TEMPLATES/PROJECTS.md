---
version: 1.0.0
last_updated: {{now}}
convention: kaios-freshness-v1
---

# Projects

Every project the assistant may be asked about, and the words that route to it.

## Projects table

| Project | Path | URL | Deploy | Stack |
|---------|------|-----|--------|-------|
{{project_rows}}

## Routing aliases

| When the ask says | Route to |
|---|---|
{{alias_rows}}

---
Rendered by `kaios setup render`. Per-project rules live beside this file in
`PROJECTS/<name>.instructions.md`, and each project's articulated done-state in
`PROJECTS/<name>/ISA.md`.

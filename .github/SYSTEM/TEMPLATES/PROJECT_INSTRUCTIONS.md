---
applyTo: "{{glob}}"
version: 1.0.0
last_updated: {{now}}
convention: kaios-freshness-v1
---

# {{name}}

| field | value |
|---|---|
| path | {{path}} |
| url | {{url}} |
| deploy | {{deploy}} |
| stack | {{stack}} |

## What this project is for

{{purpose}}

## What done looks like here

{{done_means}}

- The change is verified by running something, not by reading the diff.
- The project's own test command passes before any claim closes.
- Deploying is `{{deploy}}`, and it is never run without being asked.

## Where this project hurts

{{pain_points}}

## Rules for this project

{{rules}}

## Articulated done-state

`PROJECTS/{{slug}}/ISA.md` holds this project's claims. Read it before planning
work here, and close claims on evidence.

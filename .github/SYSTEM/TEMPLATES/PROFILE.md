---
version: 1.0.0
last_updated: {{now}}
convention: kaios-freshness-v1
---

# Work profile

The assistant reads this at session start. It carries work context only.

| field | value |
|---|---|
| name | {{name}} |
| role | {{role}} |
| team | {{team}} |

## Stack

{{stack_list}}

## How to work with me

{{preferences}}

## Optional integrations

{{integrations}}

---
Rendered by `kaios setup render` from `CONFIG/config.json`. Edit the config and
re-render rather than editing this file by hand.

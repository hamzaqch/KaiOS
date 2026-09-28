# Threat Model

> Map what an attacker would try against a specific system, ranked by how cheap the attack is relative to what it yields.

## Done means
- The asset list is concrete. "User data" is not an asset; a named table, credential, or capability is.
- Trust boundaries are drawn and every input that crosses one is listed.
- Threats are per boundary and per asset, not a generic checklist.
- Each threat has an attacker capability requirement, so implausible threats sort below cheap ones.
- Mitigations name what they stop and what they leave open, and accepted risks are recorded as accepted.

## Output contract
```
## System and scope
## Assets
| asset | why it is worth taking | where it lives |
## Trust boundaries
| boundary | what crosses it | validated where |
## Threats
| # | threat | category | attacker needs | impact | likelihood | mitigation | status |
## Accepted risks
## Highest-value hardening
<the three changes that remove the most risk per unit of effort>
```

Categories follow spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege.

## Gotchas
Insiders and stolen credentials belong in every model. So does the build and deploy path, which is a trust boundary that teams forget to draw. Do not rate likelihood without saying what makes the attack cheap or expensive.

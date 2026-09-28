---
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# Verification rules

> The one home of the verification rules. The constitution keeps the core resident — evidence of the right modality, the pre-done self-check, the ban on "should work" — and points here. The Algorithm binds these rules into runs through claims 6, 7 and 13. Nothing else restates them.
>
> Load this file when: verifying anything that renders, deploying, deleting or replacing something live, verifying anything that has to expire or propagate, or when the verifier you need is unavailable.

Each rule below has a name. Cite the name; do not re-explain the rule somewhere else.

## Modality fidelity

The probe must exercise the same path the consumer does.

A claim about what a browser renders closes on a real browser at the real URL. A claim about what a command prints closes on that command's own output, not on reading the code that prints it. A claim about a stored value closes on reading it back from the store, not on the write call returning success. A claim about a package's behaviour closes on importing it the way the caller does, not on the source looking right.

A probe against a sibling path, a different environment, or a mock of the thing is a different request and proves nothing about the one in question. "The unit test passes" is not "the deployed job succeeds". "The file has the right content" is not "the loader parses it".

## Unavailable verifier means DEFER

When the verifier a claim needs is missing, broken, or out of reach, the claim is **not verified**. It stays open and marked deferred with a named follow-up, and I say "changed, not verified" out loud.

The forbidden move is substitution: reaching for weaker evidence and relabelling it as verification because the real probe was inconvenient. No CLI available means the claim about the CLI's behaviour defers. No access to the environment means the claim about that environment defers. A deferred claim is honest state; a claim closed on a substitute is a false record that someone will trust later.

## Appearance is not existence

Appearance ≠ existence. Finding a thing proves it exists. It proves nothing about how it looks, reads, or behaves.

A search hit proves a symbol is present, not that it is wired in. A row in a listing proves a resource exists, not that it is configured correctly. An element in a page's markup proves it is in the document, not that it is visible, legible, or the right colour. Any claim about appearance closes on an image I actually looked at — and a blank, black, or uniform frame is not a look. Any claim about a document's readability closes on reading the rendered output, not the source.

Generalised: for every claim, ask what the probe actually establishes, then check that against what the claim says. The gap between those two is where false completions live.

## Reproduce before fixing

For any reported failure, observe the failure before reading the suspect code and before writing a fix. Run the command. Open the page. Execute the query. Read the real error and the real exit code.

Code analysis without reproduction is speculation. It produces plausible fixes for bugs that were never there and leaves the real one in place, and it is the single most reliable way to spend an hour going backwards.

Three bypasses exist, and each is logged in the ISA rather than assumed: the work is purely additive so there is nothing yet to reproduce, the symptom is architectural and cannot be isolated to a reproducible case, or reproducing it would cause real damage.

## Temporal fidelity

Probe when the failure can exist.

Anything mediated by a cache, a lease, a schedule, or a time-to-live can pass at T+0 for reasons that have nothing to do with being correct. A name that resolves because a resolver still holds the old answer. A token that works because a session is still warm. A scheduled job that "ran" because the last run predates the change. A permission that still works because the grant is cached.

A claim about that class of state closes against the authority — the provider's own record, the source of truth, the authoritative server — not against a request that happened to succeed through something warm. When only a runtime probe is possible, the claim holds deferred until a re-probe after the relevant interval, and the re-probe is scheduled before the run closes, not hoped for.

## Restore parity on replace or delete

Changing or removing anything that serves real traffic or produces a real number requires four things, in order.

1. **Baseline captured before the change** — the rate over a stated window, the inventory, the row count, whatever the flow's health actually is. Captured, not remembered.
2. **Ownership enumerated from the authority before the operation** — what does this resource own, hold, or back? A dependent that "already exists" is not evidence it survives the delete; things created as children of a resource look identical to independent ones in a listing and die with their parent.
3. **The authority re-listed after the operation** — a runtime probe through a warm path is not the authority.
4. **Post-change evidence that the flow continues at baseline** within a stated tolerance.

One synthetic success is an example claim and never closes parity. The **rate** is the universal claim, and it is the one that catches an outage: an end-to-end probe can pass cleanly while throughput sits at a few percent of the baseline measured in the same run.

Any safety mitigation written into prose gets promoted to a claim with a falsifier **before** the operation executes. A mitigation that lives only in a Decisions paragraph has no teeth.

## Cache fidelity

A cache can sit between the probe and the truth in three distinct places. Name all three, because each one has produced a passing probe over a broken system.

- **Response path.** Any health or liveness surface must answer uncached, and that header is itself a claim with its own probe. A cached success during an outage is exactly the failure the endpoint exists to catch.
- **Deploy path.** A single probe after a deploy reads whichever copy answered. Verification converges or it does not count: repeat until several consecutive probes agree, and never report a fix from one call.
- **Data path.** The application's own reads may be cached too, so behaviour that depends on a value *expiring* cannot be verified from the code. Make expiry structural — rotate the key or the query so the new period reads something that cannot exist yet — rather than trusting a time-to-live on the read path.

The through-line: **a mock cannot reproduce a cache.** Tests over a faked store prove the logic and never the deployment.

## Evidence must span the claim

When a claim quantifies over a container — a suite, a directory, a fleet, a table, a corpus — the container passing is not evidence about its members, and one member passing is not evidence about the container.

The probe set touches every member *type* that a consumer actually meets, one real instance each, and a deterministic sweep covers the rest where one exists. A claim that says "every" closes on something that examined every, or it gets split until each leaf says what was really checked.

The same rule going the other way: a claim about one file does not close because the whole test suite is green, and a claim about the whole tree does not close because the one file I edited reads correctly.

## Briefing a verifier

A verification or audit brief carries the steps to run and the evidence to return. It never carries the answer it is expected to find.

A verifier told what a pass looks like will reason its way to that pass instead of driving the real path. Withholding the expected result is what forces it to produce actual evidence. This is why an independent second look restates the goal and the claims but not the build plan and not the conclusion.

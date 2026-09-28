---
name: research
description: Multi-source web research where every claim is tied to a source that was actually opened, and every source in the table has been fetched rather than remembered. Four depths from a single-question check to a full investigation, with confidence tags on each finding and an explicit list of what could not be established. USE WHEN research, look this up, find out, investigate, what is the current state of, compare these tools, is this still true, find documentation, what changed in version, vendor comparison, prior art, does anything already do this, source this claim, verify this online. NOT FOR questions answerable from the repository itself (read the code), generating ideas rather than finding facts (use be-creative), or debugging a local failure (use science).
argument-hint: "<the question> [--depth quick|standard|deep|investigation]"
---

# Research

A research report is only worth the sources someone can open. Everything else is recollection with footnotes.

## USE WHEN / NOT FOR

USE WHEN a claim needs a source, a comparison needs current facts, or something you believe about a vendor may have changed.

NOT FOR questions the repository itself answers, where reading the code is faster, or generating ideas rather than finding facts, which is be-creative.

## What this produces

Findings a reader can verify without repeating the work.

## Done looks like

- The question is restated as the specific thing being established, with the decision it feeds.
- Every source in the table was fetched in this session. A URL reproduced from memory is a guess about a URL, and it is often a plausible guess that resolves to nothing.
- Every finding carries a confidence tag and at least one source reference. Findings with no source are labelled as inference and kept in their own section.
- Sources disagree in real research. Disagreements are reported as disagreements, with both positions and the reason to prefer one, never averaged into a single bland sentence.
- Dates are attached to anything that can go stale — versions, prices, limits, availability. An undated claim about a fast-moving tool is worthless in a month.
- What could not be established is listed. An empty unknowns section in a real investigation means the search was too shallow to notice its own gaps.

## Confidence tags

| tag | when it applies |
|---|---|
| verified | stated by primary documentation or the vendor, fetched and quoted |
| corroborated | two or more independent secondary sources agree, no primary found |
| single-source | one source only, plausible, not confirmed |
| contested | credible sources disagree, both recorded |
| inference | reasoned from the above, not stated anywhere |

Primary beats secondary. Vendor documentation, a release note, a specification, a repository, or a filing outranks a blog post summarizing it, and a blog post outranks a forum recollection.

## Depths

| depth | shape | stop when |
|---|---|---|
| quick | one question, two to four sources | the primary source answers it |
| standard | a question with sub-questions, five to ten sources | each sub-question has a verified or corroborated answer |
| deep | a landscape or comparison, ten to twenty sources across positions | the options are characterized on the dimensions the decision needs |
| investigation | a contested or obscured question, no source limit | the disagreement is explained rather than restated |

Depth is set by the cost of being wrong, not by curiosity.

## Output contract

```
## Question
<the specific thing being established, and the decision it feeds>

## Findings
| # | finding | confidence | source | as of |
|---|---|---|---|---|

## Disagreements
| topic | position A (source) | position B (source) | which to prefer and why |

## Sources
| # | url | what it is | primary? | fetched |

## Unknowns
<what could not be established, and what would settle it>

## So what
<two or three sentences on what this means for the decision>
```

## Roles and tooling

Fetch pages with the agent's `fetch` tool and read them before citing them. Search results are pointers, not evidence; a title and a snippet are not a source. When a page cannot be fetched, say so in the sources table rather than citing it from the snippet.

Run at the **research** role, which is pinned to models suited to long documents and grounded retrieval. The Researcher agent carries the dispatch; parallel sub-questions can each go to their own **research** run and be merged. Synthesis and the "so what" section run at the **max** role, since deciding which source to trust is judgment. When findings will drive an expensive decision, get a **cross** role read from a different vendor family on the synthesis, not on the raw sources.

## Constraints and gotchas

- Never invent a URL. If you cannot produce a fetched link, the finding is inference, and it says so.
- Quote the sentence that supports a finding when the finding is load-bearing. Paraphrase drifts.
- Check the publication date on every page and record it. Documentation sites often serve a version other than the one in question.
- Prefer the changelog to the marketing page for anything about behavior, limits, or pricing.
- One vendor's comparison table about its competitors is a primary source about that vendor's claims and a weak secondary source about anything else.
- Write down what was searched and not found. A negative result is a finding, and it saves the next person the same sweep.

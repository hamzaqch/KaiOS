# Create Mermaid

> Produce a diagram that renders on the first try and shows the mechanism, not a box per noun.

## Done means
- The diagram type fits the content — flowchart for control, sequence for interactions over time, state for lifecycles, er for data shape.
- Syntax is valid Mermaid and the fence is labelled `mermaid`.
- Node labels are short noun phrases; edge labels carry the verb or condition.
- The diagram fits on a screen. More than about fifteen nodes means it should be split.
- Anything the diagram deliberately omits is named underneath it.

## Output contract
A single fenced `mermaid` block, then two or three sentences explaining what the reader should notice, then a line naming what is left out.

## Gotchas
Quote labels containing punctuation, parentheses, or colons, or the parse fails. Keep direction consistent, top-down for process and left-right for pipelines. A diagram that is just the file tree restated adds nothing; diagram the flow of data or control.
